"""CA Toolbox Agent for fetching data and executing queries across Dataplex and BigQuery assets."""

import base64
import json
import logging
import os
import re
from typing import Any
import uuid

from google.adk.agents.llm_agent import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.api_core import client_options, exceptions
import google.auth
from google.cloud import geminidataanalytics_v1beta as geminidataanalytics
import requests

from . import auth_utils
from .file_utils import log_to_file, truncate

# The new flow is creating agent and conversation in the BigQuery CA,
# while the legacy makes one on the fly.
USE_NEW_CA_TOOLBOX_FLOW = False

# Default project used by CA calls. Resolved once at import time via the
# metadata server (or Resource Manager fallback), NOT from GOOGLE_CLOUD_PROJECT —
# Vertex AI Agent Engine silently populates that env var with the project
# NUMBER, which is fine for resource paths like projects/<num>/... but wrong
# for any API that distinguishes ID from number. See
# auth_utils.resolve_project_id for the resolution chain.
_DEFAULT_PROJECT = auth_utils.resolve_project_id()


def _project_id() -> str:
  """Resolve the GCP project for CA API calls (alphabetic project ID)."""
  return _DEFAULT_PROJECT or os.environ.get("GOOGLE_CLOUD_PROJECT") or ""


def _call_legacy_ca_toolbox(
    question: str,
    inline_instruction: str,
    context_block: str,
    table_references: list[dict],
    creds: Any,
    project_id: str,
) -> str:
  headers = {
      "Authorization": f"Bearer {creds.token}",
      "Content-Type": "application/json",
  }

  url = f"https://geminidataanalytics.googleapis.com/v1beta/projects/{project_id}/locations/global:chat"

  inline_ctx = {
      "system_instruction": (
          f"Instructions: {inline_instruction}\n\nInline entry"
          f" context:\n{context_block}"
      ),
      "options": {"analysis": {"python": {"enabled": True}}},
      "tenancy_mode": "TENANCY_MODE_ENABLED",
  }
  if table_references:
    inline_ctx["datasource_references"] = {
        "bq": {"table_references": table_references}
    }

  payload = {
      "parent": f"projects/{project_id}/locations/global",
      "messages": [{"userMessage": {"text": question}}],
      "inline_context": inline_ctx,
  }

  log_to_file(json.dumps(payload, indent=2), "ca_toolbox_request")

  try:
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    if response.status_code != 200:
      err_msg = (
          f"Error calling CA Toolbox: {response.status_code} - {response.text}"
      )
      logging.error(err_msg)
      return err_msg

    data_json = response.json()
    log_to_file(json.dumps(data_json, indent=2), "ca_toolbox_response")

    final_answer = ""
    sqls = []
    tables = []

    for msg in data_json:
      if "systemMessage" in msg:
        sys_msg = msg["systemMessage"]
        if "text" in sys_msg:
          text_msg = sys_msg["text"]
          if text_msg.get("textType") == "FINAL_RESPONSE":
            final_answer += "".join(text_msg.get("parts", []))
        if "data" in sys_msg:
          data_obj = sys_msg["data"]
          if "generatedSql" in data_obj:
            sql = data_obj["generatedSql"]
            sqls.append(sql)
          if "result" in data_obj:
            res_data = data_obj["result"]
            if isinstance(res_data, dict) and "data" in res_data:
              rows = []
              for r in res_data["data"]:
                if "fields" in r:
                  row_dict = {}
                  for k, v in r["fields"].items():
                    row_dict[k] = str(
                        v.get("stringValue", v.get("numberValue", "NULL"))
                    )
                  if row_dict:
                    rows.append(row_dict)
              if rows:
                max_rows = 20
                if len(rows) > max_rows:
                  half = max_rows // 2
                  indicators = {k: "..." for k in rows[0].keys()}
                  rows = rows[:half] + [indicators] + rows[-half:]
                keys = list(rows[0].keys())
                header = "| " + " | ".join(keys) + " |"
                separator = "| " + " | ".join(["---"] * len(keys)) + " |"
                table_str = [header, separator]
                for r in rows:
                  vals = [str(r.get(k, "")) for k in keys]
                  table_str.append("| " + " | ".join(vals) + " |")
                tables.append("\n".join(table_str))

    if sqls:
      final_answer += "\n\n### Generated SQL Queries\n"
      for sql in sqls:
        final_answer += f"```sql\n{sql.strip()}\n```\n"
    if tables:
      final_answer += "\n\n### Tabular Results\n"
      for t in tables:
        final_answer += f"\n{t}\n"

    return final_answer
  except Exception as e:
    err_msg = f"Failed to call legacy CA Toolbox service: {e}"
    logging.error(err_msg)
    return err_msg


