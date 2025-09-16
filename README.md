# Ephemeral Notes ✨📝

A small, privacy-minded ephemeral notes app for local development and testing. Notes are stored in Redis with a TTL and can be optionally password protected and/or set to burn after reading.

---

**Quick Links**

- Local quick start: see "Quick start (local)" below
- Docker quick start: see "Quick start (docker)"
- Tech used: Flask, Redis, Gunicorn, Docker
 - UI updates: homepage now shows two stat cards (🗂️ Total Notes and 🔥 Active Notes)
 - Recent notes: the Recent Notes list shows the 12 most recent creations (was 10)

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

## Quick start (docker) 🐳

This repo includes a multi-stage `Dockerfile` and a `docker-compose.yml` for local testing.

Build & run with Docker Compose:

```bash
docker compose up --build
```

The app will be available at `http://localhost:8080` and Redis will be started by compose.

Run the image directly (example):

```bash
docker build -t ephemeralnotes:latest .
docker run -e REDIS_URL=redis://<redis-host>:6379/0 -e SECRET_KEY="replace-me" -p 8080:8080 ephemeralnotes:latest
```

Notes for Docker / production-ready deploy:

- Do not embed secrets in `docker-compose.yml` — use environment files, Docker secrets, or your cloud provider's secret store.
- Configure `EXTERNAL_HOST` to the external URL used by your deployment.
- When running behind TLS (e.g., Azure Web Apps, a reverse proxy), set `Talisman(..., force_https=True)` or ensure TLS is enforced by the platform.
- The app exposes `/healthz` for a simple health probe.

Local cleanup & git hygiene

- The repository excludes local virtualenvs and cache files via `.gitignore` (e.g. `.venv/`, `__pycache__/`, `*.pyc`, `.env`).
- I removed local development artifacts (`.venv/`, `__pycache__`) from the workspace to avoid accidental commits. If you want these removals committed and pushed I can make the commit (you requested manual pushes previously).

---

## Tech stack / Used technologies

Logos are small linked images; if you prefer local logos add them to `static/img/` and reference them instead.

- ⚗️ **Flask** — lightweight Python web framework
- 🧠 **Redis** — ephemeral data store for notes + TTL
- 🦄 **Gunicorn** — WSGI server for production
- 🐳 **Docker** — containerization for local dev and deployment

Other dev tools: `python-dotenv`, `Flask-Limiter`, `Flask-Talisman`, `markdown`, `bleach`.

Recent UI and usability changes

- Homepage now displays two compact stat cards side-by-side: **🗂️ Total Notes** (total created) and **🔥 Active Notes** (currently active keys in Redis). This helps at-a-glance monitoring during local hosting.
- The Recent Notes table shows the 12 most recent creation events with masked tokens and TTL/flags metadata (no plaintext content shown).
- Button styles and spacing were unified across pages for visual consistency.

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

Recommended next steps

- Add CSRF protection for form endpoints (Flask-WTF or other CSRF middleware).
- Consider using Redis keyspace notifications or an atomic counter if you need an exact active-note count (current implementation uses a capped SCAN for a lightweight estimate).

---

If you'd like the README to include local logos copied into `static/img/` or a demo GIF, tell me where you'd like the assets and I will add them (I will not push any commits unless you ask me to).

