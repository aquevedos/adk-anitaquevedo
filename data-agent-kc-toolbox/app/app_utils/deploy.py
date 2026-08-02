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

import asyncio
import datetime
import importlib
import inspect
import json
import logging
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any
import warnings

import click
import google.auth
from google.cloud import resourcemanager_v3
from google.iam.v1 import iam_policy_pb2, policy_pb2
import vertexai
from vertexai._genai import _agent_engines_utils
from vertexai._genai.types import AgentEngine, AgentEngineConfig, IdentityType
import yaml

# Suppress google-cloud-storage version compatibility warning
warnings.filterwarnings(
    "ignore", category=FutureWarning, module="google.cloud.aiplatform"
)

METADATA_FILE = "deployment_metadata.json"
DEFAULT_MCP_IMAGE = (
    "us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest"
)


def _metadata_path(variant: str | None) -> str:
  """Per-variant metadata file path. No variant → `deployment_metadata.json`.

  Variants live alongside the default file:
  `deployment_metadata.<variant>.json`.
  This isolates agent ↔ MCP deploy handoff per variant so multiple variants
  (with-dataplex / no-dataplex / with-spanner / etc.) can coexist in one
  workspace without clobbering each other.
  """
  if not variant:
    return METADATA_FILE
  return f"deployment_metadata.{variant}.json"


# ============================================================================
# Shared helpers
# ============================================================================


def parse_key_value_pairs(kv_string: str | None) -> dict[str, str]:
  """Parse key-value pairs from a comma-separated KEY=VALUE string."""
  result = {}
  if kv_string:
    for pair in kv_string.split(","):
      if "=" in pair:
        key, value = pair.split("=", 1)
        result[key.strip()] = value.strip()
      else:
        logging.warning(f"Skipping malformed key-value pair: {pair}")
  return result


def parse_secrets(secrets_string: str | None) -> dict[str, dict[str, str]]:
  """Parse secrets from ENV_VAR=SECRET_ID or ENV_VAR=SECRET_ID:VERSION format."""
  raw = parse_key_value_pairs(secrets_string)
  result: dict[str, dict[str, str]] = {}
  for key, spec in raw.items():
    if ":" not in spec:
      secret_id, version = spec, "latest"
    else:
      secret_id, _, version = spec.rpartition(":")
    result[key] = {"secret": secret_id, "version": version}
  return result


def format_env_value(value: Any) -> str:
  """Format an env var value for display, masking secrets."""
  if isinstance(value, dict) and "secret" in value and "version" in value:
    return f"[secret:{value['secret']}:{value['version']}]"
  return str(value)


def _read_metadata(path: str = METADATA_FILE) -> dict[str, Any]:
  """Read a deployment-metadata file. Returns {} if missing or unparseable."""
  p = Path(path)
  if not p.exists():
    return {}
  try:
    return json.loads(p.read_text())
  except (json.JSONDecodeError, OSError):
    logging.warning(f"Could not parse {path}; treating as empty.")
    return {}


def _merge_metadata(updates: dict[str, Any], path: str = METADATA_FILE) -> None:
  """Merge updates into a deployment-metadata file without clobbering other keys."""
  existing = _read_metadata(path)
  existing.update(updates)
  Path(path).write_text(json.dumps(existing, indent=2) + "\n")


# ============================================================================
# Agent Engine deploy helpers
# ============================================================================


def generate_class_methods_from_agent(
    agent_instance: Any,
) -> list[dict[str, Any]]:
  """Generate method specifications with schemas from agent's register_operations().

  See:
  https://docs.cloud.google.com/agent-builder/agent-engine/use/custom#supported-operations
  """
  registered_operations = _agent_engines_utils._get_registered_operations(
      agent=agent_instance
  )
  class_methods_spec = (
      _agent_engines_utils._generate_class_methods_spec_or_raise(
          agent=agent_instance,
          operations=registered_operations,
      )
  )
  class_methods_list = [
      _agent_engines_utils._to_dict(method_spec)
      for method_spec in class_methods_spec
  ]
  return class_methods_list


def write_deployment_metadata(
    remote_agent: Any,
    service_account: str | None = None,
    metadata_file: str = METADATA_FILE,
) -> None:
  """Persist agent engine info to a deployment-metadata file (merges with existing)."""
  updates: dict[str, Any] = {
      "remote_agent_engine_id": remote_agent.api_resource.name,
      "deployment_target": "agent_engine",
      "is_a2a": False,
      "deployment_timestamp": datetime.datetime.now().isoformat(),
  }
  if service_account is None:
    service_account = getattr(
        remote_agent.api_resource.spec, "service_account", None
    )
  if service_account:
    updates["service_account"] = service_account
  _merge_metadata(updates, path=metadata_file)
  logging.info(f"Agent Engine metadata written to {metadata_file}")


def print_deployment_success(
    remote_agent: Any,
    location: str,
    project: str,
) -> None:
  """Print deployment success message with console URL."""
  resource_name_parts = remote_agent.api_resource.name.split("/")
  agent_engine_id = resource_name_parts[-1]
  project_number = resource_name_parts[1]
  print("\n✅ Deployment successful!")
  service_account = remote_agent.api_resource.spec.service_account
  if service_account:
    print(f"Service Account: {service_account}")
  else:
    default_sa = (
        f"service-{project_number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
    )
    print(f"Service Account: {default_sa}")
  playground_url = f"https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/{location}/agent-engines/{agent_engine_id}/playground?project={project}"
  print(f"\n📊 Open Console Playground: {playground_url}\n")


