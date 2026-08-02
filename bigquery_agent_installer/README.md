# BigQuery Agent — basic installer

A self-contained installer for **just** the `bigquery_agent` from the GENAI155
"Build a Secure Multi-Agent Framework" lab. Use this when all you need is the
single BigQuery agent deployed to **Agent Runtime** with its own **Agent
Identity** — no `storage_agent`, no `invoice_processor`, no A2A wiring.

## What it sets up

1. Enables the required APIs (aiplatform, bigquery, logging, storage).
2. Creates the `gs://<project>-bucket` staging bucket.
3. Creates the `pool_data` BigQuery dataset and loads the `invoices` table from
   `past_invoices.csv` (15 historical invoices).
4. Installs the Python requirements and writes a `.env`.
5. Deploys the `bigquery_agent` with an Agent Identity (denied-by-default).

## Prerequisites

- `gcloud`, `bq`, and `python3` available (e.g. Cloud Shell).
- A project set: `gcloud config set project <PROJECT_ID>`.
- Permission to enable APIs and grant IAM in that project.

## Run it

```bash
cd bigquery_agent_installer
./install.sh
```

Or override the defaults:

```bash
PROJECT_ID=my-project REGION=us-central1 MODEL=gemini-2.5-flash ./install.sh
```

Deployment takes about 5–10 minutes.

## One manual step: grant the agent its roles

This is the whole point of Agent Identity — a freshly deployed agent has **no**
access to your data, so its BigQuery calls are denied until you grant it the
least-privilege roles. The identity principal only exists after deployment, so
this step is manual:

1. Open **Agent Platform > Agents > Deployments** and select the deployed
   **BigQuery Invoice Agent**.
2. Find its **Agent Identity principal** (a `principal://...system.id.goog/...`
   string tied to the reasoning engine).
3. In **IAM & Admin > IAM > Grant access**, add that principal with:
   - **BigQuery User** (`roles/bigquery.user`) — run queries and jobs.
   - **BigQuery Data Editor** (`roles/bigquery.dataEditor`) — read/insert rows.

## Verify

Open the agent's **Playground** and ask:

- `What is the schema of the invoices table?`
- `What was the total sum of the invoice totals that arrived in April 2026?`
  → should answer **$7,672.85**.
- `What is the total number of unpaid invoices we currently have?`
  → should answer **6**.

## Files

| File | Purpose |
|------|---------|
| `install.sh` | One-shot provisioning + deploy. |
| `deploy.py` | Deploys only the `bigquery_agent` to Agent Runtime. |
| `bigquery_agent/` | The agent package (copied from the full lab). |
| `past_invoices.csv` | Seed data loaded into `pool_data.invoices`. |

> This is a standalone copy of the agent code from
> `../tf/bucket_data/lab_agents/bigquery_agent/`. If you change the agent in the
> full lab, re-copy it here.
