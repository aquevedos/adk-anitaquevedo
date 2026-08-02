# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import os
from typing import Any

from app.app_utils.agent_typing import Feedback
from app.app_utils.telemetry import setup_telemetry
from app.auth_utils import get_end_user_token, is_local_mcp_url, resolve_project_id
from app.ca_toolbox_kc_wrapper import app as adk_app, orchestration_agent
from dotenv import load_dotenv
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.adk.tools.function_tool import FunctionTool
from google.cloud import logging as google_cloud_logging
import vertexai
from vertexai.agent_engines.templates.adk import AdkApp

# Load environment variables from .env file at runtime
load_dotenv()


def _load_mcp_toolbox_tools(url: str) -> list[Any]:
  """Connect to a deployed MCP Toolbox and return its tools as ADK FunctionTools.

  Uses ``ToolboxSyncClient`` which maintains a class-level persistent
  background thread + event loop for the underlying aiohttp session. This
  matters because Vertex AI Agent Engine calls ``set_up()`` on one loop,
  then dispatches each request on a different loop — an aiohttp session
  bound to either of those would go stale ("Event loop is closed" on the
  first tool invocation). The sync client's forever-loop sidesteps that
  entirely: every tool call marshals onto the same loop via
  ``run_coroutine_threadsafe``.

  Auth model: up to two headers
    - Authorization: Google ID token from the agent's runtime SA (gates Cloud
      Run IAM via roles/run.invoker).
    - X-Goog-User-Authorization: end-user OAuth token from
      ``auth_utils.get_end_user_token()``, included only when a token is
      actually available. toolbox-core has no None-omit behavior — if you
      pass a callable that resolves to None, aiohttp raises a "Cannot
      serialize non-str key" TypeError on the next request. So we resolve
      once at startup and attach the header only when it has content. When
      ADK exposes the end-user OAuth token per-request, change this to
      forward the token via a different mechanism (custom middleware, or
      upstream ``resolve_value`` gains None-omit semantics).
  """
  from toolbox_core import ToolboxSyncClient, auth_methods

  client_headers: dict = {}

  # Local toolbox isn't behind Cloud Run IAM — skip the ID token (the
  # metadata-server lookup would fail for a non-Google audience anyway).
  if not is_local_mcp_url(url):
    client_headers["Authorization"] = auth_methods.aget_google_id_token(url)
  else:
    logging.info(
        f"MCP_TOOLBOX_URL is local ({url}); skipping Cloud Run ID token."
    )

  user_token = get_end_user_token()
  if user_token:
    client_headers["X-Goog-User-Authorization"] = f"Bearer {user_token}"
  else:
    logging.info(
        "No end-user OAuth token available at startup;"
        " X-Goog-User-Authorization omitted (sources with client_auth_mode:"
        " end_user will fall back to SA)."
    )

  client = ToolboxSyncClient(url, client_headers=client_headers)
  toolbox_tools = client.load_toolset()
  return [FunctionTool(func=t) for t in toolbox_tools]


def _attach_mcp_tools() -> None:
  """Read MCP_TOOLBOX_URL env var, load tools, append to orchestration_agent.

  Failure modes (missing URL, network errors, auth errors) are caught and
  logged; the agent continues with its existing stub tools rather than
  crashing set_up().
  """
  if getattr(orchestration_agent, "_mcp_tools_attached", False):
    return
  orchestration_agent._mcp_tools_attached = True

  url = os.environ.get("MCP_TOOLBOX_URL")
  if not url:
    logging.info(
        "MCP_TOOLBOX_URL not set; agent will run with stub tools only. "
        "Deploy MCP Toolbox via `make deploy-mcp` to enable real data access."
    )
    return
  try:
    tools = _load_mcp_toolbox_tools(url)
  except Exception as e:
    logging.warning(
        f"Failed to load MCP Toolbox tools from {url}: {e}. "
        "Agent will continue with stub tools."
    )
    return
  orchestration_agent.tools.extend(tools)
  logging.info(
      f"Loaded {len(tools)} tool(s) from MCP Toolbox at {url}: "
      f"{[getattr(t, 'name', repr(t)) for t in tools]}"
  )


def _wrap_session_service_for_auto_create(session_service: Any) -> None:
  """Patch ``create_session`` to ignore client-supplied ``session_id``.

  The runner's ``_get_or_create_session`` (when ``auto_create_session=True``)
  forwards the stale client-supplied ``session_id`` into
  ``session_service.create_session(session_id=<stale-id>)``. With
  ``VertexAiSessionService``, that becomes a POST to the Vertex AI
  sessions.create REST endpoint with ``{"session_id": "<stale-id>"}`` —
  the server doesn't accept client-minted IDs (it assigns its own) and
  rejects the request with a 400 ``ClientError``. We patch the instance's
  ``create_session`` to drop the kwarg before delegating, so the server
  mints a fresh ID. The response includes the new session_id; well-behaved
  clients pick it up from the response and use it on subsequent calls.
  """
  if session_service is None:
    return
  original = session_service.create_session

  async def _create_session_ignore_id(
      *, app_name: str, user_id: str, session_id: Any = None, **kwargs: Any
  ) -> Any:
    if session_id:
      logging.info(
          "Ignoring client-supplied session_id=%s on create_session — "
          "Vertex AI mints its own; a fresh session will be created.",
          session_id,
      )
    return await original(app_name=app_name, user_id=user_id, **kwargs)

  session_service.create_session = _create_session_ignore_id


class AgentEngineApp(AdkApp):

  def set_up(self) -> None:
    """Initialize the agent engine app with logging, telemetry, and MCP tools."""
    project_id = resolve_project_id()
    vertexai.init(project=project_id)
    setup_telemetry()
    _attach_mcp_tools()
    super().set_up()
    # The Vertex AI AdkApp template constructs Runner without passing
    # auto_create_session, so it defaults to False — meaning a client that
    # sends a session_id that doesn't exist on this revision gets a hard
    # SessionNotFoundError instead of having the session created on demand.
    # That's user-hostile for our usage pattern (UIs and clients that
    # cache session_ids across redeploys, or just skip create_session
    # entirely). Flip the flag so missing sessions get auto-created — and
    # wrap session_service.create_session so it doesn't pass the stale
    # client-supplied session_id back into Vertex AI's API, which rejects
    # caller-minted IDs.
    runner = self._tmpl_attrs.get("runner")
    if runner is not None:
      runner.auto_create_session = True
      _wrap_session_service_for_auto_create(runner.session_service)
    logging.basicConfig(level=logging.INFO)
    logging_client = google_cloud_logging.Client()
    self.logger = logging_client.logger(__name__)

  def register_feedback(self, feedback: dict[str, Any]) -> None:
    """Collect and log feedback."""
    feedback_obj = Feedback.model_validate(feedback)
    self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

  def register_operations(self) -> dict[str, list[str]]:
    """Registers the operations of the Agent."""
    operations = super().register_operations()
    operations[""] = operations.get("", []) + ["register_feedback"]
    return operations


logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
agent_engine = AgentEngineApp(
    app=adk_app,
    artifact_service_builder=lambda: (
        GcsArtifactService(bucket_name=logs_bucket_name)
        if logs_bucket_name
        else InMemoryArtifactService()
    ),
)
