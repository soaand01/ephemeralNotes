# Azure Web Apps Deployment Guide

This document has copy-paste-ready CLI steps for both App Service (Code) and Web App for Containers.

A) App Service (Linux) — Code deployment with Oryx
-------------------------------------------------

1. Create a resource group
   ```bash
   az group create -n myRg -l eastus
   ```

2. Create an App Service plan (Linux)
   ```bash
   az appservice plan create -n myPlan -g myRg --is-linux --sku B1
   ```

3. Create the webapp (Python 3.11)
   ```bash
   az webapp create -n my-ephemeral-notes -g myRg -p myPlan --runtime "PYTHON|3.11"
   ```

4. Configure App Settings (replace placeholders)
   ```bash
   az webapp config appsettings set -n my-ephemeral-notes -g myRg --settings \
     SCM_DO_BUILD_DURING_DEPLOYMENT=1 \
     FLASK_ENV=production \
     SECRET_KEY="<replace_with_secure_value>" \
     REDIS_URL="<your_redis_connection_string>" \
     EXTERNAL_HOST="https://my-ephemeral-notes.azurewebsites.net"
   ```

5. Set Startup Command (in Portal or via CLI)
   Startup Command:
   ```
   bash azure/startup.sh
   ```

6. Deploy (zip deploy)
   ```bash
   az webapp deploy -n my-ephemeral-notes -g myRg --src-path ./ -t zip
   ```

7. Enable logs (optional):
   ```bash
   az webapp log config -n my-ephemeral-notes -g myRg --application-logging true
   ```

8. Verify:
   ```
   curl -v https://my-ephemeral-notes.azurewebsites.net/healthz
   ```

Notes:
- For Azure Cache for Redis, prefer using the primary connection string (rediss://) and include SSL options as provided by Azure.
- Consider enabling Managed Identity and store `SECRET_KEY` in Key Vault. Then reference Key Vault secret in App Settings.

B) Web App for Containers
-------------------------

1. Build Docker image and push to ACR (example)
   ```bash
   az acr create -n myRegistry -g myRg --sku Basic
   az acr login -n myRegistry
   docker build -t myRegistry.azurecr.io/ephemeral-notes:latest .
   docker push myRegistry.azurecr.io/ephemeral-notes:latest
   ```

2. Create Web App for Containers
   ```bash
   az webapp create -n my-ephemeral-notes -g myRg -p myPlan --deployment-container-image-name myRegistry.azurecr.io/ephemeral-notes:latest
   ```

3. Configure App Settings:
   ```bash
   az webapp config appsettings set -n my-ephemeral-notes -g myRg --settings \
     WEBSITES_PORT=8080 \
     FLASK_ENV=production \
     SECRET_KEY="<secure>" \
     REDIS_URL="<your_redis_connection_string>" \
     EXTERNAL_HOST="https://my-ephemeral-notes.azurewebsites.net"
   ```

4. Configure registry access if ACR is private:
   ```bash
   az webapp config container set -n my-ephemeral-notes -g myRg \
     --docker-custom-image-name myRegistry.azurecr.io/ephemeral-notes:latest \
     --docker-registry-server-url https://myRegistry.azurecr.io \
     --docker-registry-server-user <username> \
     --docker-registry-server-password <password>
   ```

5. Verify `/healthz` endpoint once the app is running.

Managed Identity + Key Vault (brief)
-----------------------------------
- Assign a system-assigned Managed Identity to the Web App.
- Grant the identity access to secrets in Key Vault.
- In App Settings, reference Key Vault secrets with the syntax:
  - `@Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/<name>/<version>)`
- The Web App will retrieve secrets at runtime from Key Vault.

Networking notes
----------------
- For Azure Cache for Redis, prefer enabling TLS and using the `rediss://` scheme. If your cache is in a VNet, ensure App Service has VNet integration.
