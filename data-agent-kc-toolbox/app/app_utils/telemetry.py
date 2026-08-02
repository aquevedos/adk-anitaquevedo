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


def setup_telemetry() -> str | None:
  """Configure OpenTelemetry and GenAI telemetry with GCS upload.

  Telemetry is **opt-in**. The Agent Engine framework consults
  ``GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY`` at import time; when it's
  enabled but nothing consumes the data, the cost shows up as:
    - "telemetry enabled but proceeding without httpx/gRPC instrumentation"
      warnings at startup;
    - a ``Waiting for OTEL push...`` delay on every container shutdown
      (Cloud Run rolling deploys feel this on the *old* revision dying);
    - extra HTTP round-trips on first invocation as exporters initialize.

  Setting ``LOGS_BUCKET_NAME`` opts in to GenAI completion logging (auto-
  enables Agent Engine telemetry too). Setting
  ``GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true`` enables tracing only.
  Leave both unset to skip OTEL entirely.
  """
  bucket = os.environ.get("LOGS_BUCKET_NAME")
  capture_content = os.environ.get(
      "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
  )

  if bucket and capture_content != "false":
    # Logging requested → ensure the framework telemetry pipeline is on
    # too (the GenAI completion hook publishes through OTEL).
    os.environ.setdefault("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true")
    logging.info(
        "Prompt-response logging enabled - mode: NO_CONTENT (metadata only, no"
        " prompts/responses)"
    )
    os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = (
        "NO_CONTENT"
    )
    os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl")
    os.environ.setdefault(
        "OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload"
    )
    os.environ.setdefault(
        "OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental"
    )
    commit_sha = os.environ.get("COMMIT_SHA", "dev")
    os.environ.setdefault(
        "OTEL_RESOURCE_ATTRIBUTES",
        f"service.namespace=data-agent-kc,service.version={commit_sha}",
    )
    path = os.environ.get("GENAI_TELEMETRY_PATH", "completions")
    os.environ.setdefault(
        "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
        f"gs://{bucket}/{path}",
    )
  elif (
      os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "").lower()
      == "true"
  ):
    logging.info(
        "Agent Engine telemetry enabled (no GenAI completion logging)."
    )
  else:
    logging.info(
        "Telemetry disabled (no OTEL setup, no shutdown push). Enable by"
        " setting LOGS_BUCKET_NAME=gs://your-bucket (for completion logs) or"
        " GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true (tracing only)."
    )

  return bucket