def _grant_agent_runtime_roles(project: str, sa_email: str) -> None:
  """Grant the Agent Engine runtime SA the IAM roles required by the agent's tools.

  The default Vertex AI Agent Engine service agent
  (``service-{project_number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com``)
  has framework-level permissions but **not** the downstream-service
  permissions the agent actually needs at runtime. Without these you get
  403s like:

    - ``User does not have permission to chat.`` (Conversational Analytics)
    - ``PERMISSION_DENIED`` reading BigQuery tables / running jobs
    - ``PERMISSION_DENIED`` reading Dataplex catalog entries

  The set below is what's needed for the current agent surface:
    Conversational Analytics
    (https://docs.cloud.google.com/gemini/data-agents/conversational-analytics-api/access-control):
    - ``geminidataanalytics.dataAgentStatelessUser`` → call CA's chat
      endpoint with inline_context (the path ``_call_legacy_ca_toolbox``
      takes by default; this was the role missing in the 403)
    - ``geminidataanalytics.dataAgentCreator`` + ``dataAgentUser`` →
      only needed if ``USE_NEW_CA_TOOLBOX_FLOW=True`` (creates an ad-hoc
      DataAgent + Conversation before chatting). Granted defensively so
      the flag can be flipped without re-running IAM.
    BigQuery (via CA)
    - ``bigquery.user`` → run BQ jobs that CA generates on the caller's behalf
    - ``bigquery.dataViewer`` → read BQ tables underneath those jobs
    Dataplex Knowledge Catalog discovery agent
    (https://docs.cloud.google.com/dataplex/docs/use-discovery-agent):
    - ``dataplex.viewer`` → ``dataplex.projects.search`` for ``SearchEntries``
      plus all entry/catalog read perms. Replaces the narrower
      ``dataplex.catalogViewer`` which doesn't include the search permission.
    - ``aiplatform.user`` → discovery agent calls Vertex AI for ranking /
      embedding; needs ``aiplatform.endpoints.predict``.
    - ``serviceusage.serviceUsageConsumer`` → required for API consumption
      billing against the calling project.
    Telemetry
    - ``cloudtrace.agent`` → silences the "Failed to export span batch
      code: 403, reason: Forbidden" log spam from the Agent Engine
      framework's built-in OTEL trace exporter. The framework pushes spans
      regardless of our setup_telemetry() opt-in, so the SA needs write
      access to Cloud Trace.

  Idempotent (re-runs are no-ops on already-bound role+member pairs).
  """
  roles = [
      "roles/geminidataanalytics.dataAgentStatelessUser",
      "roles/geminidataanalytics.dataAgentCreator",
      "roles/geminidataanalytics.dataAgentUser",
      "roles/bigquery.user",
      "roles/bigquery.dataViewer",
      "roles/dataplex.viewer",
      "roles/aiplatform.user",
      "roles/serviceusage.serviceUsageConsumer",
      "roles/cloudtrace.agent",
  ]
  click.echo(
      f"\n🔐 Granting agent runtime SA the IAM roles it needs to call tools"
  )
  _grant_project_roles(project, sa_email, roles)


def _resolve_agent_service_account(
    remote_agent: Any,
    cli_override: str | None,
) -> str:
  """Resolve the SA that the deployed agent actually runs as.

  Priority: explicit CLI override > what the API returned > default Vertex AI
  SA.
  """
  if cli_override:
    return cli_override
  sa = getattr(remote_agent.api_resource.spec, "service_account", None)
  if sa:
    return sa
  project_number = remote_agent.api_resource.name.split("/")[1]
  return (
      f"service-{project_number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
  )


def setup_agent_identity(client: Any, project: str, display_name: str) -> Any:
  """Create agent with identity and grant required IAM roles."""
  click.echo(f"\n🔧 Creating agent identity for: {display_name}")
  agent = client.agent_engines.create(
      config={
          "identity_type": IdentityType.AGENT_IDENTITY,
          "display_name": display_name,
      }
  )

  roles = [
      "roles/aiplatform.user",
      "roles/serviceusage.serviceUsageConsumer",
      "roles/browser",
      "roles/cloudapiregistry.viewer",
      "roles/logging.logWriter",
      "roles/monitoring.metricWriter",
  ]
  principal = f"principal://{agent.api_resource.spec.effective_identity}"
  click.echo(f"🔐 Granting IAM roles to: {principal}")
  proj_client = resourcemanager_v3.ProjectsClient()
  policy = proj_client.get_iam_policy(
      request=iam_policy_pb2.GetIamPolicyRequest(resource=f"projects/{project}")
  )
  for role in roles:
    policy.bindings.append(policy_pb2.Binding(role=role, members=[principal]))
  proj_client.set_iam_policy(
      request=iam_policy_pb2.SetIamPolicyRequest(
          resource=f"projects/{project}", policy=policy
      )
  )
  click.echo("  ✅ Agent identity ready")
  return agent


# ============================================================================
# CLI group
# ============================================================================