def _call_new_ca_toolbox(
    question: str,
    inline_instruction: str,
    context_block: str,
    table_references: list[dict],
    creds: Any,
    project_id: str,
) -> str:
  logging.info("Configuring Data Agent Client options...")
  opts = client_options.ClientOptions(
      api_endpoint="geminidataanalytics.googleapis.com",
      client_cert_source=lambda: (None, None),
  )

  agent_client = geminidataanalytics.DataAgentServiceClient(
      credentials=creds, client_options=opts
  )
  chat_client = geminidataanalytics.DataChatServiceClient(
      credentials=creds, client_options=opts
  )

  agent_id = f"tool-agent-{uuid.uuid4().hex[:8]}"
  parent = f"projects/{project_id}/locations/global"

  inline_ctx = {
      "system_instruction": (
          f"Instructions: {inline_instruction}\n\nInline entry"
          f" context:\n{context_block}"
      ),
  }
  if table_references:
    inline_ctx["datasource_references"] = {
        "bq": {"table_references": table_references}
    }

  data_agent = geminidataanalytics.DataAgent(
      display_name="CA Toolbox Agent",
      data_analytics_agent={"published_context": inline_ctx},
  )

  create_req = geminidataanalytics.CreateDataAgentRequest(
      parent=parent, data_agent_id=agent_id, data_agent=data_agent
  )

  try:
    logging.info("Step 1: Creating Data Agent...")
    operation = agent_client.create_data_agent(request=create_req)
    agent_response = operation.result()
    agent_name = agent_response.name
  except exceptions.AlreadyExists:
    agent_name = f"{parent}/dataAgents/{agent_id}"
  except Exception as e:
    if "already exists" in str(e).lower():
      agent_name = f"{parent}/dataAgents/{agent_id}"
    else:
      logging.error(f"Exception calling create data agent: {e}")
      agent_name = f"{parent}/dataAgents/{agent_id}"

  logging.info("Step 2: Creating conversation...")
  conv_req = geminidataanalytics.CreateConversationRequest(
      parent=parent,
      conversation=geminidataanalytics.Conversation(
          agents=[agent_name], labels={"host": "bigquery"}
      ),
  )
  conv_resp = chat_client.create_conversation(request=conv_req)
  conv_name = conv_resp.name

  agent_uuid = agent_name.split("/")[-1]
  chat_uuid = conv_name.split("/")[-1]

  link_url = f"https://console.cloud.google.com/bigquery/agents_hub;agentsHubTab=Conversations;agentsPath=%2Fbq%2Fagents%2F{agent_uuid};chatPath=%2Fbq%2Fchat%2F{chat_uuid}?project={project_id}"

  logging.info("Step 3: Sending message to chat...")
  chat_req = geminidataanalytics.ChatRequest(
      parent=parent,
      conversation_reference=geminidataanalytics.ConversationReference(
          conversation=conv_name,
          data_agent_context=geminidataanalytics.DataAgentContext(
              data_agent=agent_name
          ),
      ),
      messages=[
          geminidataanalytics.Message(
              user_message=geminidataanalytics.UserMessage(text=question)
          )
      ],
      thinking_mode=geminidataanalytics.ChatRequest.ThinkingMode.THINKING,
  )

  responses = chat_client.chat(request=chat_req)

  final_answer = ""
  sqls = []
  tables = []

  for chunk in responses:
    sys_msg = chunk.system_message
    if not sys_msg:
      continue

    # Try to convert to dictionary for robust parsing matching legacy structure
    sys_msg_dict = {}
    try:
      sys_msg_dict = type(sys_msg).to_dict(sys_msg)
    except Exception:
      pass

    # Stream text chunks, identifying if it's a thought context or final response
    if sys_msg.text and sys_msg.text.parts:
      raw_type = getattr(sys_msg.text, "text_type", None)
      type_name = (
          getattr(raw_type, "name", str(raw_type))
          if raw_type is not None
          else ""
      )
      if "FINAL_RESPONSE" in type_name or str(raw_type) == "1":
        final_answer += "".join(sys_msg.text.parts)

    # Stream data parts
    if sys_msg.data:
      if sys_msg.data.generated_sql:
        sqls.append(sys_msg.data.generated_sql)
      if sys_msg.data.result:
        # Extract fields from result payload
        res_dict = sys_msg_dict.get("data", {}).get("result", {})
        if isinstance(res_dict, dict) and "data" in res_dict:
          rows = []
          for r in res_dict["data"]:
            if "fields" in r:
              row_dict = {}
              for k, v in r["fields"].items():
                row_dict[k] = str(
                    v.get("stringValue", v.get("numberValue", "NULL"))
                )
              if row_dict:
                rows.append(row_dict)
          if rows:
            max_rows = 20
            if len(rows) > max_rows:
              half = max_rows // 2
              indicators = {k: "..." for k in rows[0].keys()}
              rows = rows[:half] + [indicators] + rows[-half:]
            keys = list(rows[0].keys())
            header = "| " + " | ".join(keys) + " |"
            separator = "| " + " | ".join(["---"] * len(keys)) + " |"
            table_str = [header, separator]
            for r in rows:
              vals = [str(r.get(k, "")) for k in keys]
              table_str.append("| " + " | ".join(vals) + " |")
            tables.append("\n".join(table_str))

  if sqls:
    final_answer += "\n\n### Generated SQL Queries\n"
    for sql in sqls:
      final_answer += f"```sql\n{sql.strip()}\n```\n"
  if tables:
    final_answer += "\n\n### Tabular Results\n"
    for t in tables:
      final_answer += f"\n{t}\n"

  logging.info(f"Created CA Toolbox conversation with URL: {link_url}")

  final_answer += (
      "\nImportant: in the final resopnse include the following link:"
      f" {link_url} and mention that you have created this conversation for the"
      " user in BigQuery CA (Conversational Analytics)."
  )

  return final_answer


