#!/usr/bin/env bash
# =============================================================================
# Azure deployment FROM CLOUD SHELL (in portal.azure.com)
# No local az login, no Docker needed — Cloud Shell is already authenticated,
# and the image is built inside Azure Container Registry (az acr build).
#
# HOW TO USE (in the Azure portal):
#   1. Click the  >_  (Cloud Shell) icon in the TOP BAR of portal.azure.com
#   2. Choose "Bash" if asked (first use takes ~30s to set up storage)
#   3. Paste this whole command and press Enter:
#
#   curl -fsSL https://raw.githubusercontent.com/twomathematicians-code/leibniz/main/deploy/cloudshell-deploy.sh | bash
# =============================================================================
set -euo pipefail

RG="rg-scitamehtam"
LOCATION="westeurope"
ACR="scitamehtam$RANDOM"          # globally unique, lowercase alnum
APP="leibniz-engine"
ENV="scitamehtam-env"

echo "== SCITAMEHTAM Leibniz -> Azure (Cloud Shell) =="

# 0. must have a subscription
SUB=$(az account show --query name -o tsv) || { echo "No subscription on this account. Create one at azure.microsoft.com/free"; exit 1; }
echo "subscription: $SUB"

# 1. get the code
rm -rf leibniz && git clone -q --depth 1 https://github.com/twomathematicians-code/leibniz.git
cd leibniz

# 2. resource group + registry
az group create -n "$RG" -l "$LOCATION" -o none
az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true -o none
echo "registry: $ACR.azurecr.io (building image — 3-6 min, no local Docker needed)"
az acr build -r "$ACR" -t leibniz-app:latest --file deploy/Dockerfile.streamlit . -o none

# 3. container app
ACR_SERVER="$ACR.azurecr.io"
ACR_PASS=$(az acr credential show -n "$ACR" --query "passwords[0].value" -o tsv)
az containerapp env create -n "$ENV" -g "$RG" -l "$LOCATION" -o none
if az containerapp show -n "$APP" -g "$RG" >/dev/null 2>&1; then
  az containerapp update -n "$APP" -g "$RG" --image "$ACR_SERVER/leibniz-app:latest" -o none
else
  az containerapp create -n "$APP" -g "$RG" --environment "$ENV" \
    --image "$ACR_SERVER/leibniz-app:latest" \
    --target-port 8501 --ingress external \
    --min-replicas 1 --max-replicas 3 \
    --cpu 1.0 --memory 2.0Gi \
    --registry-server "$ACR_SERVER" --registry-username "$ACR" --registry-password "$ACR_PASS" \
    -o none
fi

# 4. the live URL
FQDN=$(az containerapp show -n "$APP" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv)
echo ""
echo "=================================================="
echo "LIVE: https://$FQDN"
echo "=================================================="