@click.group()
def cli():
  """Deployment commands for data-agent-kc-toolbox.

  Subcommands:
    agent        — deploy the agent to Vertex AI Agent Engine
    mcp-toolbox  — deploy MCP Toolbox as a Cloud Run sidecar
  """
  pass


# ============================================================================
# `agent` subcommand (formerly the single top-level command)
# ============================================================================


@cli.command("agent")
@click.option(
    "--project",
    default=None,
    help="GCP project ID (defaults to application default credentials)",
)
@click.option(
    "--location",
    default=None,
    help=(
        "GCP region (defaults to `gcloud config get-value compute/region` if"
        " set, else us-central1)"
    ),
)
@click.option(
    "--display-name",
    default="data-agent-kc",
    help="Display name for the agent engine",
)
@click.option(
    "--description",
    default="Simple ReAct agent",
    help="Description of the agent",
)
@click.option(
    "--source-packages",
    multiple=True,
    default=["./app"],
    help="Source packages to deploy. Can be specified multiple times.",
)
@click.option(
    "--entrypoint-module",
    default="app.ca_toolbox_engine_app",
    help="Python module path for the agent entrypoint (required)",
)
@click.option(
    "--entrypoint-object",
    default="agent_engine",
    help="Name of the agent instance at module level (required)",
)
@click.option(
    "--requirements-file",
    default="app/app_utils/.requirements.txt",
    help="Path to requirements.txt file",
)
@click.option(
    "--set-env-vars",
    default=None,
    help="Comma-separated list of environment variables in KEY=VALUE format",
)
@click.option(
    "--set-secrets",
    default=None,
    help=(
        "Comma-separated secrets: ENV_VAR=SECRET_ID or"
        " ENV_VAR=SECRET_ID:VERSION"
    ),
)
@click.option(
    "--labels",
    default=None,
    help="Comma-separated list of labels in KEY=VALUE format",
)
@click.option(
    "--service-account",
    default=None,
    help="Service account email to use for the agent engine",
)
@click.option(
    "--min-instances",
    type=int,
    default=1,
    help="Minimum number of instances (default: 1)",
)
@click.option(
    "--max-instances",
    type=int,
    default=10,
    help="Maximum number of instances (default: 10)",
)
@click.option(
    "--cpu",
    default="4",
    help="CPU limit (default: 4)",
)
@click.option(
    "--memory",
    default="8Gi",
    help="Memory limit (default: 8Gi)",
)
@click.option(
    "--container-concurrency",
    type=int,
    default=9,
    help="Container concurrency (default: 9)",
)
@click.option(
    "--num-workers",
    type=int,
    default=1,
    help="Number of worker processes (default: 1)",
)
@click.option(
    "--agent-identity",
    is_flag=True,
    default=False,
    help=(
        "Enable agent identity for per-agent IAM access control (Preview"
        " feature)"
    ),
)
@click.option(
    "--variant",
    default=None,
    help=(
        "Variant suffix for deploying multiple coexisting agent versions. "
        "If --display-name is left at its default, it becomes "
        "'data-agent-kc-<variant>'. The metadata file becomes "
        "'deployment_metadata.<variant>.json' so this variant's "
        "MCP-handoff stays isolated from other variants."
    ),
)
@click.option(
    "--metadata-file",
    default=None,
    help=(
        "Explicit path to the deployment-metadata JSON file. Overrides the "
        "value derived from --variant. Default: 'deployment_metadata.json'."
    ),
)
def deploy_agent_engine_app(
    project: str | None,
    location: str | None,
    display_name: str,
    description: str,
    source_packages: tuple[str, ...],
    entrypoint_module: str,
    entrypoint_object: str,
    requirements_file: str,
    set_env_vars: str | None,
    set_secrets: str | None,
    labels: str | None,
    service_account: str | None,
    min_instances: int,
    max_instances: int,
    cpu: str,
    memory: str,
    container_concurrency: int,
    num_workers: int,
    agent_identity: bool,
    variant: str | None,
    metadata_file: str | None,
) -> AgentEngine:
  """Deploy the agent engine app to Vertex AI."""

  logging.basicConfig(level=logging.INFO)
  logging.getLogger("httpx").setLevel(logging.WARNING)

  # Resolve project + location defaults before they're stuffed into env_vars
  # or printed in the banner. Without this, --location omitted → None → the
  # Vertex AI SDK rejects the env var with "Unknown value type ... must be
  # a str or SecretRef: None".
  if not project:
    _, project = google.auth.default()
  if not location:
    location = _default_location()

  # Resolve variant-aware defaults. Explicit --display-name / --metadata-file
  # always win over variant-derived ones.
  if variant and display_name == "data-agent-kc":
    display_name = f"data-agent-kc-{variant}"
  effective_metadata_file = metadata_file or _metadata_path(variant)
  if variant:
    click.echo(f"\n🏷️  Variant: {variant}")
    click.echo(f"    Display name: {display_name}")
    click.echo(f"    Metadata file: {effective_metadata_file}")

  env_vars: dict[str, Any] = parse_key_value_pairs(set_env_vars)
  secrets = parse_secrets(set_secrets)
  labels_dict = parse_key_value_pairs(labels)

  env_vars.update(secrets)  # type: ignore

  env_vars["GOOGLE_CLOUD_REGION"] = location
  env_vars["NUM_WORKERS"] = str(num_workers)
  env_vars.setdefault("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true")
  env_vars.setdefault(
      "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true"
  )
  # Bake the alphabetic customer project ID into the runtime. Agent Engine's
  # GOOGLE_CLOUD_PROJECT carries the project NUMBER, and the metadata server
  # returns the Google-managed tenant project ID (`*-tp` suffix) — neither
  # is usable for Dataplex's projectid:(...) search predicate. Setting these
  # explicitly avoids a Resource Manager IAM lookup at runtime.
  env_vars.setdefault("AGENT_PROJECT_ID", project)
  env_vars.setdefault("DATAPLEX_CATALOG_PROJECT", project)

  # Pick up MCP Toolbox URL recorded by a prior `make deploy-mcp` (for the
  # same variant) so the agent runtime can connect to it. If absent, the
  # agent runs with stub tools only — no failure.
  metadata = _read_metadata(effective_metadata_file)
  mcp_url = metadata.get("mcp_toolbox_url")
  if mcp_url:
    env_vars["MCP_TOOLBOX_URL"] = mcp_url
    click.echo(
        f"\n🔗 Found MCP Toolbox URL in {effective_metadata_file}: {mcp_url}"
    )
  else:
    click.echo(
        f"\n⚠️  No mcp_toolbox_url in {effective_metadata_file}; "
        "agent will run without MCP tools."
    )

  print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🤖 DEPLOYING AGENT TO VERTEX AI AGENT ENGINE 🤖         ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

  click.echo("\n📋 Deployment Parameters:")
  params = [
      ("Project", project),
      ("Location", location),
      ("Display Name", display_name),
      ("Min Instances", min_instances),
      ("Max Instances", max_instances),
      ("CPU", cpu),
      ("Memory", memory),
      ("Container Concurrency", container_concurrency),
  ]
  if service_account:
    params.append(("Service Account", service_account))
  if agent_identity:
    params.append(("Agent Identity", "Enabled (Preview)"))
  for name, value in params:
    click.echo(f"  {name}: {value}")
  if env_vars:
    click.echo("\n🌍 Environment Variables:")
    for key, value in sorted(env_vars.items()):
      click.echo(f"  {key}: {format_env_value(value)}")

  source_packages_list = list(source_packages)

  _ensure_apis_enabled(project, ["aiplatform.googleapis.com"])

  http_options = {"api_version": "v1beta1"} if agent_identity else None
  client = vertexai.Client(
      project=project,
      location=location,
      http_options=http_options,
  )
  vertexai.init(project=project, location=location)

  logging.info(f"Importing {entrypoint_module}.{entrypoint_object}")
  module = importlib.import_module(entrypoint_module)
  agent_instance = getattr(module, entrypoint_object)

  if inspect.iscoroutine(agent_instance):
    logging.info(f"Detected coroutine, awaiting {entrypoint_object}...")
    agent_instance = asyncio.run(agent_instance)
  class_methods_list = generate_class_methods_from_agent(agent_instance)

  config = AgentEngineConfig(
      display_name=display_name,
      description=description,
      source_packages=source_packages_list,
      entrypoint_module=entrypoint_module,
      entrypoint_object=entrypoint_object,
      class_methods=class_methods_list,
      env_vars=env_vars,
      service_account=service_account,
      requirements_file=requirements_file,
      labels=labels_dict,
      min_instances=min_instances,
      max_instances=max_instances,
      resource_limits={"cpu": cpu, "memory": memory},
      container_concurrency=container_concurrency,
      agent_framework="google-adk",
      identity_type=IdentityType.AGENT_IDENTITY if agent_identity else None,
  )

  existing_agents = list(_retry_on_service_disabled(client.agent_engines.list))
  matching_agents = [
      agent
      for agent in existing_agents
      if agent.api_resource.display_name == display_name
  ]

  if agent_identity and not matching_agents:
    matching_agents = [setup_agent_identity(client, project, display_name)]

  action = "Updating" if matching_agents else "Creating"
  click.echo(
      f"\n🚀 {action} agent: {display_name} (this can take 3-5 minutes)..."
  )

  if matching_agents:
    remote_agent = client.agent_engines.update(
        name=matching_agents[0].api_resource.name, config=config
    )
  else:
    remote_agent = client.agent_engines.create(config=config)

  if set_secrets is not None and not secrets and matching_agents:
    clear_op = client.agent_engines._update(
        name=remote_agent.api_resource.name,
        config={
            "spec": {"deployment_spec": {"secret_env": []}},
            "update_mask": "spec.deployment_spec.secret_env",
        },
    )
    _agent_engines_utils._await_operation(
        operation_name=clear_op.name,
        get_operation_fn=client.agent_engines._get_agent_operation,
    )

  actual_sa = _resolve_agent_service_account(remote_agent, service_account)
  _grant_agent_runtime_roles(project, actual_sa)
  write_deployment_metadata(
      remote_agent,
      service_account=actual_sa,
      metadata_file=effective_metadata_file,
  )
  print_deployment_success(remote_agent, location, project)

  return remote_agent


