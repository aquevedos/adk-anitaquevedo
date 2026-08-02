# Copyright 2026 Google LLC

import logging
import os
import urllib.request

import google.auth


def get_user_credentials(tool_context):
  if hasattr(tool_context, "auth") and tool_context.auth:
    return tool_context.auth
  creds, _ = google.auth.default()
  return creds


def resolve_project_id() -> str:
  """Return the alphabetic Google Cloud project ID for the running container.

  Why this exists: Vertex AI Agent Engine populates ``GOOGLE_CLOUD_PROJECT``
  with the customer project **number**, not the alphabetic project ID. The
  number works for most resource paths but breaks anything that parses the
  value as a project *ID* — most importantly Dataplex's ``SearchEntries``
  API, whose ``projectid:(...)`` predicate matches the alphabetic ID stored
  on each entry. With the numeric value, the predicate matches zero entries
  and catalog-driven discovery fails silently.

  Resolution order is environment-aware:

    1. ``AGENT_PROJECT_ID`` env var. The deploy script sets this explicitly
       to the alphabetic customer project ID (which it knows from
       ``--project`` / ``gcloud config get-value project``). This is the
       most reliable signal on Agent Engine.
    2. ``GOOGLE_CLOUD_PROJECT`` env var if alphabetic. Cloud Run / CLI set
       it to the alphabetic ID; only Agent Engine sets it to the number.
    3. ``GOOGLE_CLOUD_PROJECT`` env var if numeric → convert via Resource
       Manager. Needs ``resourcemanager.projects.get`` (granted by
       ``roles/browser``); falls through to numeric on failure.
    4. GCE metadata server ``/project/project-id``. WARNING: in Agent
       Engine this returns the **tenant** project ID (Google-managed
       isolation project, ``*-tp`` suffix), which has nothing to do with
       the customer project — the agent SA has no permissions there.
       Only useful in plain Cloud Run / GCE.
    5. ``google.auth.default()`` as a last resort.
  """
  explicit = os.environ.get("AGENT_PROJECT_ID", "").strip()
  if explicit:
    return explicit

  env_value = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
  if env_value and not env_value.isdigit():
    return env_value
  if env_value and env_value.isdigit():
    try:
      from google.cloud import resourcemanager_v3

      client = resourcemanager_v3.ProjectsClient()
      project = client.get_project(name=f"projects/{env_value}")
      return project.project_id
    except Exception as e:
      logging.warning(
          f"GOOGLE_CLOUD_PROJECT={env_value} is numeric and Resource Manager"
          f" lookup failed ({e}); falling back to numeric — set"
          " AGENT_PROJECT_ID at deploy time to bypass this lookup."
      )
      return env_value

  try:
    req = urllib.request.Request(
        "http://metadata.google.internal/computeMetadata/v1/project/project-id",
        headers={"Metadata-Flavor": "Google"},
    )
    with urllib.request.urlopen(req, timeout=2) as resp:
      value = resp.read().decode().strip()
      if value and not value.endswith("-tp"):
        return value
  except Exception as e:
    logging.debug(f"Metadata server project-id lookup failed: {e}")

  try:
    _, default_project = google.auth.default()
    return default_project or ""
  except Exception:
    return ""


def is_local_mcp_url(url: str) -> bool:
  """True if URL points to a local MCP Toolbox instance.

  Local toolbox (typically `http://localhost:5001` from `docker run` or
  `go run .`) is not behind Cloud Run IAM and does NOT validate the
  `Authorization` header. Skipping the Google ID token avoids a noisy
  metadata-server call that fails for non-Google audiences.
  """
  return url.startswith(
      ("http://localhost", "http://127.0.0.1", "http://0.0.0.0")
  )


def get_end_user_token() -> str | None:
  """Return the end user's OAuth access token for MCP Toolbox delegation.

  The MCP Toolbox client uses this as the value of the
  ``X-Goog-User-Authorization`` header so that sources configured with
  ``client_auth_mode: end_user`` (and ``useClientOAuth`` in the source YAML)
  can call BigQuery / Dataplex / GCS as the end user instead of as the
  toolbox service account. When this returns ``None``, the caller
  (``ca_toolbox_engine_app._load_mcp_toolbox_tools``) omits the header
  entirely — toolbox-core 1.x doesn't drop None-valued headers itself, and
  aiohttp rejects them with a "Cannot serialize non-str key" TypeError on
  the next request.

  Today this returns ``None`` (or a test token via the env var below) because
  ADK's ``ToolContext`` does not expose the end user's identity or OAuth
  token; ``IdentityType.AGENT_IDENTITY`` only controls per-agent IAM, not
  user delegation. When ADK / Vertex AI Agent Engine adds a way to access the
  caller's token at tool-call time, populate this function — but note that
  today the caller resolves it once at startup, so per-request resolution
  will require revising the header plumbing too.

  Set ``_FAKE_USER_TOKEN_FOR_TESTING=<value>`` to inject a static token for
  integration-testing the wire-up before that upstream feature lands.
  """
  fake = os.environ.get("_FAKE_USER_TOKEN_FOR_TESTING")
  if fake:
    return fake
  return None
