#!/usr/bin/env bash
# Azure App Service Startup script (Code deployment via Oryx)
# This script is intended to be used as the App Service "Startup Command":
#   bash azure/startup.sh
set -euo pipefail

# Ensure PORT is set by App Service
PORT=${PORT:-${WEBSITES_PORT:-8080}}
export PORT

# Use Gunicorn to serve the app
exec gunicorn -w 2 -k gthread -b 0.0.0.0:${PORT} app:app