# ============================================================================
# MCP Toolbox deploy helpers
# ============================================================================


def _run_gcloud(
    args: list[str], check: bool = True
) -> subprocess.CompletedProcess:
  """Run a gcloud subprocess. Streams stdout/stderr to the terminal."""
  cmd = ["gcloud"] + args
  logging.info(f"$ {' '.join(cmd)}")
  return subprocess.run(cmd, check=check, text=True)


def _default_location() -> str:
  """Resolve the default deploy region for the agent and toolbox.

  Mirrors how project defaulting works — if the operator has set
  ``gcloud config set compute/region``, we deploy to that region. Otherwise
  fall back to ``us-central1``. Keeping the agent and the MCP toolbox in
  the same region matters because they communicate via Cloud Run private
  networking, and Vertex AI Agent Engine resources are regional.
  """
  try:
    result = subprocess.run(
        ["gcloud", "config", "get-value", "compute/region"],
        capture_output=True,
        text=True,
        check=False,
    )
    value = (result.stdout or "").strip()
    if value and value != "(unset)":
      return value
  except Exception:
    pass
  return "us-central1"


def _gcloud_check_exists(args: list[str]) -> bool:
  """Run a `gcloud ... describe` and return True if exit code 0."""
  result = subprocess.run(
      ["gcloud"] + args,
      capture_output=True,
      text=True,
  )
  return result.returncode == 0


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
  """Parse manifest.yaml and return its contents."""
  if not manifest_path.exists():
    raise click.ClickException(f"Manifest not found: {manifest_path}")
  data = yaml.safe_load(manifest_path.read_text())
  if not isinstance(data, dict) or "sources" not in data:
    raise click.ClickException(
        f"Manifest {manifest_path} must contain a top-level 'sources:' key."
    )
  return data


