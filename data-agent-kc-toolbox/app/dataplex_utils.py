"""Utils for Dataplex semantic search, verification, and CA Toolbox calling."""

import json
import logging
import os
from typing import Any
import urllib.parse

from google import genai
from google.adk.tools.tool_context import ToolContext
import google.auth
import google.auth.transport.requests
from google.cloud import dataplex_v1
import google.protobuf.json_format as jsonpb
import requests

from . import auth_utils

PROJECT_ID = auth_utils.resolve_project_id()
# Project whose catalog hosts the team's data assets (BQ tables, Dataplex
# zones). Defaults to the active GCP project; override with
# DATAPLEX_CATALOG_PROJECT if your data lives in a different project than the
# agent runs in. Glossaries and other cross-project context entries are
# discovered separately by the unscoped KNOWLEDGE catch-all in `dataplex_search`.
# Important: must be the **alphabetic** project ID — Dataplex's projectid:
# predicate doesn't match against project numbers, which is what
# GOOGLE_CLOUD_PROJECT silently is under Vertex AI Agent Engine.
PROJECT_NAME = os.environ.get("DATAPLEX_CATALOG_PROJECT", PROJECT_ID)

# Hard cap on dataplex_search calls per user question. The orchestration prompt
# asks the LLM to stop after 3 rounds, but prompt-only enforcement isn't
# reliable — this is the in-code backstop. Tracked per invocation_id via
# tool_context.state so multiple turns in the same session each get their own
# budget.
_MAX_SEARCHES_PER_QUESTION = 3


def _search_count_key(tool_context: Any) -> str:
  """State key used to count dataplex_search calls per user question."""
  invocation_id = getattr(tool_context, "invocation_id", "default") or "default"
  return f"dataplex_search_count:{invocation_id}"


_GLOBAL_ENTRY_CACHE = {}  # Legacy marker, unused
_GLOBAL_OVERVIEW_CACHE = {}  # Legacy marker, unused
_GLOBAL_INFO_CACHE = {}  # Legacy marker, unused
_GLOBAL_LOOKUP_CACHE = {}  # Legacy marker, unused


def _classify_entry_system(entry: Any) -> str:
  """Bucket an entry into BIGQUERY / CLOUD_STORAGE / SPANNER / DATAPLEX / KNOWLEDGE by its entry_type or name.

  The orchestrator routes by this label: BIGQUERY entries go to
  call_bigquery_ca; CLOUD_STORAGE / SPANNER go to MCP tools;
  KNOWLEDGE/DATAPLEX entries are grounding.
  """
  et = (getattr(entry, "entry_type", "") or "").lower()
  name = (getattr(entry, "name", "") or "").lower()
  if "bigquery" in et:
    return "BIGQUERY"
  if (
      any(k in et for k in ("cloud_storage", "gcs", "fileset", "bucket"))
      or "gs://" in name
      or "fileset" in name
  ):
    return "CLOUD_STORAGE"
  if "spanner" in et or "spanner" in name:
    return "SPANNER"
  if "dataplex" in et:
    return "DATAPLEX"
  return "KNOWLEDGE"


def _get_cached_entry_dict(
    name: str, client: dataplex_v1.CatalogServiceClient, tool_context: Any = None
) -> dict[str, Any]:
  """Fetches a Dataplex entry with view=FULL, caching the JSON-serializable dict in tool_context.state."""
  state = getattr(tool_context, "state", None) if tool_context else None
  if state is not None:
    entry_cache = state.setdefault("dataplex_entry_cache", {})
    if name in entry_cache:
      return entry_cache[name]

  logging.info(f"Outgoing GetEntryRequest for: {name}")
  request = dataplex_v1.GetEntryRequest(name=name, view="FULL")
  entry = client.get_entry(request=request)
  entry_dict = jsonpb.MessageToDict(entry._pb)

  if state is not None:
    state["dataplex_entry_cache"][name] = entry_dict
  return entry_dict


