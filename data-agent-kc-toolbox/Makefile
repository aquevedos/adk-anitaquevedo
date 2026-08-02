
# ==============================================================================
# Installation & Setup
# ==============================================================================

# Install dependencies using uv package manager. Includes the `demo` extra
# so the markdown→PDF tooling used by demo-scripts/setup/40-create-pdfs.sh is
# available. The demo extra adds `markdown` + `weasyprint`; the latter needs
# pango/cairo system libraries:
#   macOS:  brew install pango
#   Linux:  apt-get install libpango-1.0-0 libpangoft2-1.0-0 libcairo2
# `uv export --no-dev` (used by `make deploy`) does not pull extras, so the
# deployed Agent Engine image stays lean.
install:
	uv sync --extra demo

# ==============================================================================
# Playground Targets
# ==============================================================================

# Launch CMI Data Governance Platform & Admin UI
ui: cmi-ui
cmi-ui:
	@echo "==============================================================================="
	@echo "| 🏢 Iniciando Plataforma de Gobierno de Datos CMI...                         |"
	@echo "|                                                                             |"
	@echo "| 🌐 Abre tu navegador en: http://localhost:8080                              |"
	@echo "|                                                                             |"
	@echo "| 🛡️ Panel de Control, Chat con Agente Especialista y Capa de Administración  |"
	@echo "==============================================================================="
	uv run uvicorn app.cmi_admin_api:app --host 0.0.0.0 --port 8080 --reload

# Launch local dev playground
playground:
	@echo "==============================================================================="
	@echo "| 🚀 Iniciando Agent Playground (ADK)...                                      |"
	@echo "|                                                                             |"
	@echo "| 🌐 Abre tu navegador en: http://localhost:8501                              |"
	@echo "|                                                                             |"
	@echo "| 🔍 Selecciona la carpeta 'app' para interactuar con el Agente CMI.         |"
	@echo "==============================================================================="
	uv run adk web . --port 8501 --reload_agents

# ==============================================================================
# Backend Deployment Targets
# ==============================================================================

# Helper for building a comma-joined --set-env-vars value from multiple
# command-line Make vars. Joining is needed because --set-env-vars takes a
# single comma-separated string of pairs, but Make variables come in
# separately. Today only DATAPLEX_ENABLED feeds this, but the pattern is kept
# so additional agent env vars can be added without restructuring.
_NULL :=
_SPACE := $(_NULL) $(_NULL)
_COMMA := ,
_AGENT_ENV_PAIRS := $(strip \
    $(if $(filter command line,$(origin DATAPLEX_ENABLED)),DATAPLEX_ENABLED=$(DATAPLEX_ENABLED)) \
)
_AGENT_ENV_VARS := $(subst $(_SPACE),$(_COMMA),$(_AGENT_ENV_PAIRS))

# Auto-select the MCP manifest based on DATAPLEX_ENABLED so a single flag
# configures both sides of the deploy. When Dataplex is on (default), the
# catalog provides table discovery and MCP is GCS-only. When Dataplex is off,
# MCP also ships BigQuery introspection tools so the LLM can find tables to
# hand to Conversational Analytics. Explicit MANIFEST= still wins — set it for
# custom variants (e.g. no-dataplex AND Spanner enabled).
ifeq ($(DATAPLEX_ENABLED),false)
  _DEFAULT_MANIFEST := app/mcp_toolbox/manifest-no-dataplex.yaml
else
  _DEFAULT_MANIFEST := app/mcp_toolbox/manifest.yaml
endif
_MANIFEST := $(if $(MANIFEST),$(MANIFEST),$(_DEFAULT_MANIFEST))

