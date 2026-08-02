#!/usr/bin/env bash
# Pre-create Dataplex Catalog entries for each policy markdown file in the bucket.
#
# Why this script exists:
#   The agent's dataplex_search calls Dataplex's SearchEntries API. That only
#   returns things Dataplex has catalogued. A GCS bucket registered as a
#   Dataplex Asset (via setup/30-dataplex-discovery.sh) is itself catalogued,
#   but per-file entries are not automatically created for markdown documents
#   by the standard RAW discovery flow. Without this script, Act III's
#   "what's our outerwear return window?" question would not be able to find
#   the policy document via dataplex_search — the agent would have to enumerate
#   the bucket via MCP, which defeats the catalog-driven-routing demo story.
#
# What this script does:
#   1. Creates a custom entry type `policy-document` (if missing).
#   2. Creates an entry group `retail-policies` (if missing).
#   3. For each markdown file in sample-docs/, upserts a catalog entry whose:
#       - entry_source.resource points at the GCS URI of the file
#       - entry_source.system   = "CLOUD_STORAGE"
#       - fully_qualified_name  = "policy:retail.<filename>"
#       - display_name          = a human-readable title
#       - overview aspect       = a short summary + the gs:// URI
#
# The overview aspect's content begins with "Source: gs://..." so the agent's
# orchestration prompt — which says "for any entry whose name/description
# identifies a GCS bucket or object, use the MCP gcs_* tools" — routes these
# entries to MCP gcs_read_object for the actual document body.
#
# Idempotent: re-running deletes and recreates each entry so aspect content
# stays in sync with the markdown source.

set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
: "${DEMO_BUCKET:=retail-policies-${GOOGLE_CLOUD_PROJECT}}"
: "${ENTRY_GROUP:=retail-policies}"
: "${ENTRY_TYPE_ID:=policy-document}"
: "${LOCATION:=global}"

DOCS_DIR="$(cd "$(dirname "$0")" && pwd)/sample-docs"
ENTRY_TYPE_PATH="projects/${GOOGLE_CLOUD_PROJECT}/locations/${LOCATION}/entryTypes/${ENTRY_TYPE_ID}"

# Aspect key for the standard Dataplex overview aspect. The "655216118709"
# prefix is the project number of dataplex-types (Google-managed), so this key
# is stable across all customers.
OVERVIEW_ASPECT_KEY="655216118709.global.overview"

command -v jq >/dev/null 2>&1 || { echo "❌ 'jq' is required; install with 'brew install jq' or apt." >&2; exit 1; }

echo "🗂  Pre-creating catalog entries for policy documents..."
echo "    Project:     $GOOGLE_CLOUD_PROJECT"
echo "    Entry group: $ENTRY_GROUP"
echo "    Bucket:      gs://$DEMO_BUCKET/"
echo

# ---- 1. Entry type --------------------------------------------------------

if ! gcloud dataplex entry-types describe "$ENTRY_TYPE_ID" \
       --location="$LOCATION" --project="$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
  echo "🔧 Creating entry type: $ENTRY_TYPE_ID"
  gcloud dataplex entry-types create "$ENTRY_TYPE_ID" \
    --location="$LOCATION" \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --display-name="Policy Document" \
    --description="Retail policy or contract document stored as markdown in Cloud Storage"
else
  echo "✅ Entry type exists: $ENTRY_TYPE_ID"
fi

# ---- 2. Entry group -------------------------------------------------------

if ! gcloud dataplex entry-groups describe "$ENTRY_GROUP" \
       --location="$LOCATION" --project="$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
  echo "🔧 Creating entry group: $ENTRY_GROUP"
  gcloud dataplex entry-groups create "$ENTRY_GROUP" \
    --location="$LOCATION" \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --display-name="Retail Policies" \
    --description="Supplier contracts and customer policies (markdown in $DEMO_BUCKET)"
else
  echo "✅ Entry group exists: $ENTRY_GROUP"
fi

# ---- 3. Per-file summaries + display names --------------------------------
#
# Hardcoded so the script is fully deterministic and doesn't depend on Gemini
# availability. To regenerate summaries dynamically, replace these maps with
# a Gemini call against each file's content.

# Case-statement helpers instead of associative arrays so this works on macOS's
# default bash 3.2 (which doesn't support `declare -A`).
get_summary() {
  case "$1" in
    supplier-jackets-carhartt-contract)
      echo "Carhartt supplier agreement for Outerwear & Coats (CAR-OUTW-* SKU prefix). Defines the wholesale-to-retail markup target (1.85x-1.95x), customer return rate accountability against the 8% policy threshold, and shipping commitments. Owner: Procurement Team." ;;
    return-policy-2024)
      echo "Customer return policy. Per-category return windows (Outerwear 45 days standard, 60 days holiday extension; most others 30/45 days), reason codes, restocking fees, and operational metric thresholds including the 8% return-rate alert per category." ;;
    holiday-pricing-policy-q4)
      echo "Q4 holiday pricing and promotions policy. Discount caps per window (Black Friday 35%, Cyber Week 30%, etc.). Outerwear is excluded from Pre-Holiday Tease and capped at 25% off through Black Friday to preserve margin." ;;
    vendor-sla-template)
      echo "Default service-level template for new vendor agreements. Standard 5-business-day shipping window, 8-day peak-surge allowance, \$25 late-shipment fee. Active vendor agreements override; refer to specific contracts for vendor-specific terms." ;;
    customer-segment-policy)
      echo "Canonical customer segmentation policy. Defines the Premium, Standard, Lapsed, and Prospect tiers and the exact data signals (users.traffic_source, users.age, recent completed orders) that determine them. Includes the reference SQL filter for the Premium segment. All analytical reporting must use these definitions." ;;
    *)
      echo "Policy document." ;;
  esac
}