def get_entry_overview(
    name: str, client: dataplex_v1.CatalogServiceClient, tool_context: Any = None
) -> str:
  """Fetches a textual overview for a single Dataplex entry with session caching."""
  state = getattr(tool_context, "state", None) if tool_context else None
  if state is not None:
    overview_cache = state.setdefault("dataplex_overview_cache", {})
    if name in overview_cache:
      return overview_cache[name]

  overview_aspect_key = "655216118709.global.overview"
  try:
    entry_dict = _get_cached_entry_dict(name, client, tool_context)

    aspects = entry_dict.get("aspects", {})
    overview = (
        aspects.get(overview_aspect_key, {}).get("data", {}).get("content", "")
    )
    if not overview:
      for aspect_data in aspects.values():
        data = aspect_data.get("data", {})
        for field in ("content", "description", "summary", "body"):
          val = data.get(field)
          if isinstance(val, str) and val.strip():
            overview = val
            break
        if overview:
          break

    if not overview:
      source_dict = (
          entry_dict.get("entrySource", entry_dict.get("entry_source", {})) or {}
      )
      source_desc = source_dict.get("description", "")
      if source_desc:
        overview = source_desc

    if not overview:
      overview = entry_dict.get("description", "")

    gcs_uri = _extract_gcs_uri(entry_dict)
    if gcs_uri:
      body = _fetch_gcs_text(gcs_uri)
      if body:
        overview = (
            f"{overview}\n\n--- Content of {gcs_uri} ---\n{body}"
            if overview
            else f"--- Content of {gcs_uri} ---\n{body}"
        )

    overview = overview or "No description available."
  except Exception as e:
    logging.warning(f"Failed to fetch overview for {name}: {e}")
    overview = "No description available."

  if state is not None:
    state["dataplex_overview_cache"][name] = overview
  return overview


_GCS_TEXT_MAX_BYTES = (
    16 * 1024
)  # cap per object so policy docs don't blow up context


def _extract_gcs_uri(entry_dict: dict[str, Any]) -> str | None:
  """Find a gs:// URI in an entry's source metadata, if present."""
  source_dict = (
      entry_dict.get("entrySource", entry_dict.get("entry_source", {})) or {}
  )
  for attr in ("resource", "system", "description"):
    val = source_dict.get(attr, "")
    if isinstance(val, str) and "gs://" in val:
      idx = val.find("gs://")
      return val[idx:].split()[0].rstrip(".,;)")
  for v in source_dict.values():
    if isinstance(v, str) and "gs://" in v:
      idx = v.find("gs://")
      return v[idx:].split()[0].rstrip(".,;)")
  return None


def _fetch_gcs_text(gs_uri: str) -> str:
  """Read a ``gs://bucket/object`` as UTF-8 text, truncated.

  Returns "" on any failure.
  """
  try:
    from google.cloud import storage

    if not gs_uri.startswith("gs://"):
      return ""
    path = gs_uri[len("gs://") :]
    bucket_name, _, object_name = path.partition("/")
    if not bucket_name or not object_name:
      return ""
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(object_name)
    data = blob.download_as_bytes(start=0, end=_GCS_TEXT_MAX_BYTES - 1)
    text = data.decode("utf-8", errors="replace")
    if len(data) >= _GCS_TEXT_MAX_BYTES:
      text += f"\n\n[... truncated at {_GCS_TEXT_MAX_BYTES} bytes ...]"
    return text
  except Exception as e:
    logging.info(f"Could not fetch GCS object {gs_uri}: {e}")
    return ""


def fetch_full_entry_info(
    name: str, client: dataplex_v1.CatalogServiceClient, tool_context: Any = None
) -> str:
  """Fetches full entry aspect data via GetEntry with session caching."""
  state = getattr(tool_context, "state", None) if tool_context else None
  if state is not None:
    info_cache = state.setdefault("dataplex_info_cache", {})
    if name in info_cache:
      return info_cache[name]

  try:
    entry_dict = _get_cached_entry_dict(name, client, tool_context)

    # Dump important fields
    result_lines = [f"Entry Name: {name}"]
    description = entry_dict.get("description", "")
    if description:
      result_lines.append(f"Description: {description}")
    if "aspects" in entry_dict:
      result_lines.append("Aspects:")
      for key, aspect in entry_dict["aspects"].items():
        data = aspect.get("data", {})
        result_lines.append(f" - {key}: {json.dumps(data, indent=2)}")
    info = "\n".join(result_lines)
  except Exception as e:
    info = f"Entry Name: {name}\nError fetching info: {e}"

  if state is not None:
    state["dataplex_info_cache"][name] = info
  return info


from .file_utils import truncate, log_to_file


def get_brief_context(
    entry_names: list[str],
    client: dataplex_v1.CatalogServiceClient,
    prepopulated_descriptions: dict[str, str] | None = None,
    systems: dict[str, str] | None = None,
    tool_context: ToolContext | None = None,
) -> str:
  """Returns short/brief context for a set of resources.

  Each entry block includes ``Category:`` (BIGQUERY / CLOUD_STORAGE / SPANNER / DATAPLEX / KNOWLEDGE)
  when ``systems`` is provided — the orchestration prompt routes by this
  field to pick the right downstream tool per entry.
  """
  results = []
  seen = set()
  preloaded = prepopulated_descriptions or {}
  sys_map = systems or {}

  for name in entry_names:
    if name in seen or name == "Unknown":
      continue
    seen.add(name)

    desc = preloaded.get(name, "")
    if not desc:
      desc = get_entry_overview(name, client, tool_context)

    sys_line = f"Category: {sys_map[name]}\n" if name in sys_map else ""
    results.append(f"Entry Name: {name}\n{sys_line}Description: {desc}\n---")

  return (
      "\n".join(results) if results else "No entries found for the given query."
  )


