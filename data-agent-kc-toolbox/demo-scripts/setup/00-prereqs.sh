#!/usr/bin/env bash
# Verify prerequisites for the demo setup.
# Run before any of the other setup scripts.

set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT to your demo project ID}"
: "${DEMO_DATASET:=retail_demo}"
: "${DEMO_BUCKET:=retail-policies-${GOOGLE_CLOUD_PROJECT}}"
: "${BQ_LOCATION:=US}"
# GCS bucket must be in a single region that matches the Dataplex zone region
# in setup/30-dataplex-discovery.sh. Dataplex SINGLE_REGION zones reject
# multi-region GCS buckets. us-central1 is also where the MCP toolbox runs.
: "${GCS_LOCATION:=us-central1}"

echo "🔍 Checking prerequisites..."
echo "  Project:        $GOOGLE_CLOUD_PROJECT"
echo "  BQ dataset:     $DEMO_DATASET"
echo "  GCS bucket:     $DEMO_BUCKET"
echo "  BQ location:    $BQ_LOCATION"
echo "  GCS location:   $GCS_LOCATION"
echo

# Tools
for tool in gcloud bq gsutil; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "❌ $tool not found in PATH. Install the Google Cloud SDK." >&2
    exit 1
  fi
done
echo "✅ gcloud, bq, gsutil present"

# jq is used by 35-create-catalog-entries.sh to build aspect JSON.
if ! command -v jq >/dev/null 2>&1; then
  echo "❌ 'jq' not found. See setup/install-jq.md for installation instructions." >&2
  exit 1
fi
echo "✅ jq present"

# Auth
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
  echo "❌ No active gcloud account. Run: gcloud auth login && gcloud auth application-default login" >&2
  exit 1
fi
ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
echo "✅ Active gcloud account: $ACCOUNT"

# Project
if ! gcloud projects describe "$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
  echo "❌ Project $GOOGLE_CLOUD_PROJECT not found or no access." >&2
  exit 1
fi
echo "✅ Project $GOOGLE_CLOUD_PROJECT accessible"

# APIs we need enabled
echo
echo "🔌 Ensuring required APIs are enabled..."
gcloud services enable \
  bigquery.googleapis.com \
  storage.googleapis.com \
  dataplex.googleapis.com \
  aiplatform.googleapis.com \
  geminidataanalytics.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  --project="$GOOGLE_CLOUD_PROJECT"

echo
echo "✅ Prereqs OK. Next: ./setup/10-copy-bq-tables.sh"
