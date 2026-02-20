#!/usr/bin/env bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

# Deploy to Azure Container Apps
# ================================
#
# Builds a container image, pushes it to Azure Container Registry (ACR),
# and deploys it to Azure Container Apps. Container Apps auto-scales to
# zero and sets PORT automatically.
#
# Prerequisites (auto-detected and installed interactively):
#   - Azure CLI (az)
#   - Podman or Docker
#   - GEMINI_API_KEY set in your environment
#
# Usage:
#   ./deploy_azure.sh                                  # Interactive setup
#   ./deploy_azure.sh --resource-group=my-rg           # Explicit resource group
#   ./deploy_azure.sh --location=eastus                # Non-default location
#   ./deploy_azure.sh --app=my-genkit-app              # Custom app name

set -euo pipefail

cd "$(dirname "$0")"
source "$(dirname "$0")/scripts/_common.sh"

APP_NAME="${APP_NAME:-genkit-asgi}"
RESOURCE_GROUP="${RESOURCE_GROUP:-genkit-rg}"
LOCATION="${LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-genkitacr}"

# Parse arguments.
for arg in "$@"; do
  case "$arg" in
    --app=*) APP_NAME="${arg#*=}" ;;
    --resource-group=*) RESOURCE_GROUP="${arg#*=}" ;;
    --location=*) LOCATION="${arg#*=}" ;;
    --acr=*) ACR_NAME="${arg#*=}" ;;
    --help|-h)
      echo "Usage: ./deploy_azure.sh [--app=NAME] [--resource-group=RG] [--location=LOC] [--acr=ACR]"
      echo ""
      echo "Environment variables:"
      echo "  GEMINI_API_KEY    Required. Your Gemini API key."
      echo "  RESOURCE_GROUP    Azure resource group (default: genkit-rg)."
      echo "  LOCATION          Azure location (default: eastus)."
      echo ""
      echo "Options:"
      echo "  --app=NAME              Container App name (default: genkit-asgi)."
      echo "  --resource-group=RG     Resource group name."
      echo "  --location=LOC          Azure location (e.g. eastus, westeurope)."
      echo "  --acr=ACR               ACR name (default: genkitacr)."
      exit 0
      ;;
  esac
done

# ── Prerequisites ──────────────────────────────────────────────────────

# 1. Check Azure CLI is installed.
check_az_installed || exit 1

# 2. Check authentication.
check_az_auth || exit 1

# 3. Check GEMINI_API_KEY (interactive prompt if missing).
check_env_var "GEMINI_API_KEY" "https://aistudio.google.com/apikey" || exit 1

echo "🚀 Deploying ${APP_NAME} to Azure Container Apps (${LOCATION})..."
echo "   Resource Group: ${RESOURCE_GROUP}"
echo "   ACR:            ${ACR_NAME}"
echo ""

# ── Create resource group if needed ───────────────────────────────────

if ! az group show --name "${RESOURCE_GROUP}" &> /dev/null; then
  echo "📦 Creating resource group: ${RESOURCE_GROUP}..."
  az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}" > /dev/null
fi

# ── Create ACR if needed ──────────────────────────────────────────────

if ! az acr show --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" &> /dev/null; then
  echo "📦 Creating Azure Container Registry: ${ACR_NAME}..."
  az acr create \
    --name "${ACR_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --sku Basic \
    --admin-enabled true > /dev/null
fi

# ── Build and push container ──────────────────────────────────────────

ACR_LOGIN_SERVER=$(az acr show --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" \
  --query "loginServer" --output tsv)

echo "🏗️  Building and pushing container via ACR..."
az acr build \
  --registry "${ACR_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --image "${APP_NAME}:latest" \
  --file Containerfile \
  .

# ── Ensure Container Apps extension ───────────────────────────────────

az extension add --name containerapp --upgrade --yes 2>/dev/null || true
az provider register --namespace Microsoft.App --wait 2>/dev/null || true
az provider register --namespace Microsoft.OperationalInsights --wait 2>/dev/null || true

# ── Deploy to Container Apps ──────────────────────────────────────────

echo ""
echo "🚀 Deploying to Azure Container Apps..."

ACR_USERNAME=$(az acr credential show --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" \
  --query "username" --output tsv)
ACR_PASSWORD=$(az acr credential show --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" \
  --query "passwords[0].value" --output tsv)

# Check if the container app already exists.
if az containerapp show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" &> /dev/null; then
  echo "   Updating existing Container App..."
  az containerapp update \
    --name "${APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --image "${ACR_LOGIN_SERVER}/${APP_NAME}:latest" \
    --set-env-vars \
      "GEMINI_API_KEY=${GEMINI_API_KEY}" \
      "PORT=8080" > /dev/null
else
  echo "   Creating new Container App..."
  az containerapp create \
    --name "${APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --environment "${APP_NAME}-env" \
    --image "${ACR_LOGIN_SERVER}/${APP_NAME}:latest" \
    --registry-server "${ACR_LOGIN_SERVER}" \
    --registry-username "${ACR_USERNAME}" \
    --registry-password "${ACR_PASSWORD}" \
    --target-port 8080 \
    --ingress external \
    --min-replicas 0 \
    --max-replicas 2 \
    --cpu 0.5 \
    --memory 1.0Gi \
    --env-vars \
      "GEMINI_API_KEY=${GEMINI_API_KEY}" \
      "PORT=8080" > /dev/null
fi

# ── Output ────────────────────────────────────────────────────────────

APP_URL=$(az containerapp show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" \
  --query "properties.configuration.ingress.fqdn" --output tsv 2>/dev/null || echo "")

echo ""
echo "✅ Deployed!"
if [[ -n "$APP_URL" ]]; then
  echo "   URL:       https://${APP_URL}"
fi
echo "   Dashboard: https://portal.azure.com/#@/resource/subscriptions/$(az account show --query id --output tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/containerApps/${APP_NAME}"
echo "   Logs:      az containerapp logs show --name ${APP_NAME} --resource-group ${RESOURCE_GROUP}"
