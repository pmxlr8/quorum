#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
LIVE_MODEL_ID="${LIVE_MODEL_ID:-gemini-2.5-flash-native-audio-preview-12-2025}"
GOOGLE_API_KEY="${GOOGLE_API_KEY:-}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "PROJECT_ID is required"
  exit 1
fi
if [[ -z "$GOOGLE_API_KEY" ]]; then
  echo "GOOGLE_API_KEY is required"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Backend build + deploy
gcloud builds submit "${ROOT_DIR}/backend" \
  --project "$PROJECT_ID" \
  --config "${ROOT_DIR}/infra/cloudbuild.backend.yaml"

gcloud run deploy warroom-backend \
  --image "gcr.io/${PROJECT_ID}/warroom-backend:latest" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --session-affinity \
  --set-env-vars "LIVE_MODEL_ID=${LIVE_MODEL_ID},GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},GOOGLE_API_KEY=${GOOGLE_API_KEY}"

BACKEND_URL="$(gcloud run services describe warroom-backend --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')"
BACKEND_WS_URL="${BACKEND_URL/https:/wss:}"

# Frontend build + deploy with ws URL baked at build-time
gcloud builds submit "${ROOT_DIR}/frontend" \
  --project "$PROJECT_ID" \
  --config "${ROOT_DIR}/infra/cloudbuild.frontend.yaml" \
  --substitutions "_VITE_WS_BASE_URL=${BACKEND_WS_URL}"

gcloud run deploy warroom-frontend \
  --image "gcr.io/${PROJECT_ID}/warroom-frontend:latest" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated

FRONTEND_URL="$(gcloud run services describe warroom-frontend --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')"

echo "Backend URL: ${BACKEND_URL}"
echo "Frontend URL: ${FRONTEND_URL}"
echo "Health check: curl ${BACKEND_URL}/health"