def _validate_and_compose(
    manifest: dict[str, Any],
    manifest_dir: Path,
    env_vars: dict[str, str],
) -> tuple[str, list[str], list[str], list[str], list[dict[str, Any]]]:
  """Validate enabled sources and compose them into a single tools.yaml.

  Returns:
      composed_yaml: full tools.yaml content (with optional authService
      prepended).
      iam_roles: deduplicated project-level roles to grant to toolbox-identity.
      apis: deduplicated GCP APIs to enable.
      required_env: deduplicated env vars that must be set on Cloud Run.
      summaries: per-source info for logging.
  """
  sources = manifest.get("sources", {})
  enabled = [(name, cfg) for name, cfg in sources.items() if cfg.get("enabled")]
  if not enabled:
    raise click.ClickException(
        "No sources are enabled in manifest.yaml. Set at least one to enabled:"
        " true."
    )

  composed_parts: list[str] = []
  all_iam_roles: set[str] = set()
  all_apis: set[str] = set()
  all_required_env: set[str] = set()
  needs_auth_service = False
  summaries: list[dict[str, Any]] = []

  for name, cfg in enabled:
    # Per-source mode check
    mode = cfg.get("client_auth_mode", "service_account")
    if mode not in {"service_account", "end_user", "hybrid"}:
      raise click.ClickException(
          f"Invalid client_auth_mode '{mode}' for source '{name}'. "
          "Must be one of: service_account, end_user, hybrid."
      )
    if mode != "service_account":
      needs_auth_service = True

    all_required_env.update(cfg.get("required_env", []))
    all_iam_roles.update(cfg.get("iam_roles", []))
    all_apis.update(cfg.get("apis", []))

    fragment_path = manifest_dir / cfg["file"]
    if not fragment_path.exists():
      raise click.ClickException(
          f"Source fragment not found: {fragment_path} (for source '{name}')"
      )
    composed_parts.append(
        f"# === source: {name} (mode: {mode}) ===\n" + fragment_path.read_text()
    )

    summaries.append({"name": name, "client_auth_mode": mode})

  # Validate required_env
  missing = sorted(k for k in all_required_env if k not in env_vars)
  if missing:
    hint = " ".join(f"--set-env-vars {k}=..." for k in missing[:2])
    raise click.ClickException(
        f"Missing required env vars: {', '.join(missing)}\n"
        f"Pass them via --set-env-vars. Example: {hint}"
    )

  composed = "\n---\n".join(composed_parts)

  # Prepend Google authService if any source needs end-user delegation
  if needs_auth_service:
    auth_path = manifest_dir / "auth" / "google.yaml"
    if auth_path.exists():
      composed = (
          "# === authService: google ===\n"
          + auth_path.read_text()
          + "\n---\n"
          + composed
      )
    else:
      click.echo(
          f"⚠️  At least one source needs end-user auth but {auth_path} "
          "is missing; sources may fail to start."
      )

  return (
      composed,
      sorted(all_iam_roles),
      sorted(all_apis),
      sorted(all_required_env),
      summaries,
  )


def _ensure_apis_enabled(project: str, apis: list[str]) -> None:
  """Enable required GCP APIs idempotently (`gcloud services enable` is a no-op if already on)."""
  if not apis:
    return
  click.echo(f"\n🔌 Ensuring APIs enabled: {', '.join(apis)}")
  _run_gcloud(["services", "enable", *apis, "--project", project])


def _ensure_service_account(
    project: str, sa_name: str, display_name: str
) -> str:
  """Create the service account if absent. Returns its email."""
  sa_email = f"{sa_name}@{project}.iam.gserviceaccount.com"
  if _gcloud_check_exists(
      ["iam", "service-accounts", "describe", sa_email, "--project", project]
  ):
    click.echo(f"  ✅ Service account already exists: {sa_email}")
    return sa_email
  click.echo(f"  🔧 Creating service account: {sa_email}")
  _run_gcloud([
      "iam",
      "service-accounts",
      "create",
      sa_name,
      "--display-name",
      display_name,
      "--project",
      project,
  ])
  return sa_email


