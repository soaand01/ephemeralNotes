# Ephemeral Notes ✨📝

Created by Anderson Lopes (<andlopes@microsoft.com>)

A small, privacy-minded ephemeral notes app for local development and testing. Notes are stored in Redis with a TTL and can be optionally password protected and/or set to burn after reading.

---

**Quick Links**

- Local quick start: see "Quick start (local)" below
- Tech used: Flask, Redis, Gunicorn

---

## Quick start (local) 🚀

1) Install Redis (local dev):

```bash
sudo apt update
sudo apt install -y redis-server
sudo systemctl enable --now redis-server
```

2) Create & activate a virtualenv and install dependencies:

```bash
cd /home/andlopes/labs/ephemeralNotes
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3) Run the app (development):

```bash
export REDIS_URL=redis://localhost:6379/0
export EXTERNAL_HOST=http://localhost:8080
# Generate a secure SECRET_KEY (do not share or commit this value)
export SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(32))")

# Option A: Flask dev server with autoreload
FLASK_APP=app FLASK_ENV=development flask run --host=0.0.0.0 --port=8080

# Option B: run the bundled simple server (no autoreload)
python3 app.py
```

Visit: http://localhost:8080

Run tests:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest -q
```

---

## Environment Variables 🌐

To run the application, you need to set the following environment variables:

1. **`REDIS_URL`**:
   - This specifies the connection URL for your Redis instance.
   - Structure: `rediss://<username>:<password>@<host>:<port>/<db>`
     - `<username>`: The username for Redis authentication (e.g., `default`).
     - `<password>`: The Redis access key (e.g., "Shared key primary").
     - `<host>`: The Redis host URL (e.g., `your-redis-name.redis.cache.windows.net`).
     - `<port>`: The port number (e.g., `6380` for SSL connections).
     - `<db>`: The database index (e.g., `0`).
   - Example:
     ```bash
     export REDIS_URL="rediss://default:<your-redis-password>@your-redis-name.redis.cache.windows.net:6380/0"
     ```

2. **`REDIS_PASSWORD`**:
   - This is the password (access key) for your Redis instance.
   - Use the "Shared key primary" from your Azure Redis instance.
   - Example:
     ```bash
     export REDIS_PASSWORD="<your-redis-password>"
     ```

3. **`SECRET_KEY`**:
   - A secure key used by Flask for session management and cryptographic operations.
   - Generate a secure key using the following command:
     ```bash
     export SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(32))")
     ```

4. **`EXTERNAL_HOST`**:
   - The external URL where your application is hosted.
   - Example:
     ```bash
     export EXTERNAL_HOST="http://localhost:8080"
     ```

---

## Tech stack / Used technologies

- ⚗️ **Flask** — lightweight Python web framework
- 🧠 **Redis** — ephemeral data store for notes + TTL
- 🦄 **Gunicorn** — WSGI server for production

Other dev tools: `python-dotenv`, `Flask-Limiter`, `Flask-Talisman`, `markdown`, `bleach`.

Recent UI and usability changes:

- Homepage now displays two compact stat cards side-by-side: **🗂️ Total Notes** (total created) and **🔥 Active Notes** (currently active keys in Redis). This helps at-a-glance monitoring during local hosting.
- The Recent Notes table shows the 12 most recent creation events with masked tokens and TTL/flags metadata (no plaintext content shown).
- Button styles and spacing were unified across pages for visual consistency.
- **New Statistics Added**: The dashboard now includes:
  - Notes Created in the Last 24 Hours
  - Notes Expired Automatically
  - Most Shared Note
  - Peak Usage Time
- **Clarity Analytics**: Integrated for tracking user interactions.
- **Welcome Message**: Updated with emojis for a more engaging user experience.

---

## Deploying to Azure Web Apps (notes)

You can deploy this app to Azure Web Apps as a containerized app (recommended path):

1. Build and push the image to a registry (ACR or Docker Hub).
2. Create an Azure Web App for Containers and point it to the image.
3. Configure app settings in the Azure Portal (set `SECRET_KEY`, `REDIS_URL`, `EXTERNAL_HOST`, and `PORT` if needed).
4. Enable a health check on `/healthz` and configure readiness/liveness probes if desired.

If you'd like, I can add a step-by-step `azure-deploy.md` and a GitHub Actions workflow that builds and pushes the image to Azure Container Registry (but you requested you will push manually, so I won't enable an automated push).

---

## Security notes

- Keep `SECRET_KEY` out of the repo. Use environment variables or secrets stores in production.
- Rotate `SECRET_KEY` if the `.env` was ever committed (there was a local `.env` previously — rotate it now).
- Consider enabling `force_https=True` in `Talisman` when behind TLS.

