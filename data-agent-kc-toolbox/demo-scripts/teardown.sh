#!/usr/bin/env bash
# Tear down everything the demo setup scripts created.
# Safe to re-run; missing resources are skipped.
# Prompts for confirmation before destroying each class of resource.

set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
: "${DEMO_DATASET:=retail_demo}"
: "${DEMO_BUCKET:=retail-policies-${GOOGLE_CLOUD_PROJECT}}"
: "${DATAPLEX_LOCATION:=us-central1}"
: "${DATAPLEX_LAKE:=retail-lake}"
: "${DATAPLEX_ZONE:=policies-zone}"
: "${DATAPLEX_ASSET:=policies-bucket}"
: "${CATALOG_LOCATION:=global}"
: "${ENTRY_GROUP:=retail-policies}"
: "${ENTRY_TYPE_ID:=policy-document}"
: "${TOOLBOX_REGION:=us-central1}"

confirm() {
  local prompt="$1"
  read -r -p "$prompt [y/N] " ans
  [[ "$ans" =~ ^[yY]([eE][sS])?$ ]]
}

echo "🧹 demo teardown for project: $GOOGLE_CLOUD_PROJECT"
echo

# 1. BigQuery dataset
if bq --project_id="$GOOGLE_CLOUD_PROJECT" show "$DEMO_DATASET" >/dev/null 2>&1; then
  if confirm "  Delete BQ dataset ${GOOGLE_CLOUD_PROJECT}:${DEMO_DATASET} (and all tables)?"; then
    bq rm -r -f --dataset "${GOOGLE_CLOUD_PROJECT}:${DEMO_DATASET}"
    echo "  ✅ Dataset removed"
  else
    echo "  ⏭  Skipped dataset"
  fi
fi

# 2. GCS bucket
if gsutil ls -b "gs://${DEMO_BUCKET}" >/dev/null 2>&1; then
  if confirm "  Delete GCS bucket gs://${DEMO_BUCKET}/ (and all contents)?"; then
    gsutil -m rm -r "gs://${DEMO_BUCKET}"
    echo "  ✅ Bucket removed"
  else
    echo "  ⏭  Skipped bucket"
  fi
fi

# 3. Dataplex Lake/Zone/Asset
if gcloud dataplex lakes describe "$DATAPLEX_LAKE" \
     --location="$DATAPLEX_LOCATION" \
     --project="$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
  if confirm "  Delete Dataplex Lake/Zone/Asset (${DATAPLEX_LAKE})?"; then
    gcloud dataplex assets delete "$DATAPLEX_ASSET" \
      --zone="$DATAPLEX_ZONE" --lake="$DATAPLEX_LAKE" \
      --location="$DATAPLEX_LOCATION" --project="$GOOGLE_CLOUD_PROJECT" \
      --quiet 2>/dev/null || true
    gcloud dataplex zones delete "$DATAPLEX_ZONE" \
      --lake="$DATAPLEX_LAKE" \
      --location="$DATAPLEX_LOCATION" --project="$GOOGLE_CLOUD_PROJECT" \
      --quiet 2>/dev/null || true
    gcloud dataplex lakes delete "$DATAPLEX_LAKE" \
      --location="$DATAPLEX_LOCATION" --project="$GOOGLE_CLOUD_PROJECT" \
      --quiet 2>/dev/null || true
    echo "  ✅ Dataplex hierarchy removed"
  else
    echo "  ⏭  Skipped Dataplex"
  fi
fi

