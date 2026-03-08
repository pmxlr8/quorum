#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export CLOUDSDK_CONFIG="${CLOUDSDK_CONFIG:-$ROOT_DIR/.gcloud}"
mkdir -p "$CLOUDSDK_CONFIG"

printf "[check] gcloud installed... "
command -v gcloud >/dev/null && echo "ok" || { echo "missing"; exit 1; }

printf "[check] project configured... "
PROJECT="$(gcloud config get-value core/project 2>/dev/null || true)"
if [[ -z "$PROJECT" || "$PROJECT" == "(unset)" ]]; then
  echo "missing"
  exit 1
fi
echo "$PROJECT"

printf "[check] auth account... "
ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null || true)"
if [[ -z "$ACCOUNT" ]]; then
  echo "missing"
  exit 1
fi
echo "$ACCOUNT"

printf "[check] ADC token... "
gcloud auth application-default print-access-token >/dev/null 2>&1 && echo "ok" || { echo "missing"; exit 1; }

printf "[check] required services...\n"
for svc in aiplatform.googleapis.com run.googleapis.com cloudbuild.googleapis.com firestore.googleapis.com storage.googleapis.com artifactregistry.googleapis.com; do
  if gcloud services list --enabled --format='value(config.name)' | grep -qx "$svc"; then
    echo "  - $svc: enabled"
  else
    echo "  - $svc: missing"
    exit 1
  fi
done

echo "All local cloud checks passed."
