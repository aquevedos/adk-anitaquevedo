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

"""Deploy ONLY the bigquery_agent to Agent Runtime with an Agent Identity.

This is a trimmed copy of the full lab's deploy.py, hardcoded to the single
agent this installer cares about. Run it from this directory (install.sh does
this for you):
    python3 deploy.py

The deployed agent is given a unique Agent Identity (a SPIFFE-based principal)
instead of sharing a service account. That principal starts with NO access to
your data, which is why BigQuery calls are denied until you grant it the
roles/bigquery.user and roles/bigquery.dataEditor roles (see README.md).

Optional environment variables (also read from a local .env):
    GOOGLE_CLOUD_LOCATION   Region for the agent (default: us-central1).
    MODEL                   Gemini model id (default: gemini-2.5-flash).
"""

import os
import sys

from dotenv import load_dotenv

import vertexai
from vertexai._genai import types

# Load .env (written by install.sh) so the project, location, and model are
# available both here and when the agent module is imported below.
load_dotenv()

PROJECT_ID = "qwiklabs-gcp-01-49ca056a6505"
REGION = "europe-west1"
AGENT_NAME = "BigQuery Invoice Agent"
MODEL_VERSION = "gemini-2.5-flash"
STAGING_BUCKET_NAME = "gs://qwiklabs-gcp-01-49ca056a6505-bucket"

project = os.environ.get("GOOGLE_CLOUD_PROJECT", PROJECT_ID)
location = os.environ.get("GOOGLE_CLOUD_LOCATION", REGION)

if not project:
    sys.exit("GOOGLE_CLOUD_PROJECT is not set. Run: gcloud config set project <PROJECT_ID>")

AGENT_PACKAGE = "bigquery_agent"
DISPLAY_NAME = os.environ.get("DISPLAY_NAME", AGENT_NAME)

# Import the root_agent object from the bigquery_agent package.
from bigquery_agent.agent import root_agent as local_agent

# Read the agent's deployment requirements from its requirements.txt.
with open(os.path.join(AGENT_PACKAGE, "requirements.txt")) as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

vertexai.init(project=project, location=location)
client = vertexai.Client(project=project, location=location)

STAGING_BUCKET = STAGING_BUCKET_NAME

config = {
    "display_name": DISPLAY_NAME,
    # Give the agent its own identity rather than a shared service account.
    "identity_type": types.IdentityType.AGENT_IDENTITY,
    "staging_bucket": STAGING_BUCKET,
    "python_version": "3.12",
    "requirements": requirements,
    "extra_packages": [f"./{AGENT_PACKAGE}"],
    "env_vars": {
        "GOOGLE_GENAI_USE_VERTEXAI": os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "TRUE"),
        "GOOGLE_CLOUD_LOCATION": location,
        "MODEL": os.environ.get("MODEL", MODEL_VERSION),
    },
}

print(f"Deploying '{AGENT_PACKAGE}' as '{DISPLAY_NAME}' to Agent Runtime with an Agent Identity...")
print("This typically takes 5-10 minutes.")

remote_agent = client.agent_engines.create(agent=local_agent, config=config)

print("\nAgent deployed successfully!")
print(f"Resource Name: {remote_agent.api_resource.name}")
print("\n--- ACTION REQUIRED ---")
print("1. In the console, open Agent Runtime (Agent Platform > Agents > Deployments)")
print("   and find this agent's Agent Identity principal.")
print("2. Grant that principal the roles it needs:")
print("   - BigQuery User (roles/bigquery.user)")
print("   - BigQuery Data Editor (roles/bigquery.dataEditor)")
print("   See README.md for the exact steps.")