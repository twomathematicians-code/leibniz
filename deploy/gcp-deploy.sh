#!/usr/bin/env bash
# =============================================================================
# Google Cloud Run deployment for SCITAMEHTAM Leibniz
# Cloud Run builds the container from source (no local Docker), serves it
# serverless with a real HTTPS URL. Free tier is generous.
#
# Prereqs: gcloud CLI installed and authenticated (gcloud auth login).
# Usage:   PROJECT_ID=my-project bash deploy/gcp-deploy.sh
#   (or export PROJECT_ID first; creates the project if it doesn't exist)
# =============================================================================
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-europe-west1}"       # closest to Ghent
SERVICE="${SERVICE:-leibniz}"

[ -z "$PROJECT_ID" ] && { echo "Set PROJECT_ID first, e.g.: PROJECT_ID=scitamehtam-<something> bash deploy/gcp-deploy.sh"; exit 1; }

echo "== SCITAMEHTAM Leibniz -> Google Cloud Run =="
gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q . || { echo "Run 'gcloud auth login' first."; exit 1; }

# 1. project (create if missing)
if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
  echo "creating project $PROJECT_ID ..."
  gcloud projects create "$PROJECT_ID" --name="SCITAMEHTAM Leibniz"
fi
gcloud config set project "$PROJECT_ID"

# 2. billing check — Cloud Run needs a billing account (free trial credits count)
BILLING=$(gcloud billing projects describe "$PROJECT_ID" --format="value(billingAccountName)" 2>/dev/null || true)
if [ -z "$BILLING" ] || [ "$BILLING" = "None" ]; then
  echo ""
  echo "!! No billing account linked to $PROJECT_ID."
  echo "   Open https://console.cloud.google.com/billing in your browser,"
  echo "   start the FREE TRIAL (\$300 / 90 days, no auto-charge), then link the"
  echo "   billing account to project $PROJECT_ID, and re-run this script."
  exit 2
fi

# 3. enable APIs + deploy (build happens in Cloud Build)
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com -o none > /dev/null 2>&1 || true

echo "building + deploying (5-8 min) ..."
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8501 \
  --cpu 1 --memory 2Gi \
  --min-instances 0 --max-instances 3 \
  --set-env-vars STREAMLIT_SERVER_HEADLESS=true,STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format="value(status.url)")
echo ""
echo "=================================================="
echo "LIVE: $URL"
echo "=================================================="
