#!/usr/bin/env bash
# =============================================================================
# Azure deployment for SCITAMEHTAM Leibniz (Streamlit app)
# Container Apps + Azure Container Registry — one script, end to end.
#
# Prereqs: az CLI logged in (az login), Docker daemon running.
# Usage:   bash deploy/azure-deploy.sh
# Customise the variables below (or export them beforehand).
# =============================================================================
set -euo pipefail

# --- configuration ----------------------------------------------------------
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-scitamehtam}"
LOCATION="${LOCATION:-westeurope}"            # closest to Ghent
ACR_NAME="${ACR_NAME:-scitamehtamacr}"        # globally unique, lowercase
APP_NAME="${APP_NAME:-leibniz-engine}"        # yourapp.<region>.azurecontainerapps.io
IMAGE_TAG="${IMAGE_TAG:-latest}"
ENV_NAME="${ENV_NAME:-scitamehtam-env}"

echo "== SCITAMEHTAM Leibniz -> Azure Container Apps =="
az account show --query name -o tsv || { echo "Run 'az login' first."; exit 1; }

# 1. resource group
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" -o none

# 2. container registry
az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" \
    --sku Basic --admin-enabled true -o none
ACR_SERVER=$(az acr show -n "$ACR_NAME" --query loginServer -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR_NAME" --query "passwords[0].value" -o tsv)
docker login "$ACR_SERVER" -u "$ACR_NAME" -p "$ACR_PASS"

# 3. build + push
docker build -t "$ACR_SERVER/leibniz-app:$IMAGE_TAG" \
    -f deploy/Dockerfile.streamlit .
docker push "$ACR_SERVER/leibniz-app:$IMAGE_TAG"

# 4. container apps environment + app
az containerapp env create --name "$ENV_NAME" \
    --resource-group "$RESOURCE_GROUP" --location "$LOCATION" -o none

if az containerapp show -n "$APP_NAME" -g "$RESOURCE_GROUP" >/dev/null 2>&1; then
  echo "App exists — updating image."
  az containerapp update -n "$APP_NAME" -g "$RESOURCE_GROUP" \
      --image "$ACR_SERVER/leibniz-app:$IMAGE_TAG" -o none
else
  az containerapp create --name "$APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --environment "$ENV_NAME" \
      --image "$ACR_SERVER/leibniz-app:$IMAGE_TAG" \
      --target-port 8501 --ingress external \
      --min-replicas 1 --max-replicas 3 \
      --cpu 1.0 --memory 2.0Gi \
      --registry-server "$ACR_SERVER" \
      --registry-username "$ACR_NAME" \
      --registry-password "$ACR_PASS" \
      -o none
fi

# 5. report the live URL
FQDN=$(az containerapp show -n "$APP_NAME" -g "$RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn -o tsv)
echo ""
echo "LIVE: https://$FQDN"