# 4. Dataplex Catalog entries (policy documents) + entry group + entry type
if gcloud dataplex entry-groups describe "$ENTRY_GROUP" \
     --location="$CATALOG_LOCATION" --project="$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
  if confirm "  Delete catalog entry group '$ENTRY_GROUP' (and all policy-document entries inside)?"; then
    # Delete each entry first (entry-groups can't be deleted if non-empty)
    for entry_id in $(gcloud dataplex entries list \
                        --entry-group="$ENTRY_GROUP" \
                        --location="$CATALOG_LOCATION" \
                        --project="$GOOGLE_CLOUD_PROJECT" \
                        --format="value(name.basename())" 2>/dev/null); do
      gcloud dataplex entries delete "$entry_id" \
        --entry-group="$ENTRY_GROUP" \
        --location="$CATALOG_LOCATION" \
        --project="$GOOGLE_CLOUD_PROJECT" \
        --quiet 2>/dev/null || true
    done
    gcloud dataplex entry-groups delete "$ENTRY_GROUP" \
      --location="$CATALOG_LOCATION" \
      --project="$GOOGLE_CLOUD_PROJECT" \
      --quiet
    echo "  ✅ Entry group removed"
  else
    echo "  ⏭  Skipped entry group"
  fi
fi
if gcloud dataplex entry-types describe "$ENTRY_TYPE_ID" \
     --location="$CATALOG_LOCATION" --project="$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
  if confirm "  Delete catalog entry type '$ENTRY_TYPE_ID'?"; then
    gcloud dataplex entry-types delete "$ENTRY_TYPE_ID" \
      --location="$CATALOG_LOCATION" \
      --project="$GOOGLE_CLOUD_PROJECT" \
      --quiet
    echo "  ✅ Entry type removed"
  else
    echo "  ⏭  Skipped entry type"
  fi
fi

# 5. Agent Engine deployments (baseline + enriched)
for variant in baseline enriched; do
  display_name="data-agent-kc-${variant}"
  if gcloud beta ai agent-engines list \
       --project="$GOOGLE_CLOUD_PROJECT" \
       --format="value(displayName)" 2>/dev/null | grep -qx "$display_name"; then
    if confirm "  Delete Agent Engine '$display_name'?"; then
      agent_id=$(gcloud beta ai agent-engines list \
                   --project="$GOOGLE_CLOUD_PROJECT" \
                   --format="value(name)" \
                   --filter="displayName=$display_name" | head -1)
      if [[ -n "$agent_id" ]]; then
        gcloud beta ai agent-engines delete "$agent_id" \
          --project="$GOOGLE_CLOUD_PROJECT" --quiet || true
        echo "  ✅ Removed $display_name"
      fi
    else
      echo "  ⏭  Skipped $display_name"
    fi
  fi
done

# 6. MCP toolbox Cloud Run services (baseline + enriched)
for variant in baseline enriched; do
  service_name="data-agent-mcp-toolbox-${variant}"
  if gcloud run services describe "$service_name" \
       --region="$TOOLBOX_REGION" \
       --project="$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
    if confirm "  Delete MCP Toolbox Cloud Run service '$service_name'?"; then
      gcloud run services delete "$service_name" \
        --region="$TOOLBOX_REGION" \
        --project="$GOOGLE_CLOUD_PROJECT" --quiet
      echo "  ✅ Toolbox service removed"
    else
      echo "  ⏭  Skipped toolbox service"
    fi
  fi
done

# 7. Secret Manager + IAM (lightweight cleanup; keep the toolbox SA since it
# might be shared with other variants in the future)
for variant in baseline enriched; do
  secret_name="toolbox-tools-config-${variant}"
  if gcloud secrets describe "$secret_name" \
       --project="$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
    if confirm "  Delete Secret '$secret_name'?"; then
      gcloud secrets delete "$secret_name" \
        --project="$GOOGLE_CLOUD_PROJECT" --quiet
      echo "  ✅ Secret removed"
    else
      echo "  ⏭  Skipped secret"
    fi
  fi
done

# 8. Deployment metadata files
echo
if confirm "  Delete deployment_metadata.{baseline,enriched}.json from the project root?"; then
  rm -f ../deployment_metadata.baseline.json ../deployment_metadata.enriched.json
  echo "  ✅ Metadata files removed"
else
  echo "  ⏭  Skipped metadata"
fi

echo
echo "🧹 Teardown complete."