get_display_name() {
  case "$1" in
    supplier-jackets-carhartt-contract) echo "Carhartt Supplier Agreement (Outerwear)" ;;
    return-policy-2024)                 echo "Customer Return Policy 2024" ;;
    holiday-pricing-policy-q4)          echo "Q4 Holiday Pricing & Promotions Policy" ;;
    vendor-sla-template)                echo "Vendor SLA Template" ;;
    customer-segment-policy)            echo "Customer Segmentation Policy" ;;
    *)                                   echo "$1" ;;
  esac
}

# ---- 4. Upsert one entry per markdown file --------------------------------

if ! ls "$DOCS_DIR"/*.md >/dev/null 2>&1; then
  echo "❌ No markdown files found in $DOCS_DIR" >&2
  exit 1
fi

# gcloud's --aspects parser chokes on dotted aspect keys like
# `655216118709.global.overview` (it tries to evaluate `.global` as Python
# attribute access). Bypass it by hitting the Dataplex REST API directly with
# curl + an access token.
ACCESS_TOKEN=$(gcloud auth print-access-token)
ENTRIES_API="https://dataplex.googleapis.com/v1/projects/${GOOGLE_CLOUD_PROJECT}/locations/${LOCATION}/entryGroups/${ENTRY_GROUP}/entries"
OVERVIEW_ASPECT_TYPE="projects/dataplex-types/locations/global/aspectTypes/overview"

for file in "$DOCS_DIR"/*.md; do
  basename=$(basename "$file" .md)
  gcs_uri="gs://${DEMO_BUCKET}/${basename}.md"
  display_name=$(get_display_name "$basename")
  summary=$(get_summary "$basename")
  file_content=$(cat "$file")

  # Overview aspect content. The first line MUST be "Source: gs://..." so the
  # agent's orchestration prompt routes this entry to MCP gcs_read_object.
  overview_content="Source: ${gcs_uri}

Summary: ${summary}

--- Document Content ---
${file_content}"

  # fullyQualifiedName is optional and Dataplex only accepts prefixes from a
  # known allow-list (bigquery:, cloud-storage:, looker:, etc.). We don't need
  # it — the entry's stable handle is its resource path, and the agent finds
  # these entries via semantic search over the overview aspect content.
  entry_body=$(jq -n \
    --arg entry_type "$ENTRY_TYPE_PATH" \
    --arg resource "$gcs_uri" \
    --arg display "$display_name" \
    --arg aspect_key "$OVERVIEW_ASPECT_KEY" \
    --arg aspect_type "$OVERVIEW_ASPECT_TYPE" \
    --arg content "$overview_content" \
    '{
       entryType: $entry_type,
       entrySource: {
         resource: $resource,
         system: "CLOUD_STORAGE",
         displayName: $display
       },
       aspects: {
         ($aspect_key): {
           aspectType: $aspect_type,
           data: { content: $content }
         }
       }
     }')

  # Idempotent: explicit delete first (404 if absent → ignored), then create.
  echo "  🗑️ Deleting existing entry (if present): $basename"
  curl -sS -X DELETE \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    "${ENTRIES_API}/${basename}" >/dev/null 2>&1 || true

  echo "  📝 Creating entry:   $basename"
  http_status=$(curl -sS -o /tmp/dataplex_create.json -w "%{http_code}" \
    -X POST \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$entry_body" \
    "${ENTRIES_API}?entryId=${basename}")
  if [[ "$http_status" != "200" && "$http_status" != "201" ]]; then
    echo "❌ Entry create for '$basename' returned HTTP $http_status:" >&2
    cat /tmp/dataplex_create.json >&2
    echo >&2
    rm -f /tmp/dataplex_create.json
    exit 1
  fi
  rm -f /tmp/dataplex_create.json
done

echo
echo "✅ Catalog entries ready in entry group $ENTRY_GROUP"
echo
echo "Verify with:"
echo "  gcloud dataplex entries list --entry-group=$ENTRY_GROUP --location=$LOCATION --project=$GOOGLE_CLOUD_PROJECT"
echo
echo "Or test the agent's search by asking the enriched deployment a question that"
echo "should hit a policy doc (e.g. 'what is our return window for outerwear?')."