def _retry_on_service_disabled(func, max_wait_seconds: int = 180):
  """Call `func()`, retrying with backoff while it raises a SERVICE_DISABLED-style 403.

  Handles the propagation window after `gcloud services enable` returns but
  before the
  target API is actually queryable. Re-raises any other error immediately.
  """
  deadline = time.monotonic() + max_wait_seconds
  delay = 5
  while True:
    try:
      return func()
    except Exception as e:
      if "SERVICE_DISABLED" not in str(e) or time.monotonic() >= deadline:
        raise
      click.echo(f"  ⏳ API still propagating; retrying in {delay}s...")
      time.sleep(delay)
      delay = min(delay * 2, 30)


def _get_iam_policy_with_retry(
    proj_client: "resourcemanager_v3.ProjectsClient",
    resource: str,
):
  """Fetch a project IAM policy, retrying through API enablement propagation."""
  request = iam_policy_pb2.GetIamPolicyRequest(resource=resource)
  return _retry_on_service_disabled(
      lambda: proj_client.get_iam_policy(request=request)
  )


def _grant_project_roles(
    project: str, member_email: str, roles: list[str]
) -> None:
  """Grant project-level roles to a service account, idempotent on the role+member pair."""
  if not roles:
    return
  principal = f"serviceAccount:{member_email}"
  click.echo(f"\n🔐 Granting {len(roles)} role(s) to {principal}")

  proj_client = resourcemanager_v3.ProjectsClient()
  resource = f"projects/{project}"
  policy = _get_iam_policy_with_retry(proj_client, resource)

  changed = False
  for role in roles:
    existing = next((b for b in policy.bindings if b.role == role), None)
    if existing:
      if principal not in existing.members:
        existing.members.append(principal)
        changed = True
        click.echo(f"  + {role}")
      else:
        click.echo(f"  ✓ {role} (already bound)")
    else:
      policy.bindings.append(policy_pb2.Binding(role=role, members=[principal]))
      changed = True
      click.echo(f"  + {role}")

  if changed:
    proj_client.set_iam_policy(
        request=iam_policy_pb2.SetIamPolicyRequest(
            resource=resource, policy=policy
        )
    )
    click.echo("  ✅ Project IAM updated")
  else:
    click.echo("  ✅ Project IAM already up to date")


def _ensure_secret(project: str, secret_name: str, payload: str) -> None:
  """Create the secret if missing, then add a new version with the payload."""
  click.echo(f"\n🔑 Updating secret: {secret_name}")
  secret_exists = _gcloud_check_exists(
      ["secrets", "describe", secret_name, "--project", project]
  )
  if not secret_exists:
    click.echo(f"  🔧 Creating secret: {secret_name}")
    _run_gcloud([
        "secrets",
        "create",
        secret_name,
        "--replication-policy",
        "automatic",
        "--project",
        project,
    ])
  else:
    click.echo("  ✅ Secret already exists")

  with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
    f.write(payload)
    temp_path = f.name
  try:
    _run_gcloud([
        "secrets",
        "versions",
        "add",
        secret_name,
        "--data-file",
        temp_path,
        "--project",
        project,
    ])
    click.echo("  ✅ New secret version added")
  finally:
    os.unlink(temp_path)


def _deploy_cloud_run_service(
    project: str,
    location: str,
    service_name: str,
    image: str,
    service_account_email: str,
    secret_name: str,
    env_vars: dict[str, str],
) -> str:
  """Deploy or update the toolbox Cloud Run service. Returns the service URL."""
  click.echo(
      f"\n🚀 Deploying Cloud Run service: {service_name} "
      "(this can take 1-3 minutes)"
  )
  env_kv = ",".join(f"{k}={v}" for k, v in sorted(env_vars.items()))
  container_args = "--config=/app/tools.yaml,--address=0.0.0.0,--port=8080"

  args = [
      "run",
      "deploy",
      service_name,
      "--image",
      image,
      "--region",
      location,
      "--project",
      project,
      "--service-account",
      service_account_email,
      "--no-allow-unauthenticated",
      "--port",
      "8080",
      "--set-secrets",
      f"/app/tools.yaml={secret_name}:latest",
      f"--args={container_args}",
      "--quiet",
  ]
  if env_kv:
    args += ["--set-env-vars", env_kv]

  _run_gcloud(args)

  result = subprocess.run(
      [
          "gcloud",
          "run",
          "services",
          "describe",
          service_name,
          "--region",
          location,
          "--project",
          project,
          "--format",
          "value(status.url)",
      ],
      capture_output=True,
      text=True,
      check=True,
  )
  url = result.stdout.strip()
  click.echo(f"  ✅ Service URL: {url}")
  return url


