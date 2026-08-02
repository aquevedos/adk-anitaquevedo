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

"""The bigquery_agent records and analyzes invoice data in BigQuery.

In this lab it is the agent that is exposed via A2A (Agent-to-Agent): the
invoice_processor orchestrator calls it to write the values extracted from new
invoices into the `pool_data.invoices` table, and a lab user can also chat with
it directly in the Agent Runtime Playground to analyze invoice data.

Because the agent reads AND writes BigQuery, it relies on Application Default
Credentials. When deployed to Agent Runtime with an Agent Identity, those
credentials resolve to the agent's own identity principal -- which is why
BigQuery access is denied until the principal is granted the BigQuery User and
BigQuery Data Editor roles (see Task 3).
"""

import os

from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.bigquery import BigQueryToolset, BigQueryCredentialsConfig
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode
from google.adk.models import Gemini
from google.genai import types

import google.auth
import google.cloud.logging

load_dotenv()
cloud_logging_client = google.cloud.logging.Client(project=os.getenv('GOOGLE_CLOUD_PROJECT'))
cloud_logging_client.setup_logging()

from .callback_logging import log_query_to_model, log_model_response

RETRY_OPTIONS = types.HttpRetryOptions(initial_delay=1, max_delay=3, attempts=30)

# Uses externally-managed Application Default Credentials (ADC) by default.
# This decouples authentication from the agent / tool lifecycle. When the agent
# is deployed to Agent Runtime with an Agent Identity, ADC resolves to the
# agent's identity principal.
# https://cloud.google.com/docs/authentication/provide-credentials-adc
application_default_credentials, _ = google.auth.default()
credentials_config = BigQueryCredentialsConfig(
    credentials=application_default_credentials)

# Allow write operations so the agent can INSERT new invoice rows.
tool_config = BigQueryToolConfig(write_mode=WriteMode.ALLOWED)

# Instantiate a BigQuery toolset
bigquery_toolset = BigQueryToolset(
    credentials_config=credentials_config,
    bigquery_tool_config=tool_config
)


# Agent Definition
root_agent = Agent(
    model=Gemini(model=os.getenv("MODEL"), retry_options=RETRY_OPTIONS),
    name="bigquery_agent",
    description=(
        "Records invoices into BigQuery and answers questions about invoice"
        " data and models by executing SQL queries."
    ),
    instruction=f"""
        You are an accounts-payable data agent for Cymbal Pools with access to
        several BigQuery tools. Use those tools to answer the user's questions
        and to record new invoices.

        When using the BigQuery toolset, always use the
        project {os.getenv('GOOGLE_CLOUD_PROJECT')} and the dataset named
        `pool_data`. Invoices are stored in the `invoices` table.

        The `invoices` table has the following columns:
          - invoice_date (DATE): the date on the invoice.
          - date_processed (DATE): the date the invoice was recorded.
          - invoice_id (STRING): the vendor's invoice number.
          - vendor_name (STRING): the supplier that issued the invoice.
          - invoice_total (FLOAT): the total amount due on the invoice.
          - payment_status (STRING): e.g. PAID or UNPAID.

        When you are asked to record or add a new invoice:
          - If the caller does not provide a value for `date_processed`, use
            today's date by calling the BigQuery tool to select CURRENT_DATE().
          - If `payment_status` is not provided, default it to 'UNPAID'.
          - Insert exactly one row into `pool_data.invoices` and then confirm
            what was written, including the invoice_id.

        When asked to analyze data, write efficient SQL and report the result
        clearly. If a tool call is denied because of missing permissions, tell
        the user that the agent's identity needs the BigQuery User and BigQuery
        Data Editor roles.
    """,
    before_model_callback=log_query_to_model,
    after_model_callback=log_model_response,
    tools=[bigquery_toolset],
)
