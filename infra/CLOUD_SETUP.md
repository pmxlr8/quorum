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
- `GOOGLE_API_KEY` (Gemini API key)
- `gcloud auth login` and `gcloud auth application-default login`

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
PROJECT_ID=<your-project-id> GOOGLE_API_KEY=<your-key> ./deploy_cloud_run.sh
```

## 5) Verify
```bash
curl https://<warroom-backend-url>/health
```
Expected keys: `status`, `version`, `live_model_id`.

## 6) Notes
- Current backend live bridge is scaffolded for wiring. Replace with full ADK runner in BACK-003 completion pass.
- Session affinity is enabled for demo stability.