def _predict_default_agent_sa(project: str) -> str | None:
  """Compute the default Vertex AI Agent Engine runtime SA from project number.

  The SA
  ``service-{project_number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com``
  is the Google-managed service agent for Reasoning Engine (the underlying
  name for Agent Engine). It's auto-provisioned when aiplatform.googleapis.com
  is enabled. Returns None if the project number can't be resolved.
  """
  try:
    result = subprocess.run(
        [
            "gcloud",
            "projects",
            "describe",
            project,
            "--format",
            "value(projectNumber)",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    project_number = result.stdout.strip()
    if not project_number:
      return None
    return (
        f"service-{project_number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
    )
  except subprocess.CalledProcessError:
    return None


def _grant_invoker(
    project: str,
    location: str,
    service_name: str,
    member_email: str | None,
) -> None:
  """Grant roles/run.invoker on the Cloud Run service to a service account.

  Soft-fails: a missing-principal error (which happens for the default Agent
  Engine SA before the agent has ever been deployed) is surfaced as a clear
  warning rather than aborting the whole MCP deploy. Re-running after
  ``make deploy`` retries the binding.
  """
  if not member_email:
    click.echo("\n⚠️  No invoker SA available; skipping run.invoker grant.")
    return
  principal = f"serviceAccount:{member_email}"
  click.echo(
      f"\n🔐 Granting roles/run.invoker on {service_name} to {principal}"
  )
  cmd = [
      "gcloud",
      "run",
      "services",
      "add-iam-policy-binding",
      service_name,
      "--region",
      location,
      "--member",
      principal,
      "--role",
      "roles/run.invoker",
      "--project",
      project,
      "--quiet",
  ]
  deadline = time.monotonic() + 120
  delay = 5
  while True:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
      click.echo("  ✅ Invoker granted")
      return
    stderr = result.stderr or ""
    if "does not exist" in stderr and time.monotonic() < deadline:
      click.echo(
          f"  ⏳ Service agent not yet visible in IAM; retrying in {delay}s..."
      )
      time.sleep(delay)
      delay = min(delay * 2, 30)
      continue
    click.echo(stderr.rstrip())
    click.echo(
        f"\n⚠️  Failed to grant invoker on {member_email}.\n"
        "    This is expected if the agent hasn't been deployed yet "
        "(its SA doesn't exist as a principal in IAM until first use).\n"
        "    Re-run `make deploy-mcp` after `make deploy` to retry — "
        "the agent SA from deployment_metadata.json takes precedence."
    )
    return


# ============================================================================
# `mcp-toolbox` subcommand
# ============================================================================


@cli.command("mcp-toolbox")
@click.option(
    "--project",
    default=None,
    help="GCP project ID (defaults to ADC project)",
)
@click.option(
    "--location",
    default=None,
    help=(
        "GCP region for Cloud Run (defaults to `gcloud config get-value "
        "compute/region` if set, else us-central1)"
    ),
)
@click.option(
    "--service-name",
    default="data-agent-mcp-toolbox",
    help="Cloud Run service name",
)
@click.option(
    "--service-account-name",
    default="toolbox-identity",
    help="Service account ID (not email) for the toolbox runtime",
)
@click.option(
    "--manifest",
    "manifest_path",
    default="app/mcp_toolbox/manifest.yaml",
    help="Path to manifest.yaml",
)
@click.option(
    "--secret-name",
    default="toolbox-tools-config",
    help="Secret Manager secret name for the composed tools.yaml",
)
@click.option(
    "--image",
    default=DEFAULT_MCP_IMAGE,
    help="MCP Toolbox container image (default: official prebuilt)",
)
@click.option(
    "--invoker-service-account",
    default=None,
    help=(
        "SA to grant roles/run.invoker on the service. Defaults to"
        f" {METADATA_FILE}:service_account (written by `deploy agent`)."
    ),
)
@click.option(
    "--set-env-vars",
    default=None,
    help=(
        "Comma-separated KEY=VALUE pairs forwarded to Cloud Run "
        "(e.g. SPANNER_INSTANCE=foo,SPANNER_DATABASE=bar)"
    ),
)
@click.option(
    "--compose-only",
    is_flag=True,
    default=False,
    help=(
        "Skip GCP operations — just compose tools.yaml from the manifest and "
        "write it to --output. Useful for running the toolbox locally."
    ),
)
@click.option(
    "--output",
    default="/tmp/tools.yaml",
    help="Output path for --compose-only (default: /tmp/tools.yaml).",
)
@click.option(
    "--variant",
    default=None,
    help=(
        "Variant suffix for deploying multiple coexisting toolbox versions."
        " When set, --service-name defaults to"
        " 'data-agent-mcp-toolbox-<variant>', --secret-name defaults to"
        " 'toolbox-tools-config-<variant>', and the metadata file becomes"
        " 'deployment_metadata.<variant>.json'. The toolbox-identity SA is"
        " shared across variants by default."
    ),
)
@click.option(
    "--metadata-file",
    default=None,
    help=(
        "Explicit path to the deployment-metadata JSON file. Overrides the "
        "value derived from --variant. Default: 'deployment_metadata.json'."
    ),
)
def deploy_mcp_toolbox(
    project: str | None,
    location: str | None,
    service_name: str,
    service_account_name: str,
    manifest_path: str,
    secret_name: str,
    image: str,
    invoker_service_account: str | None,
    set_env_vars: str | None,
    compose_only: bool,
    output: str,
    variant: str | None,
    metadata_file: str | None,
) -> None:
  """Deploy MCP Toolbox to Cloud Run with sources composed from manifest.yaml."""
  logging.basicConfig(level=logging.INFO)
  logging.getLogger("httpx").setLevel(logging.WARNING)

  if not project:
    _, project = google.auth.default()
  if not location:
    location = _default_location()

  # Resolve variant-aware defaults. Explicit flags always win over
  # variant-derived values.
  if variant:
    if service_name == "data-agent-mcp-toolbox":
      service_name = f"data-agent-mcp-toolbox-{variant}"
    if secret_name == "toolbox-tools-config":
      secret_name = f"toolbox-tools-config-{variant}"
  effective_metadata_file = metadata_file or _metadata_path(variant)

  print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🧰 DEPLOYING MCP TOOLBOX TO CLOUD RUN 🧰                ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

  click.echo("\n📋 Parameters:")
  if variant:
    click.echo(f"  Variant: {variant}")
    click.echo(f"  Metadata file: {effective_metadata_file}")
  click.echo(f"  Project: {project}")
  click.echo(f"  Location: {location}")
  click.echo(f"  Service: {service_name}")
  click.echo(f"  Secret: {secret_name}")
  click.echo(f"  Manifest: {manifest_path}")
  click.echo(f"  Image: {image}")

  manifest_p = Path(manifest_path)
  manifest = _load_manifest(manifest_p)
  manifest_dir = manifest_p.parent

  # PROJECT_ID is auto-supplied. User can override or add more via --set-env-vars.
  env_vars: dict[str, str] = {"PROJECT_ID": project}
  env_vars.update(parse_key_value_pairs(set_env_vars))

  composed_yaml, iam_roles, apis, required_env, summaries = (
      _validate_and_compose(manifest, manifest_dir, env_vars)
  )

  click.echo(
      f"\n📦 Composed tools.yaml from {len(summaries)} enabled source(s):"
  )
  for s in summaries:
    click.echo(f"  - {s['name']} (mode: {s['client_auth_mode']})")

  if compose_only:
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(composed_yaml)
    click.echo(f"\n✅ Wrote composed tools.yaml to {out}")
    click.echo(
        "    Run the toolbox locally:\n      docker run --rm -p 5001:5001 \\\n"
        f"        --user 0 \\\n        -v {out}:/app/tools.yaml \\\n        -v"
        " ~/.config/gcloud:/root/.config/gcloud \\\n        -e"
        f" PROJECT_ID={project} \\\n        -e"
        " GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json"
        f" \\\n        {DEFAULT_MCP_IMAGE} \\\n        --config=/app/tools.yaml"
        " --address=0.0.0.0 --port=5001"
    )
    return

  # Always-on infra APIs + per-source APIs
  infra_apis = [
      "run.googleapis.com",
      "secretmanager.googleapis.com",
      "iam.googleapis.com",
      "cloudresourcemanager.googleapis.com",
      "aiplatform.googleapis.com",
  ]
  all_apis = sorted(set(apis) | set(infra_apis))
  _ensure_apis_enabled(project, all_apis)

  sa_email = _ensure_service_account(
      project,
      service_account_name,
      display_name="MCP Toolbox service identity",
  )

  all_roles = sorted(set(iam_roles) | {"roles/secretmanager.secretAccessor"})
  _grant_project_roles(project, sa_email, all_roles)

  _ensure_secret(project, secret_name, composed_yaml)

  cloud_run_env = {
      k: v
      for k, v in env_vars.items()
      if k in required_env or k == "PROJECT_ID"
  }

  service_url = _deploy_cloud_run_service(
      project=project,
      location=location,
      service_name=service_name,
      image=image,
      service_account_email=sa_email,
      secret_name=secret_name,
      env_vars=cloud_run_env,
  )

  # Resolve invoker SA in priority order:
  #   1. Explicit --invoker-service-account flag
  #   2. service_account recorded in deployment_metadata.json (post agent deploy)
  #   3. Predicted default Vertex AI Agent Engine SA (from project number)
  # Case 3 enables a clean first-time setup: `make deploy-mcp` first, then
  # `make deploy`. If the agent later uses a non-default SA (--agent-identity
  # or --service-account), re-running `make deploy-mcp` after agent deploy
  # falls into case 2 and grants on the actual SA.
  invoker = invoker_service_account
  if not invoker:
    meta = _read_metadata(effective_metadata_file)
    invoker = meta.get("service_account")
    if invoker:
      click.echo(
          f"\n📖 Read invoker SA from {effective_metadata_file}: {invoker}"
      )
    else:
      invoker = _predict_default_agent_sa(project)
      if invoker:
        click.echo(
            f"\n🔮 Predicted default agent SA: {invoker}\n"
            "    (Re-run `make deploy-mcp` after `make deploy` if you "
            "use --agent-identity or --service-account on the agent.)"
        )
  _grant_invoker(project, location, service_name, invoker)

  _merge_metadata(
      {
          "mcp_toolbox_url": service_url,
          "mcp_toolbox_service_account": sa_email,
          "mcp_toolbox_deployment_timestamp": (
              datetime.datetime.now().isoformat()
          ),
      },
      path=effective_metadata_file,
  )

  click.echo(f"\n✅ MCP Toolbox deployed: {service_url}")
  click.echo(
      f"📝 URL written to {effective_metadata_file}; the next `make deploy`"
      " will pick it up and set MCP_TOOLBOX_URL on the agent."
  )


if __name__ == "__main__":
  cli()
