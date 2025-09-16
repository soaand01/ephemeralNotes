#!/usr/bin/env bash
set -euo pipefail

# Usage:
# Provide environment variables before running or let GitHub Actions set them:
# AZURE_SUBSCRIPTION_ID, RESOURCE_GROUP, LOCATION, ACR_NAME, WEBAPP_NAME

echo "Provision script starting"

if [ -z "${AZURE_SUBSCRIPTION_ID:-}" ]; then
  echo "AZURE_SUBSCRIPTION_ID must be set" >&2
  exit 1
fi
if [ -z "${RESOURCE_GROUP:-}" ]; then
  echo "RESOURCE_GROUP must be set" >&2
  exit 1
fi

LOCATION=${LOCATION:-westeurope}
if [ -z "${ACR_NAME:-}" ]; then
  echo "ACR_NAME must be set" >&2
  exit 1
fi
if [ -z "${WEBAPP_NAME:-}" ]; then
  echo "WEBAPP_NAME must be set" >&2
  exit 1
fi

echo "Using subscription: $AZURE_SUBSCRIPTION_ID"
az account set --subscription "$AZURE_SUBSCRIPTION_ID"

echo "Creating resource group: $RESOURCE_GROUP in $LOCATION"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

echo "Creating ACR: $ACR_NAME"
az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Standard --admin-enabled false

ACR_LOGIN_SERVER=$(az acr show -n "$ACR_NAME" -g "$RESOURCE_GROUP" --query loginServer -o tsv)
echo "ACR login server: $ACR_LOGIN_SERVER"

REDIS_NAME="${WEBAPP_NAME}-redis"
echo "Creating Azure Cache for Redis: $REDIS_NAME"
az redis create --name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" --sku Basic --vm-size C0 --minimum-tls-version 1.2

APP_PLAN="${WEBAPP_NAME}-plan"
echo "Creating App Service plan: $APP_PLAN"
az appservice plan create --name "$APP_PLAN" --resource-group "$RESOURCE_GROUP" --is-linux --sku S1

echo "Creating Web App: $WEBAPP_NAME"
az webapp create --resource-group "$RESOURCE_GROUP" --plan "$APP_PLAN" --name "$WEBAPP_NAME" --deployment-container-image-name "hello-world:latest"

echo "Assigning system-assigned identity to Web App"
az webapp identity assign --resource-group "$RESOURCE_GROUP" --name "$WEBAPP_NAME"

# Grant AcrPull role to the web app's identity so it can pull from ACR
PRINCIPAL_ID=$(az webapp show -g "$RESOURCE_GROUP" -n "$WEBAPP_NAME" --query identity.principalId -o tsv)
ACR_ID=$(az acr show -n "$ACR_NAME" -g "$RESOURCE_GROUP" --query id -o tsv)
echo "Assigning AcrPull role to principal $PRINCIPAL_ID on $ACR_ID"
az role assignment create --assignee-object-id "$PRINCIPAL_ID" --assignee-principal-type ServicePrincipal --role "AcrPull" --scope "$ACR_ID" || true

echo "Provisioning complete"
echo "ACR_LOGIN_SERVER=$ACR_LOGIN_SERVER"
echo "REDIS_NAME=$REDIS_NAME"
echo "WEBAPP_NAME=$WEBAPP_NAME"