def get_detailed_context(
    entry_names: list[str], client: dataplex_v1.CatalogServiceClient, tool_context: ToolContext | None = None
) -> str:
  """Returns large/detailed context for a set of resources with session caching.

  For every entry, includes: brief overview (with GCS content when applicable),
  full aspect dump, and LookupContext. LookupContext is attempted on all entry
  types — for entry kinds where it doesn't apply the API returns an empty
  response and we just skip that section.
  """
  seen = set()
  results = []
  state = getattr(tool_context, "state", None) if tool_context else None

  for name in entry_names:
    if name in seen:
      continue
    seen.add(name)

    desc = get_entry_overview(name, client, tool_context)
    entry_text = f"Entry Name: {name}\nDescription: {desc}\n---"

    info = fetch_full_entry_info(name, client, tool_context)
    entry_text += f"\n--- Full Entry Info for {name} ---\n{info}"

    ctx = None
    if state is not None:
      lookup_cache = state.setdefault("dataplex_lookup_cache", {})
      if name in lookup_cache:
        ctx = lookup_cache[name]

    if ctx is None:
      parts = name.split("/")
      loc = "global"
      if "locations" in parts:
        idx = parts.index("locations")
        if len(parts) > idx + 1:
          loc = parts[idx + 1]

      try:
        logging.info(f"Outgoing LookupContextRequest for: {name}")
        request = dataplex_v1.LookupContextRequest(
            name=f"projects/{PROJECT_ID}/locations/{loc}",
            resources=[name],
            options={"format": "yaml", "allowed_entries": json.dumps([name])},
        )
        res = client.lookup_context(request=request)
        raw_ctx = getattr(res, "context", str(res))
        if raw_ctx and len(raw_ctx.strip()) > 5:
          ctx = raw_ctx
        else:
          ctx = ""
      except Exception as e:
        logging.info(f"LookupContext failed for {name}. {e}")
        ctx = ""

      if state is not None:
        state["dataplex_lookup_cache"][name] = ctx

    if ctx:
      entry_text += f"\n--- LookupContext for {name} ---\n{ctx}"

    results.append(entry_text)

  return "\n".join(results) if results else "No entries found."


