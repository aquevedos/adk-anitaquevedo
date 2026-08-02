#!/usr/bin/env bash
#
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License").
#
# Basic installer for ONLY the bigquery_agent from the GENAI155 lab.
#
# It provisions the minimum a single BigQuery agent needs and deploys it to
# Agent Runtime with its own Agent Identity:
#   1. Enables the required APIs.
#   2. Creates the gs://<project>-bucket staging bucket.
#   3. Creates the pool_data BigQuery dataset and loads the invoices table
#      from past_invoices.csv.
#   4. Installs the Python requirements and writes a .env.
#   5. Deploys the bigquery_agent (Agent Identity, denied-by-default).
#
# After it finishes you still grant the agent's identity its BigQuery roles
# once (see README.md / the script's closing output) -- that is the security
# lesson and the principal is only known after deployment.
#
# Usage:
#   ./install.sh                  # uses the active gcloud project + us-central1
#   PROJECT_ID=my-proj REGION=us-central1 ./install.sh

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
MODEL="${MODEL:-gemini-2.5-flash}"
BUCKET="gs://${PROJECT_ID}-bucket"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: No project set. Run 'gcloud config set project <PROJECT_ID>' or pass PROJECT_ID=..." >&2
  exit 1
fi

cd "$(dirname "$0")"

echo "=== bigquery_agent installer ==="
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Model:    ${MODEL}"
echo "Bucket:   ${BUCKET}"
echo

echo "[1/5] Enabling required APIs..."
gcloud services enable \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  logging.googleapis.com \
  storage.googleapis.com \
  storage-component.googleapis.com \
  --project "${PROJECT_ID}"

echo "[2/5] Creating staging bucket ${BUCKET} (ok if it already exists)..."
gcloud storage buckets create "${BUCKET}" \
  --project "${PROJECT_ID}" --location US 2>/dev/null \
  || echo "  bucket already exists, continuing."

echo "[3/5] Creating pool_data dataset and loading the invoices table..."
bq --project_id="${PROJECT_ID}" --location=US mk --force --dataset \
  --description "Cymbal Pools vendor invoices." "${PROJECT_ID}:pool_data"
bq --project_id="${PROJECT_ID}" --location=US load \
  --source_format=CSV --autodetect --skip_leading_rows=1 \
  --replace \
  "${PROJECT_ID}:pool_data.invoices" ./past_invoices.csv

echo "[4/5] Installing Python requirements and writing .env..."
export PATH="${PATH}:/home/${USER}/.local/bin"
python3 -m pip install -q -r bigquery_agent/requirements.txt
cat > .env <<EOF
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
GOOGLE_CLOUD_LOCATION=${REGION}
MODEL=${MODEL}
EOF

echo "[5/5] Deploying the bigquery_agent (5-10 minutes)..."
python3 deploy.py

echo
echo "=== Done. One manual step remains (the security lesson): ==="
echo "Grant the agent's Agent Identity principal these two roles in IAM:"
echo "  - roles/bigquery.user"
echo "  - roles/bigquery.dataEditor"
echo "Find the principal in Agent Platform > Agents > Deployments > (this agent)."
echo "See README.md for details."
