# Local Google Cloud CLI Setup (Mac)

This repo uses a local gcloud config directory so commands work reliably in restricted environments.

## 1) Verify install
```bash
gcloud --version
```

## 2) Use repo-local gcloud config
Run from repo root:
```bash
cd "/Users/lappy/Desktop/Google X Columbia"
export CLOUDSDK_CONFIG="$PWD/.gcloud"
mkdir -p "$CLOUDSDK_CONFIG"
```

Add to your shell profile if you want persistence for this project.

## 3) Authenticate locally
```bash
gcloud auth login
gcloud auth application-default login
```

## 4) Set project from hackathon init output
```bash
export PROJECT_ID="gcloud-hackathon-3xfig8zhh2usd"
gcloud config set project "$PROJECT_ID"
gcloud config get-value project
```

## 5) Verify billing + services
```bash
gcloud beta billing projects describe "$PROJECT_ID" --format="value(billingEnabled,billingAccountName)"
gcloud services list --enabled | egrep "aiplatform|run|cloudbuild|firestore|storage|artifactregistry"
```

## 6) Deploy using Vertex mode (recommended)
```bash
cd infra
PROJECT_ID="$PROJECT_ID" AUTH_MODE=vertex ./deploy_cloud_run.sh
```

## 7) Health check
```bash
curl https://<warroom-backend-url>/health
```