def dataplex_search(query: str, tool_context: ToolContext | None = None) -> str:
  """Searches Dataplex Catalog for relevant entries and returns matches.

  Args:
      query: The search string to query Dataplex semantic catalog for.
  """
  logging.info(f"Tool 'dataplex_search' called with query: {query}")

  state_key = _search_count_key(tool_context)
  state = getattr(tool_context, "state", None)
  if state is not None:
    count = state.get(state_key, 0)
    if count >= _MAX_SEARCHES_PER_QUESTION:
      msg = (
          f"SEARCH LIMIT REACHED: dataplex_search has been called {count} times"
          f" for this question (cap is {_MAX_SEARCHES_PER_QUESTION}). STOP"
          " searching. Decide based on the entries you have already fetched"
          " via get_entries_context. Pick exactly one of these actions:\n\n "
          " (A) If those entries include at least one BIGQUERY table, call"
          " `call_bigquery_ca` once with the BigQuery entry names + any"
          " KNOWLEDGE/DATAPLEX entries as grounding + the user's question.\n\n"
          "  (B) If the entries are all KNOWLEDGE/DATAPLEX (no BIGQUERY) AND"
          " the question is definitional/policy-oriented (e.g., 'what's our"
          " return policy?', 'what does X mean?'), answer the user directly"
          " from the entry content. Cite the entry.\n\n  (C) If the entries"
          " include CLOUD_STORAGE or SPANNER entries, call the corresponding"
          " MCP tools (`gcs_*`, `spanner_*`) directly.\n\n  (D) If the entries"
          " are all KNOWLEDGE/DATAPLEX but the question is analytical and"
          " needs a BigQuery table that the catalog did not surface, tell the"
          " user the catalog has no BigQuery tables matching their question"
          " and suggest they (1) verify Dataplex auto-discovery has run on the"
          " relevant dataset, or (2) redeploy with DATAPLEX_ENABLED=false to"
          " bypass the catalog.\n\nCRITICAL: Your tool set is fixed:"
          " `dataplex_search`, `get_entries_context`, `call_bigquery_ca`,"
          " plus any loaded MCP tools (`gcs_*`, `spanner_*`, etc.). Do"
          " NOT invent or call tools that are not in your tool definitions."
          " Pick action A, B, C, or D and produce your final answer."
      )
      logging.warning(
          f"dataplex_search hit cap ({count}/{_MAX_SEARCHES_PER_QUESTION}); "
          "returning stop message."
      )
      return msg
    state[state_key] = count + 1

  try:
    creds = auth_utils.get_user_credentials(tool_context)
    client = dataplex_v1.CatalogServiceClient(credentials=creds)
    location_name = f"projects/{PROJECT_ID}/locations/global"

    semantic_query = f"{query} projectid:({PROJECT_NAME})"
    semantic_results = list(
        client.search_entries(
            request=dataplex_v1.SearchEntriesRequest(
                name=location_name,
                query=semantic_query,
                page_size=15,
                semantic_search=True,
            ),
            timeout=2.0,
        ).results
    )
    logging.info(
        f"Semantic SearchEntries(query={semantic_query!r}) returned "
        f"{len(semantic_results)} entries"
    )

    bq_predicate = (
        f"system=BIGQUERY (type=TABLE OR type=VIEW) projectid:({PROJECT_NAME})"
    )
    bq_results = list(
        client.search_entries(
            request=dataplex_v1.SearchEntriesRequest(
                name=location_name,
                query=bq_predicate,
                page_size=15,
                semantic_search=False,
            ),
            timeout=2.0,
        ).results
    )
    logging.info(
        f"Keyword SearchEntries(query={bq_predicate!r}) returned "
        f"{len(bq_results)} entries"
    )

    dp_predicate = f"system=DATAPLEX projectid:({PROJECT_NAME})"
    dp_results = list(
        client.search_entries(
            request=dataplex_v1.SearchEntriesRequest(
                name=location_name,
                query=dp_predicate,
                page_size=15,
                semantic_search=False,
            ),
            timeout=2.0,
        ).results
    )
    logging.info(
        f"Keyword SearchEntries(query={dp_predicate!r}) returned "
        f"{len(dp_results)} entries"
    )

    knowledge_query = f"{query}"
    knowledge_results = list(
        client.search_entries(
            request=dataplex_v1.SearchEntriesRequest(
                name=location_name,
                query=knowledge_query,
                page_size=15,
                semantic_search=True,
            ),
            timeout=2.0,
        ).results
    )
    logging.info(
        f"Semantic SearchEntries(query={knowledge_query!r}) returned "
        f"{len(knowledge_results)} entries"
    )

    entry_names = []
    prepopulated = {}
    systems = (
        {}
    )  # name -> source system ("BIGQUERY" | "CLOUD_STORAGE" | "SPANNER" | "DATAPLEX" | "KNOWLEDGE")
    seen_entries = set()

    for source_label, items in (
        ("semantic", semantic_results),
        ("bq_predicate", bq_results),
        ("dp_predicate", dp_results),
        ("knowledge", knowledge_results),
    ):
      for item in items:
        name = getattr(item.dataplex_entry, "name", "Unknown")
        if name in seen_entries or name == "Unknown":
          continue
        seen_entries.add(name)
        entry_names.append(name)
        system = _classify_entry_system(item.dataplex_entry)
        systems[name] = system
        logging.info(f"Discovered entry ({system}, via {source_label}): {name}")
        desc = getattr(item.dataplex_entry, "description", "") or getattr(
            getattr(item, "snippets", object()), "description", ""
        )
        if desc:
          prepopulated[name] = desc

    output = get_brief_context(
        entry_names, client, prepopulated, systems=systems, tool_context=tool_context
    )
    logging.info(
        f"Total characters provided to LLM by search tool: {len(output)}"
    )

    log_to_file(output, "dataplex_search_results")

    return output
  except Exception as e:
    err_msg = f"Error in dataplex_search: {e}"
    logging.error(err_msg)
    return err_msg


def get_entries_context(
    entry_names: list[str], tool_context: ToolContext | None = None
) -> str:
  """Fetches full context for a set of Dataplex entries.

  Returns, per entry: the overview (with any inlined GCS content for
  KNOWLEDGE entries pointing to a gs:// source), all aspects from the entry,
  and the LookupContext payload. Use this after ``dataplex_search`` to read
  the actual content of relevant entries before deciding how to execute
  (query BigQuery, read a GCS object, answer from policy text, etc.).

  Args:
      entry_names: List of full Dataplex resource names to fetch.
  """
  logging.info(f"Tool 'get_entries_context' called for entries: {entry_names}")
  try:
    creds = auth_utils.get_user_credentials(tool_context)
    client = dataplex_v1.CatalogServiceClient(credentials=creds)
    output = get_detailed_context(entry_names, client, tool_context=tool_context)
    logging.info(
        "Total characters provided to LLM by get_entries_context:"
        f" {len(output)}"
    )
    log_to_file(output, "get_entries_context_results")
    return output
  except Exception as e:
    err_msg = f"Error in get_entries_context: {e}"
    logging.error(err_msg)
    return err_msg

