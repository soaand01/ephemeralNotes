# Ephemeral Notes ✨📝

A tiny, privacy-first notes app for local development — notes expire automatically and can be password-protected. This README explains how to run the app locally for development and testing.

Quick start (local) 🚀

1) Install Redis server (used as a short-term store):

```bash
sudo apt update
sudo apt install -y redis-server
sudo systemctl enable --now redis-server
```

2) Create and activate a virtual environment and install dependencies:

```bash
cd /home/andlopes/labs/ephemeralNotes
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3) Set required environment variables and run the app:

```bash
export REDIS_URL=redis://localhost:6379/0
export EXTERNAL_HOST=http://localhost:8080
# Generate a secure SECRET_KEY (do not share or commit this value)
export SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(32))")

# Run dev server with auto-reload
FLASK_APP=app FLASK_ENV=development flask run --host=0.0.0.0 --port=8080

# Or run the bundled simple server (no reloader)
python3 app.py
```

4) Open your browser at: http://localhost:8080 🌐

Run tests (no Redis required for unit tests) ✅

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest -q
```

Notes & tips 💡
- Keep your `SECRET_KEY` secret — do not commit `.env` to the repo.
- If `.venv` was accidentally committed, it's safe to remove it and add it to `.gitignore` (already done in this repo).
- Want Docker support or a production-ready deploy? Ask and I can add a multi-stage Dockerfile and deployment notes.

