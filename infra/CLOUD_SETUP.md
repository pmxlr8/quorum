# Cloud Setup (Hackathon)

## 1) Required APIs
Enable in your GCP project:
- `aiplatform.googleapis.com`
- `run.googleapis.com`
- `cloudbuild.googleapis.com`
- `firestore.googleapis.com`
- `storage.googleapis.com`
- `artifactregistry.googleapis.com`

## 2) Required Auth/Secrets
You need:
- `PROJECT_ID`
- `gcloud auth login` and `gcloud auth application-default login`
- Auth mode:
  - Recommended: `AUTH_MODE=vertex` (uses GCP project billing credits, no API key required)
  - Optional: `AUTH_MODE=devapi` + `GOOGLE_API_KEY`

## 3) One-time setup commands
```bash
gcloud config set project "$PROJECT_ID"
gcloud services enable \
  aiplatform.googleapis.com run.googleapis.com cloudbuild.googleapis.com \
  firestore.googleapis.com storage.googleapis.com artifactregistry.googleapis.com
```

## 4) Deploy
```bash
cd infra
PROJECT_ID=<your-project-id> AUTH_MODE=vertex ./deploy_cloud_run.sh
# or, if using Gemini Developer API key mode:
# PROJECT_ID=<your-project-id> AUTH_MODE=devapi GOOGLE_API_KEY=<your-key> ./deploy_cloud_run.sh
```

## 5) Verify
```bash
curl https://<warroom-backend-url>/health
```
Expected keys: `status`, `version`, `live_model_id`.

## 6) Notes
- Current backend live bridge is scaffolded for wiring. Replace with full ADK runner in BACK-003 completion pass.
- Session affinity is enabled for demo stability.
- Vertex mode env vars set on backend service:
  - `GOOGLE_GENAI_USE_VERTEXAI=true`
  - `GOOGLE_CLOUD_PROJECT=<PROJECT_ID>`
  - `GOOGLE_CLOUD_LOCATION=<REGION>`