# Deploy the agent remotely
# Usage: make deploy [VARIANT=name] [DISPLAY_NAME=name] [AGENT_IDENTITY=true]
#                    [SECRETS="KEY=SECRET_ID,..."] [DATAPLEX_ENABLED=false]
#                    [LOCATION=region]
#   VARIANT=name           — deploy a named variant (suffix added to display name
#                            + isolated metadata file). Lets you coexist multiple
#                            agent versions (with-dataplex, no-dataplex, etc.).
#   DISPLAY_NAME=name      — explicit display-name override (wins over variant).
#   AGENT_IDENTITY=true    — enable per-agent IAM identity (Preview).
#   DATAPLEX_ENABLED=false — disable the Knowledge Catalog search/verify steps;
#                            agent dispatches directly to data tools. Also flips
#                            the default MCP manifest to manifest-no-dataplex.yaml
#                            (BigQuery introspection enabled) when `make deploy-mcp`
#                            or `make deploy-all` runs with the same flag.
#                            Default is true (Dataplex-driven 3-step orchestration).
#   LOCATION=region        — GCP region (default: `gcloud config get-value
#                            compute/region` if set, else us-central1). Used by
#                            both `deploy` and `deploy-mcp` so agent and toolbox
#                            land in the same region.
deploy:
	# Export dependencies to requirements file using uv export.
	(uv export --no-hashes --no-header --no-dev --no-emit-project --no-annotate > app/app_utils/.requirements.txt 2>/dev/null || \
	uv export --no-hashes --no-header --no-dev --no-emit-project > app/app_utils/.requirements.txt) && \
	uv run -m app.app_utils.deploy agent \
		--source-packages=./app \
		--entrypoint-module=app.ca_toolbox_engine_app \
		--entrypoint-object=agent_engine \
		--requirements-file=app/app_utils/.requirements.txt \
		$(if $(filter command line,$(origin VARIANT)),--variant="$(VARIANT)") \
		$(if $(DISPLAY_NAME),--display-name="$(DISPLAY_NAME)") \
		$(if $(AGENT_IDENTITY),--agent-identity) \
		$(if $(filter command line,$(origin SECRETS)),--set-secrets="$(SECRETS)") \
		$(if $(LOCATION),--location="$(LOCATION)") \
		$(if $(_AGENT_ENV_VARS),--set-env-vars="$(_AGENT_ENV_VARS)")

# Alias for 'make deploy' for backward compatibility
backend: deploy

# Deploy MCP Toolbox as a Cloud Run sidecar. Reads enabled sources from the
# manifest (default: app/mcp_toolbox/manifest.yaml, or
# manifest-no-dataplex.yaml when DATAPLEX_ENABLED=false). Can run before
# `make deploy` — the agent SA is predicted from the project number for the
# invoker grant.
# Usage: make deploy-mcp [VARIANT=name] [PROJECT=my-proj] [SERVICE_NAME=my-svc]
#                        [DATAPLEX_ENABLED=false] [MANIFEST=path] [LOCATION=region]
#                        [EXTRA_ENV="K1=V1,K2=V2"]
#   VARIANT=name           — deploy a named variant (suffix added to service & secret
#                            names + isolated metadata file). Use the SAME VARIANT on
#                            `make deploy` so the agent picks up this toolbox's URL.
#   DATAPLEX_ENABLED=false — auto-select manifest-no-dataplex.yaml (adds BQ
#                            introspection tools). Same flag as `make deploy`.
#   MANIFEST=path          — explicit override; wins over DATAPLEX_ENABLED-based
#                            auto-selection. Use for custom variants.
#   LOCATION=region        — GCP region for the toolbox Cloud Run service.
#                            Default: `gcloud config get-value compute/region` if
#                            set, else us-central1. Should match `make deploy`.
deploy-mcp:
	uv run -m app.app_utils.deploy mcp-toolbox \
		--manifest=$(_MANIFEST) \
		$(if $(filter command line,$(origin VARIANT)),--variant="$(VARIANT)") \
		$(if $(PROJECT),--project="$(PROJECT)") \
		$(if $(LOCATION),--location="$(LOCATION)") \
		$(if $(SERVICE_NAME),--service-name="$(SERVICE_NAME)") \
		$(if $(filter command line,$(origin EXTRA_ENV)),--set-env-vars="$(EXTRA_ENV)")

# Convenience target: deploy MCP Toolbox then the agent in one shot.
# Use this for first-time setup. For subsequent changes, run `make deploy` or
# `make deploy-mcp` individually depending on what changed.
deploy-all: deploy-mcp deploy

# ==============================================================================
# Local mode (run MCP Toolbox + agent locally for development)
# ==============================================================================

