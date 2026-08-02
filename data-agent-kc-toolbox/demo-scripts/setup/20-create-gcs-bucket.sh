#!/usr/bin/env bash
# Create the retail policies bucket and upload the sample markdown
# documents that drive Act III and Act IV.
#
# We use markdown (not PDF) because:
#   - MCP gcs_read_object reads UTF-8 text up to 8 MiB
#   - The agent needs to actually consume the content during the demo, not
#     just show it in the catalog UI

set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
: "${DEMO_BUCKET:=retail-policies-${GOOGLE_CLOUD_PROJECT}}"
# Must be a single region matching the Dataplex zone in 30-dataplex-discovery.sh.
# Dataplex SINGLE_REGION zones reject multi-region GCS buckets.
: "${GCS_LOCATION:=us-central1}"

DOCS_DIR="$(cd "$(dirname "$0")" && pwd)/sample-docs"

echo "🪣 Setting up bucket gs://${DEMO_BUCKET}/"

# Use `gcloud storage` if available — Google's modern replacement for gsutil
# that handles new-bucket consistency better. Fall back to gsutil otherwise.
if command -v gcloud >/dev/null 2>&1 && gcloud storage --help >/dev/null 2>&1; then
  STORAGE_CMD="gcloud storage"
  EXISTS_CHECK="gcloud storage buckets describe"
  CREATE_CMD="gcloud storage buckets create"
  CP_CMD="gcloud storage cp"
  LS_CMD="gcloud storage ls --long --readable-sizes"
else
  STORAGE_CMD="gsutil"
  EXISTS_CHECK="gsutil ls -b"
  CREATE_CMD="gsutil mb"
  CP_CMD="gsutil -m cp"
  LS_CMD="gsutil ls -lh"
fi

BUCKET_CREATED_NOW=false

# Soft-deleted bucket detection — if a bucket name was deleted recently it
# can sit in a soft-delete state where it can't be recreated *or* written to.
# Try to restore if the gcloud version supports it; otherwise punt and let the
# caller pick a different bucket name.
restore_if_soft_deleted() {
  local bucket="$1"
  # `--soft-deleted` flag may not exist in older gcloud — silently treat as
  # "not soft-deleted".
  local hit
  hit=$(gcloud storage buckets list --soft-deleted \
          --project="$GOOGLE_CLOUD_PROJECT" \
          --filter="name:$bucket" \
          --format="value(name)" 2>/dev/null | head -1 || true)
  if [[ -z "$hit" ]]; then
    return 1
  fi
  # `buckets restore` was added in a more recent gcloud release. Probe.
  if ! gcloud storage buckets restore --help >/dev/null 2>&1; then
    echo "  ⚠️  Bucket is soft-deleted but this gcloud doesn't have 'storage buckets restore'."
    echo "     Run 'gcloud components update' to upgrade, or pick a different bucket name."
    return 1
  fi
  echo "  ♻️  Found soft-deleted bucket; restoring instead of recreating"
  gcloud storage buckets restore "gs://$bucket" \
    --project="$GOOGLE_CLOUD_PROJECT" --quiet
  return 0
}

# Create the bucket if missing
if ! $EXISTS_CHECK "gs://${DEMO_BUCKET}" >/dev/null 2>&1; then
  echo "  🔧 Creating bucket"
  if [[ "$STORAGE_CMD" == "gcloud storage" ]]; then
    create_err=$($CREATE_CMD "gs://${DEMO_BUCKET}" --location="$GCS_LOCATION" --project="$GOOGLE_CLOUD_PROJECT" 2>&1) \
      || create_failed=1
  else
    create_err=$($CREATE_CMD -l "$GCS_LOCATION" -p "$GOOGLE_CLOUD_PROJECT" "gs://${DEMO_BUCKET}" 2>&1) \
      || create_failed=1
  fi
  if [[ "${create_failed:-0}" == "1" ]]; then
    echo "$create_err"
    if echo "$create_err" | grep -q "409\|already exists"; then
      if ! restore_if_soft_deleted "$DEMO_BUCKET"; then
        cat >&2 <<EOF

❌ Bucket name 'gs://${DEMO_BUCKET}' is globally taken (409). Either a prior
   delete reserved the name in soft-delete (and either the soft-delete window
   hasn't visibly surfaced for this gcloud version, or you don't have access
   to restore it), or another project genuinely owns the name globally.

   Easiest fix: pick a different bucket name and re-run all setup scripts:

     export DEMO_BUCKET="retail-policies-${GOOGLE_CLOUD_PROJECT}-v2"
     ./setup/20-create-gcs-bucket.sh
     ./setup/30-dataplex-discovery.sh
     ./setup/35-create-catalog-entries.sh
EOF
        exit 1
      fi
    else
      exit 1
    fi
  fi
  BUCKET_CREATED_NOW=true
else
  echo "  ✅ Bucket already exists"
fi

# Upload all sample docs
if [[ ! -d "$DOCS_DIR" ]]; then
  echo "❌ Sample docs directory not found: $DOCS_DIR" >&2
  exit 1
fi

# Brief wait after fresh-create to let global consistency catch up before
# uploading — otherwise gsutil/gcloud sometimes returns 404 on the bucket it
# just made.
if [[ "$BUCKET_CREATED_NOW" == "true" ]]; then
  echo "  ⏳ Waiting briefly for bucket to be globally consistent..."
  sleep 8
fi

echo "  📤 Uploading sample docs from $DOCS_DIR"
# Retry the upload up to 3 times on transient errors (the new-bucket race
# usually clears within seconds; gcloud storage handles this internally but
# gsutil sometimes doesn't).
attempt=1
max_attempts=3
until $CP_CMD "$DOCS_DIR"/*.md "gs://${DEMO_BUCKET}/" 2>&1; do
  if [[ $attempt -ge $max_attempts ]]; then
    echo "❌ Upload failed after $max_attempts attempts." >&2
    exit 1
  fi
  attempt=$((attempt + 1))
  echo "  🔁 Upload attempt $attempt/$max_attempts (waiting 5s)..."
  sleep 5
done

echo
echo "✅ Bucket ready. Contents:"
$LS_CMD "gs://${DEMO_BUCKET}/"

echo
echo "Next steps:"
echo "  ./setup/30-dataplex-discovery.sh   # optional, registers bucket as Dataplex asset"
echo "  cd .. && make deploy-all VARIANT=enriched DATAPLEX_ENABLED=true"
echo "  cd .. && make deploy     VARIANT=baseline DATAPLEX_ENABLED=false"
