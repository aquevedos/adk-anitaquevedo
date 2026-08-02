#!/usr/bin/env bash
# Copy the subset of bigquery-public-data.thelook_ecommerce we need for the demo
# into a project-local dataset. Idempotent: re-runs are no-ops on existing
# tables, but `--force` will overwrite.
#
# Why copy instead of querying the public dataset directly?
#  - Dataplex Catalog catalogs assets in YOUR project; copying lets us showcase
#    the auto-cataloging flow (Act II).
#  - The agent's dataplex_search uses `projectid:(...)` to scope BQ/Dataplex
#    searches — public datasets won't match those filters.

set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
: "${DEMO_DATASET:=retail_demo}"
: "${BQ_LOCATION:=US}"

FORCE="${1:-}"  # pass `--force` to overwrite

SRC_DATASET="bigquery-public-data:thelook_ecommerce"
DEST_DATASET="${GOOGLE_CLOUD_PROJECT}:${DEMO_DATASET}"

# Tables used in the demo. Skipping `events` (large clickstream, not needed).
TABLES=(
  orders
  order_items
  products
  users
  inventory_items
  distribution_centers
)

echo "📦 Copying tables from $SRC_DATASET to $DEST_DATASET..."

# 1. Create the dataset if missing
if ! bq --location="$BQ_LOCATION" ls --project_id="$GOOGLE_CLOUD_PROJECT" 2>/dev/null \
     | awk 'NR>2 {print $1}' | grep -qx "$DEMO_DATASET"; then
  echo "  🔧 Creating dataset $DEST_DATASET"
  bq --location="$BQ_LOCATION" mk \
    --dataset \
    --description="demo data (copy of bigquery-public-data.thelook_ecommerce)" \
    "$DEST_DATASET"
else
  echo "  ✅ Dataset $DEST_DATASET already exists"
fi

# 2. Copy each table
for table in "${TABLES[@]}"; do
  if bq show --format=none "${DEST_DATASET}.${table}" >/dev/null 2>&1 && [[ "$FORCE" != "--force" ]]; then
    echo "  ✅ ${table}: already present (use --force to overwrite)"
    continue
  fi
  echo "  📥 Copying ${table}..."
  bq cp \
    --force \
    --location="$BQ_LOCATION" \
    "${SRC_DATASET}.${table}" \
    "${DEST_DATASET}.${table}"
done

echo
echo "✅ BQ tables ready in $DEST_DATASET"
echo
echo "Next steps:"
echo "  ./setup/20-create-gcs-bucket.sh"
echo
echo "Optional: open the Knowledge Catalog UI and click 'Generate Descriptions'"
echo "on order_items / orders / products / users — this powers Act II of the demo."