# Compose tools.yaml from the manifest and write to /tmp/tools.yaml.
# Manifest selection follows the same DATAPLEX_ENABLED-based defaulting as
# `make deploy-mcp` (override with MANIFEST=path). No GCP operations performed;
# safe to run without auth. The output file is what you mount into a
# locally-running MCP Toolbox container.
# Usage: make compose-mcp-local [DATAPLEX_ENABLED=false] [PROJECT=my-proj] [EXTRA_ENV="K=V,..."]
compose-mcp-local:
	uv run -m app.app_utils.deploy mcp-toolbox \
		--manifest=$(_MANIFEST) \
		--compose-only \
		--output=/tmp/tools.yaml \
		$(if $(PROJECT),--project="$(PROJECT)") \
		$(if $(filter command line,$(origin EXTRA_ENV)),--set-env-vars="$(EXTRA_ENV)")

# Compose + run the MCP Toolbox locally via Docker. Foreground; Ctrl+C to stop.
# Mounts your ADC credentials so the toolbox can call BQ/Dataplex/GCS as you.
# Listens on http://localhost:5001 (5000 is reserved by macOS AirPlay Receiver).
# In another terminal: `MCP_TOOLBOX_URL=http://localhost:5001 make playground`
# Usage: make local-mcp [PROJECT=my-proj] [PORT=5001] [EXTRA_ENV="K=V,..."]
local-mcp: compose-mcp-local
	@PORT=$${PORT:-5001}; \
	PROJECT_ID=$$(gcloud config get-value project 2>/dev/null); \
	echo "🧰 Starting local MCP Toolbox on http://localhost:$$PORT (PROJECT_ID=$$PROJECT_ID)"; \
	docker run --rm -p $$PORT:$$PORT \
		--user 0 \
		-v /tmp/tools.yaml:/app/tools.yaml \
		-v $$HOME/.config/gcloud:/root/.config/gcloud \
		-e PROJECT_ID=$$PROJECT_ID \
		-e GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
		us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest \
		--config=/app/tools.yaml --address=0.0.0.0 --port=$$PORT

# ==============================================================================
# Testing & Code Quality
# ==============================================================================

# Run unit and integration tests
test:
	uv sync --dev
	uv run pytest tests/unit && uv run pytest tests/integration

# ==============================================================================
# Agent Evaluation
# ==============================================================================

# Run agent evaluation using ADK eval
# Usage: make eval [EVALSET=tests/eval/evalsets/basic.evalset.json] [EVAL_CONFIG=tests/eval/eval_config.json]
eval:
	@echo "==============================================================================="
	@echo "| Running Agent Evaluation                                                    |"
	@echo "==============================================================================="
	uv sync --dev --extra eval
	uv run adk eval ./app $${EVALSET:-tests/eval/evalsets/basic.evalset.json} \
		$(if $(EVAL_CONFIG),--config_file_path=$(EVAL_CONFIG),$(if $(wildcard tests/eval/eval_config.json),--config_file_path=tests/eval/eval_config.json,))

# Run evaluation with all evalsets
eval-all:
	@echo "==============================================================================="
	@echo "| Running All Evalsets                                                        |"
	@echo "==============================================================================="
	@for evalset in tests/eval/evalsets/*.evalset.json; do \
		echo ""; \
		echo "▶ Running: $$evalset"; \
		$(MAKE) eval EVALSET=$$evalset || exit 1; \
	done
	@echo ""
	@echo "✅ All evalsets completed"

# Run code quality checks (codespell, ruff, ty)
lint:
	uv sync --dev --extra lint
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run ty check .

# ==============================================================================
# Gemini Enterprise Integration
# ==============================================================================

# Register the deployed agent to Gemini Enterprise
# Usage: make register-gemini-enterprise (interactive - will prompt for required details)
# For non-interactive use, set env vars: ID or GEMINI_ENTERPRISE_APP_ID (full GE resource name)
# Optional env vars: GEMINI_DISPLAY_NAME, GEMINI_DESCRIPTION, GEMINI_TOOL_DESCRIPTION, AGENT_ENGINE_ID
register-gemini-enterprise:
	@uvx agent-starter-pack@0.41.1 register-gemini-enterprise