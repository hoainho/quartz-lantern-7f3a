#!/usr/bin/env bash
# Save the log of the latest Cloud Run job execution to docs/logs/ (an artefact that does not
# need a GCP login to read). Usage: PROJECT_ID=my-project deploy/gcp/logs.sh
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-us-central1}"
JOB="${JOB:-kb-sync}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

EXECUTION="$(gcloud --project "$PROJECT_ID" run jobs executions list --job "$JOB" --region "$REGION" \
  --limit 1 --format 'value(name)')"
: "${EXECUTION:?no executions found; run: gcloud run jobs execute ${JOB} --region ${REGION} --wait}"

OUT="$ROOT/docs/logs/$(date -u +%Y-%m-%dT%H%M%SZ)-${EXECUTION}.log"
mkdir -p "$ROOT/docs/logs"
gcloud --project "$PROJECT_ID" logging read \
  "resource.type=cloud_run_job AND labels.\"run.googleapis.com/execution_name\"=${EXECUTION}" \
  --order asc --format 'value(timestamp,textPayload)' --freshness 2d > "$OUT"
echo "saved $OUT ($(wc -l < "$OUT") lines)"