def call_bigquery_ca(
    entry_names: list[str],
    question: str,
    inline_instruction: str,
    tool_context: ToolContext,
) -> str:
  """Per-system handler for **BigQuery** entries — calls BigQuery Conversational Analytics (CA).

  Use this ONLY for entries whose ``Category:`` is ``BIGQUERY`` (as surfaced by
  ``dataplex_search``). The function silently drops any entry name that
  doesn't match the BigQuery resource pattern, so passing GCS / Spanner
  entries here is a no-op — route those to their own tools instead
  (``gcs_*`` MCP tools for Cloud Storage, ``spanner_*`` when enabled, etc.).
  Non-BigQuery entries that carry useful context (e.g. business terms,
  glossary entries) can still be included; only the BigQuery ones drive the
  actual SQL execution via CA.

  This is one example of a per-system handler pattern. As new systems
  require non-trivial orchestration (multi-step context fetching, custom
  auth, output shaping), add sibling functions named ``call_<system>_*``.
  Systems whose existing MCP tools are sufficient can skip the wrapper and
  be called directly from the orchestration prompt.

  Args:
      entry_names: List of fully-qualified table references that CA should
        query. Accepts either Dataplex resource names (when Dataplex is enabled
        and `dataplex_search` provided them) or BigQuery resource paths of the
        form ``projects/<proj>/datasets/<dset>/tables/<tbl>`` (when Dataplex is
        disabled and the LLM discovered tables via the `bigquery_*` MCP tools).
        Non-BQ entries are used for context only.
      question: The user query or objective for the CA engine.
      inline_instruction: Hint or directional instructions guiding the analysis
        flow.
      tool_context: Context passed by the ADK framework containing user auth
        credentials.
  """
  logging.info(
      f"Tool 'call_bigquery_ca' called with entries={entry_names},"
      f" question={question}"
  )

  creds = auth_utils.get_user_credentials(tool_context)
  PROJECT_ID = _project_id()

  table_references = []
  context_block = ""

  # No entries → CA's `:chat` endpoint will return REFERENCES_NOT_SET. Steer
  # the LLM back to the discovery path instead of letting CA error out.
  if not entry_names:
    return (
        "Cannot call BigQuery Conversational Analytics with no table"
        " references. Discover candidate tables first via"
        " `bigquery_list_datasets` / `bigquery_list_tables` /"
        " `bigquery_get_table_info`, then re-call this tool with `entry_names`"
        " set to one or more"
        " `projects/<project>/datasets/<dataset>/tables/<table>` paths. If you"
        " genuinely cannot find a relevant table, ask the user for"
        " clarification rather than guessing."
    )

  # Resolve entry_names into both BQ table_references (for CA) and a
  # context_block (Dataplex catalog metadata, when those entries originated
  # from `dataplex_search`). Plain BQ resource paths skip the Dataplex
  # lookup; only true Dataplex entry-group paths get enriched context.
  has_dataplex_entries = any("entryGroups" in name for name in entry_names)
  if has_dataplex_entries:
    from google.cloud import dataplex_v1
    from .dataplex_utils import get_detailed_context

    client = dataplex_v1.CatalogServiceClient(credentials=creds)
    context_block = get_detailed_context(entry_names, client, tool_context)

  # Extract BigQuery table_references from entry_names, and collect the
  # remaining non-BQ entries (policies, glossaries, business terms) so we
  # can hoist their content into `inline_instruction` as concrete grounding.
  # The regex picks the unique `projects/<id>/datasets/<ds>/tables/<tb>`
  # triple, which for full Dataplex paths is the actual data project
  # (alphabetic ID) rather than the catalog tenant project (number).
  non_bq_entries: list[str] = []
  for name in entry_names:
    match = re.search(r"projects/([^/]+)/datasets/([^/]+)/tables/([^/]+)", name)
    if not match:
      if "entryGroups" in name:
        non_bq_entries.append(name)
      continue
    proj, dset, tbl = match.groups()
    if re.match(r"^[a-zA-Z0-9_-]+$", dset) and re.match(
        r"^[a-zA-Z0-9_-]+$", tbl
    ):
      table_references.append(
          {"project_id": proj, "dataset_id": dset, "table_id": tbl}
      )

  # Defensive grounding injection: the orchestration prompt tells the LLM to
  # transcribe policy/glossary content into `inline_instruction`, but LLM
  # adherence isn't reliable. If a vague reference like "identify the
  # definition from customer-segment-policy" reaches CA, CA cannot resolve
  # it because CA doesn't read the catalog. So we extract the overview
  # (which already includes inlined GCS text for KNOWLEDGE entries pointing
  # to a gs:// source) ourselves and prepend it under a "GROUNDING RULES"
  # banner. CA sees concrete predicates / filter rules / business
  # definitions before the LLM's instruction, regardless of how sloppy the
  # LLM was.
  if non_bq_entries:
    from google.cloud import dataplex_v1
    from .dataplex_utils import get_entry_overview

    if not has_dataplex_entries:
      client = dataplex_v1.CatalogServiceClient(credentials=creds)
    grounding_parts: list[str] = []
    for name in non_bq_entries:
      short_name = name.split("/entries/")[-1] or name
      overview = get_entry_overview(name, client, tool_context)
      if overview and overview != "No description available.":
        grounding_parts.append(
            f"=== Grounding from `{short_name}` ===\n{overview}"
        )
    if grounding_parts:
      grounding_block = "\n\n".join(grounding_parts)
      inline_instruction = (
          "GROUNDING RULES (apply these definitions, filters, business "
          "logic, and SQL fragments verbatim when generating SQL — do "
          "NOT ignore them):\n\n"
          f"{grounding_block}\n\n"
          "---\n\n"
          f"USER INSTRUCTION:\n{inline_instruction}"
      )

  if not table_references:
    return (
        "None of the provided entry_names resolved to a valid BigQuery "
        "table reference. Expected paths like "
        "`projects/<project>/datasets/<dataset>/tables/<table>`. "
        "Use `bigquery_list_datasets` / `bigquery_list_tables` to find "
        "valid tables, then retry."
    )

  if not creds.valid or not creds.token:
    import google.auth.transport.requests

    creds.refresh(google.auth.transport.requests.Request())

  if USE_NEW_CA_TOOLBOX_FLOW:
    final_answer = _call_new_ca_toolbox(
        question=question,
        inline_instruction=inline_instruction,
        context_block=context_block,
        table_references=table_references,
        creds=creds,
        project_id=PROJECT_ID,
    )
  else:
    final_answer = _call_legacy_ca_toolbox(
        question=question,
        inline_instruction=inline_instruction,
        context_block=context_block,
        table_references=table_references,
        creds=creds,
        project_id=PROJECT_ID,
    )

  logging.info(f"Final CA Toolbox response:\n{truncate(final_answer, 500)}")
  return final_answer
