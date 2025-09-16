# Terraform provisioning for ephemeralNotes

This folder contains Terraform configuration to provision the Azure resources needed by ephemeralNotes:

- Resource Group
- Azure Container Registry (ACR)
- Azure Cache for Redis
- App Service Plan (Linux, Standard S1)
- Web App (Container)
- Role assignment to allow Web App to pull from ACR

Prerequisites
- Terraform 1.5+ installed
- Azure CLI installed and logged in, or provide a service principal via environment variables

Quick start

1. Login with Azure CLI:

```bash
az login
az account set --subscription <YOUR_SUBSCRIPTION_ID>
```

2. Initialize and apply:

```bash
cd infra
terraform init
terraform apply -var="resource_group=ephemeralnotes-rg" -var="acr_name=ephemeralnotesacr" -var="webapp_name=ephemeralnotes-prod"
```

3. Outputs will include ACR login server and Redis host.

Notes
- If your subscription has quota limits for Standard App Service SKUs in the chosen region, adjust `app_service_plan` or change `location`.
- For automation in CI, use a service principal and set `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_SUBSCRIPTION_ID`, `ARM_TENANT_ID` as env vars.
