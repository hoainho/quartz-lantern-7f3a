#!/usr/bin/env bash
# Deploy the sync job to Cloud Run Jobs and schedule it daily with Cloud Scheduler.
# Idempotent: safe to re-run to ship a new image or rotate the API key.
#
#   PROJECT_ID=my-project deploy/gcp/deploy.sh            # reads GEMINI_API_KEY from .env
#   PROJECT_ID=my-project GEMINI_API_KEY=... deploy/gcp/deploy.sh
#
# Prerequisites: `gcloud auth login`, a project with an active billing account
# (free-tier usage still requires one).
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-us-central1}"      # Tier 1 region: gets the most free-tier coverage
JOB="${JOB:-kb-sync}"
REPO="${REPO:-kb-sync}"
IMAGE="${IMAGE:-sync-job}"
SECRET="${SECRET:-gemini-api-key}"
SCHEDULE="${SCHEDULE:-23 2 * * *}"   # daily, 02:23 UTC
TIMEZONE="${TIMEZONE:-Etc/UTC}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNNER_SA="kb-sync-runner"
SCHED_SA="kb-sync-scheduler"
RUNNER_EMAIL="${RUNNER_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
SCHED_EMAIL="${SCHED_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}:$(git -C "$ROOT" rev-parse --short HEAD)"

gc() { gcloud --project "$PROJECT_ID" "$@"; }

if [[ -z "${GEMINI_API_KEY:-}" && -f "$ROOT/.env" ]]; then
  GEMINI_API_KEY="$(grep -E '^(GEMINI_API_KEY|API_KEY)=' "$ROOT/.env" | head -1 | cut -d= -f2-)"
fi
: "${GEMINI_API_KEY:?set GEMINI_API_KEY or put it in .env}"

echo "==> enable APIs"
gc services enable run.googleapis.com cloudscheduler.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com

echo "==> service accounts"
for sa in "$RUNNER_SA" "$SCHED_SA"; do
  gc iam service-accounts describe "${sa}@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1 \
    || gc iam service-accounts create "$sa" --display-name "$sa"
done

echo "==> secret (value is never printed)"
if gc secrets describe "$SECRET" >/dev/null 2>&1; then
  printf '%s' "$GEMINI_API_KEY" | gc secrets versions add "$SECRET" --data-file=-
else
  printf '%s' "$GEMINI_API_KEY" | gc secrets create "$SECRET" --replication-policy=automatic --data-file=-
fi
gc secrets add-iam-policy-binding "$SECRET" \
  --member "serviceAccount:${RUNNER_EMAIL}" --role roles/secretmanager.secretAccessor >/dev/null

echo "==> image build (Cloud Build, linux/amd64)"
gc artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1 \
  || gc artifacts repositories create "$REPO" --repository-format docker --location "$REGION"
PROJECT_NUMBER="$(gc projects describe "$PROJECT_ID" --format 'value(projectNumber)')"
# Cloud Build runs as the default compute service account in new projects.
gc projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role roles/cloudbuild.builds.builder --condition None >/dev/null
gc builds submit "$ROOT" --tag "$IMAGE_URI"

echo "==> Cloud Run job"
gc run jobs deploy "$JOB" \
  --image "$IMAGE_URI" --region "$REGION" \
  --service-account "$RUNNER_EMAIL" \
  --set-secrets "API_KEY=${SECRET}:latest" \
  --set-env-vars "LOG_LEVEL=INFO" \
  --cpu 1 --memory 512Mi --max-retries 1 --task-timeout 3600s

echo "==> scheduler"
gc run jobs add-iam-policy-binding "$JOB" --region "$REGION" \
  --member "serviceAccount:${SCHED_EMAIL}" --role roles/run.invoker >/dev/null
URI="https://run.googleapis.com/v2/projects/${PROJECT_ID}/locations/${REGION}/jobs/${JOB}:run"
if gc scheduler jobs describe "${JOB}-daily" --location "$REGION" >/dev/null 2>&1; then
  verb=update
else
  verb=create
fi
gc scheduler jobs "$verb" http "${JOB}-daily" --location "$REGION" \
  --schedule "$SCHEDULE" --time-zone "$TIMEZONE" \
  --uri "$URI" --http-method POST \
  --oauth-service-account-email "$SCHED_EMAIL"

cat <<EOF

Done. Run it now:     gcloud run jobs execute ${JOB} --region ${REGION} --project ${PROJECT_ID} --wait
Read the last logs:   deploy/gcp/logs.sh   (PROJECT_ID=${PROJECT_ID})
EOF
