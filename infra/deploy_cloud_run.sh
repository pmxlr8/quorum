#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# Deploy Quorum (Virtual War Room) to Google Cloud Run
# Usage: PROJECT_ID=gcloud-hackathon-3xfig8zhh2usd ./infra/deploy_cloud_run.sh
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-gcloud-hackathon-3xfig8zhh2usd}"
REGION="${REGION:-us-central1}"
LIVE_MODEL_ID="${LIVE_MODEL_ID:-gemini-live-2.5-flash-native-audio}"
REPO_NAME="quorum"
AR_PREFIX="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "═══════════════════════════════════════════════════════════"
echo "  Deploying Quorum to Google Cloud Run"
echo "  Project: ${PROJECT_ID}  Region: ${REGION}"
echo "═══════════════════════════════════════════════════════════"

# ── 0. Ensure Artifact Registry repo exists ─────────────────────────
echo "→ Ensuring Artifact Registry repo '${REPO_NAME}' exists..."
gcloud artifacts repositories describe "$REPO_NAME" \
  --project "$PROJECT_ID" --location "$REGION" 2>/dev/null || \
gcloud artifacts repositories create "$REPO_NAME" \
  --project "$PROJECT_ID" --location "$REGION" \
  --repository-format docker \
  --description "Quorum container images"
echo "✓ Artifact Registry ready"

# ── 1. Build & push backend image ───────────────────────────────────
echo ""
echo "→ Building backend image..."
gcloud builds submit "${ROOT_DIR}/backend" \
  --project "$PROJECT_ID" \
  --config "${ROOT_DIR}/infra/cloudbuild.backend.yaml"
echo "✓ Backend image built"

# ── 2. Deploy backend to Cloud Run ──────────────────────────────────
echo ""
echo "→ Deploying backend to Cloud Run..."
gcloud run deploy quorum-backend \
  --image "${AR_PREFIX}/backend:latest" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --session-affinity \
  --memory 1Gi \
  --cpu 2 \
  --timeout 3600 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "\
LIVE_MODEL_ID=${LIVE_MODEL_ID},\
GOOGLE_CLOUD_PROJECT=${PROJECT_ID},\
GOOGLE_CLOUD_LOCATION=${REGION},\
GOOGLE_GENAI_USE_VERTEXAI=true,\
ALLOWED_ORIGINS=*"

BACKEND_URL="$(gcloud run services describe quorum-backend \
  --project "$PROJECT_ID" --region "$REGION" \
  --format='value(status.url)')"
BACKEND_WS_URL="${BACKEND_URL/https:/wss:}"
echo "✓ Backend deployed: ${BACKEND_URL}"

# ── 3. Build & push frontend image (bake in backend URLs) ───────────
echo ""
echo "→ Building frontend image (WS → ${BACKEND_WS_URL}/ws)..."
gcloud builds submit "${ROOT_DIR}/frontend-new" \
  --project "$PROJECT_ID" \
  --config "${ROOT_DIR}/infra/cloudbuild.frontend.yaml" \
  --substitutions "_VITE_WS_URL=${BACKEND_WS_URL}/ws,_VITE_API_URL=${BACKEND_URL}"
echo "✓ Frontend image built"

# ── 4. Deploy frontend to Cloud Run ─────────────────────────────────
echo ""
echo "→ Deploying frontend to Cloud Run..."
gcloud run deploy quorum-frontend \
  --image "${AR_PREFIX}/frontend:latest" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 256Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5

FRONTEND_URL="$(gcloud run services describe quorum-frontend \
  --project "$PROJECT_ID" --region "$REGION" \
  --format='value(status.url)')"
echo "✓ Frontend deployed: ${FRONTEND_URL}"

# ── 5. Update backend CORS to allow frontend URL ────────────────────
echo ""
echo "→ Updating backend CORS with frontend URL..."
gcloud run services update quorum-backend \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --update-env-vars "ALLOWED_ORIGINS=${FRONTEND_URL},http://localhost:5173,http://localhost:8080"
echo "✓ CORS updated"

# ── Done ─────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✓ DEPLOYMENT COMPLETE"
echo ""
echo "  Frontend: ${FRONTEND_URL}"
echo "  Backend:  ${BACKEND_URL}"
echo "  Health:   curl ${BACKEND_URL}/health"
echo "  WebSocket: ${BACKEND_WS_URL}/ws"
echo "═══════════════════════════════════════════════════════════"
