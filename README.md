# Ephemeral Notes (Local Development)

This repository is configured for local development and testing without Docker. Run the app locally with Python and a local Redis instance.

Quick start (local)
1. Install Redis server:
   ```bash
   sudo apt update
   sudo apt install -y redis-server
   sudo systemctl enable --now redis-server
   ```

2. Create and activate a virtualenv, install deps:
   ```bash
   cd /home/andlopes/labs/ephemeralNotes
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Set environment variables and run the app:
   ```bash
   export REDIS_URL=redis://localhost:6379/0
   export EXTERNAL_HOST=http://localhost:8080
   export SECRET_KEY=$(python -c 'import secrets;print(secrets.token_urlsafe(24))')

   # Run dev server with auto-reload
   FLASK_APP=app FLASK_ENV=development flask run --host=0.0.0.0 --port=8080

   # Or run the bundled simple server (no reloader)
   python3 app.py
   ```

4. Open http://localhost:8080 in your browser.

Run tests (no Redis required)
```bash
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

If you later want Docker support again, tell me and I'll add a clean Dockerfile and compose files back.
