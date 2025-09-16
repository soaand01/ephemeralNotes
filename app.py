#!/usr/bin/env python3
"""
ephemeral-notes: Minimal production-ready ephemeral notes app.

Core behaviors:
- Create anonymous note with TTL stored in Redis via SETEX.
- View-only share link: /s/<token>
- Optional features enabled via constants below.

Run:
  gunicorn -w 2 -k gthread -b 0.0.0.0:${PORT:-8080} app:app
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    flash,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from redis import Redis, from_url as redis_from_url
from werkzeug.middleware.proxy_fix import ProxyFix

from dotenv import load_dotenv
import os
import markdown as md
import bleach
import redis
from azure.identity import DefaultAzureCredential
from redis_entraid.cred_provider import create_from_default_azure_credential

# Load .env if present
load_dotenv()

# ---------------------------
# Feature flags (as requested)
# ---------------------------
BURN_AFTER_READ = True
PASSWORD_PROTECT = True
VIEW_LIMIT_ENABLED = False
MARKDOWN_ENABLED = True
CUSTOM_TTL_CHOICES = True
QR_CODE_ENABLED = False
CLIENT_SIDE_ENCRYPTION = False

# ---------------------------
# Configuration from env
# ---------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
REDIS_URL = os.getenv("REDIS_URL", "")
DEFAULT_TTL_SECONDS = int(os.getenv("DEFAULT_TTL_SECONDS", "900"))
MAX_CONTENT_CHARS = 20000  # 20k chars ~ safe
MAX_CONTENT_BYTES = 20 * 1024  # 20KB limit for entire request payload
RATE_LIMIT_CREATE = os.getenv("RATE_LIMIT_CREATE", "10 per minute")
RATE_LIMIT_VIEW = os.getenv("RATE_LIMIT_VIEW", "60 per minute")
EXTERNAL_HOST = os.getenv("EXTERNAL_HOST", "http://localhost:5000")
PASSWORD_POLICY_MINLEN = int(os.getenv("PASSWORD_POLICY_MINLEN", "6"))
PORT = int(os.getenv("PORT", os.getenv("WEBSITES_PORT", "8080")))

# ---------------------------
# Flask app & extensions
# ---------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=MAX_CONTENT_BYTES,
)

# Register any extra, small routes from a helper module
try:
    from extra_routes import register as _register_extra_routes
    _register_extra_routes(app)
except Exception as e:
    # non-fatal: continue if extra routes fail to import, but print for debugging
    print('Failed to import/register extra_routes:', e)

# Security: CSP and Talisman
CSP = {
    "default-src": ["'self'"],
    "script-src": [
        "'self'",
        "https://cdn.jsdelivr.net",
        "https://cdnjs.cloudflare.com",
    ],
    "style-src": [
        "'self'",
        "https://cdn.jsdelivr.net",
        "https://cdnjs.cloudflare.com",
        "'unsafe-inline'",
    ],
    "img-src": ["'self'", "data:"],
    "frame-ancestors": ["'none'"],
}
Talisman = Talisman  # type: ignore
talisman = Talisman(
    app,
    content_security_policy=CSP,
    force_https=False,  # set to True behind TLS/HTTPS in production if desired
    strict_transport_security=True,
    strict_transport_security_max_age=31536000,
)

# Redis client creation (wrapped for testability)
def create_redis_client() -> Redis:
    # Use Access Keys for authentication with password from environment variable
    client = redis.Redis(
        host="ephemeralnotes.redis.cache.windows.net",
        port=6380,
        username="default",
        password=os.getenv("REDIS_PASSWORD"),
        ssl=True,
        decode_responses=True,
    )
    return client


redis_client: Redis = create_redis_client()
app.redis_client = redis_client  # expose for tests

# Rate limiter using Redis storage (uses same redis URL)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri=REDIS_URL,
)


# ---------------------------
# Utilities
# ---------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _note_key(token: str) -> str:
    return f"note:{token}"


def generate_token() -> str:
    return secrets.token_urlsafe(24)


# Password hashing using PBKDF2 (store as algorithm$iterations$salt$hex)
def hash_password(password: str, iterations: int = 150_000) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"


def verify_password(stored: str, provided: str) -> bool:
    try:
        algorithm, iterations_s, salt, hexhash = stored.split("$")
        iterations = int(iterations_s)
        dk = hashlib.pbkdf2_hmac("sha256", provided.encode("utf-8"), salt.encode(), iterations)
        return hmac.compare_digest(dk.hex(), hexhash)
    except Exception:
        return False


def _store_note(token: str, data: Dict[str, Any], ttl: int) -> None:
    key = _note_key(token)
    payload = json.dumps(data, ensure_ascii=False)
    # Use SETEX for TTL enforcement
    app.redis_client.setex(key, ttl, payload)


def _get_note_raw(token: str) -> Optional[Dict[str, Any]]:
    key = _note_key(token)
    raw = app.redis_client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _delete_note(token: str) -> None:
    app.redis_client.delete(_note_key(token))


def _decrement_view_limit(data: Dict[str, Any]) -> None:
    # Not used if VIEW_LIMIT_ENABLED is false
    if "view_limit" not in data or data.get("view_limit") is None:
        return
    try:
        data["view_limit"] = int(data["view_limit"]) - 1
    except Exception:
        data["view_limit"] = 0


# ---------------------------
# Routes
# ---------------------------

@app.route("/")
def index():
    ttl_choices = [300, 900, 3600] if CUSTOM_TTL_CHOICES else [DEFAULT_TTL_SECONDS]
    labels = {300: "5 minutes", 900: "15 minutes (default)", 3600: "60 minutes"}
    # Read lightweight creation history (no note content)
    try:
        total_created = int(app.redis_client.get('stats:created_total') or 0)
    except Exception:
        total_created = 0

    notes = []
    try:
        # fetch only the 12 most recent creation events
        raw = app.redis_client.lrange('history:creations', 0, 11) or []
        for item in raw:
            try:
                obj = json.loads(item)
            except Exception:
                continue
            # provide a human-readable created_at display (UTC)
            try:
                ts = datetime.fromisoformat(obj.get('created_at'))
                obj['created_at_display'] = ts.strftime('%Y-%m-%d %H:%M:%S UTC')
            except Exception:
                obj['created_at_display'] = obj.get('created_at')
            notes.append(obj)
    except Exception:
        notes = []
    # Compute a lightweight count of active notes without blocking Redis.
    active_notes = 0
    try:
        # Use scan_iter for non-blocking iteration; limit to first 1000 keys for speed.
        for i, _ in enumerate(app.redis_client.scan_iter(match='note:*', count=1000)):
            active_notes += 1
            if i >= 999:
                break
    except Exception:
        active_notes = 0

    return render_template(
        "index.html",
        ttl_choices=ttl_choices,
        labels=labels,
        default_ttl=DEFAULT_TTL_SECONDS,
        feature_flags={
            "password_protect": PASSWORD_PROTECT,
            "markdown": MARKDOWN_ENABLED,
            "custom_ttl": CUSTOM_TTL_CHOICES,
            "burn_after_read": True,
        },
        total=total_created,
        notes=notes,
        active_notes=active_notes,
    )


def _index_context():
    """Return the common context used to render the index page.

    This ensures when handlers render `index.html` due to validation errors they
    pass the same feature flags, ttl choices, labels and recent notes as the
    normal `index` view.
    """
    ttl_choices = [300, 900, 3600] if CUSTOM_TTL_CHOICES else [DEFAULT_TTL_SECONDS]
    labels = {300: "5 minutes", 900: "15 minutes (default)", 3600: "60 minutes"}
    try:
        total_created = int(app.redis_client.get('stats:created_total') or 0)
    except Exception:
        total_created = 0

    notes = []
    try:
        raw = app.redis_client.lrange('history:creations', 0, 11) or []
        for item in raw:
            try:
                obj = json.loads(item)
            except Exception:
                continue
            try:
                ts = datetime.fromisoformat(obj.get('created_at'))
                obj['created_at_display'] = ts.strftime('%Y-%m-%d %H:%M:%S UTC')
            except Exception:
                obj['created_at_display'] = obj.get('created_at')
            notes.append(obj)
    except Exception:
        notes = []

    return {
        'ttl_choices': ttl_choices,
        'labels': labels,
        'default_ttl': DEFAULT_TTL_SECONDS,
        'feature_flags': {
            'password_protect': PASSWORD_PROTECT,
            'markdown': MARKDOWN_ENABLED,
            'custom_ttl': CUSTOM_TTL_CHOICES,
            'burn_after_read': True,
        },
        'total': total_created,
        'notes': notes,
    }


@app.route("/notes", methods=["POST"])
@limiter.limit(RATE_LIMIT_CREATE)
def create_note():
    content = (request.form.get("content") or "").strip()
    if not content:
        ctx = _index_context()
        ctx.update({"error": "Note cannot be empty."})
        return render_template("index.html", **ctx), 400
    if len(content) > MAX_CONTENT_CHARS:
        ctx = _index_context()
        ctx.update({"error": "Note is too long."})
        return render_template("index.html", **ctx), 400

    ttl = DEFAULT_TTL_SECONDS
    if CUSTOM_TTL_CHOICES:
        try:
            ttl_selected = int(request.form.get("ttl", str(DEFAULT_TTL_SECONDS)))
            if ttl_selected in (300, 900, 3600):
                ttl = ttl_selected
        except Exception:
            pass

    token = generate_token()
    note_obj: Dict[str, Any] = {
        "content": content,
        "created_at": _now_iso(),
        "ttl_seconds": ttl,
        # Per-note burn-after-read: creator opts in via form checkbox
        "burn_after_read": bool(request.form.get("burn_after_read")),
        "markdown": bool(request.form.get("markdown") and MARKDOWN_ENABLED),
        "is_client_encrypted": False,
    }

    # Optional password protection
    if PASSWORD_PROTECT:
        pwd = request.form.get("password", "")
        if pwd:
            if len(pwd) < PASSWORD_POLICY_MINLEN:
                ctx = _index_context()
                ctx.update({"error": "Password too short."})
                return render_template("index.html", **ctx), 400
            note_obj["password_hash"] = hash_password(pwd)

    # Optional view_limit (not enabled)
    if VIEW_LIMIT_ENABLED:
        try:
            note_obj["view_limit"] = int(request.form.get("view_limit", 0)) or None
        except Exception:
            note_obj["view_limit"] = None

    # Store via SETEX
    _store_note(token, note_obj, ttl)

    # Record creation event (no content). Keep a capped list of recent creations.
    try:
        event = {
            "created_at": note_obj["created_at"],
            "token_mask": f"{token[:4]}...{token[-4:]}",
            "ttl_seconds": ttl,
            "burn_after_read": bool(note_obj.get("burn_after_read", False)),
            "password_protected": "password_hash" in note_obj,
            "markdown": bool(note_obj.get("markdown", False)),
        }
        app.redis_client.incr('stats:created_total')
        app.redis_client.lpush('history:creations', json.dumps(event, ensure_ascii=False))
        app.redis_client.ltrim('history:creations', 0, 199)
    except Exception:
        pass

    # Build absolute share URL from the incoming request host (works for local dev and behind proxies)
    share_url = url_for('view_note', token=token, _external=True)
    return render_template("share.html", share_url=share_url, token=token, ttl=ttl)


@app.route("/s/<token>", methods=["GET"])
@limiter.limit(RATE_LIMIT_VIEW)
def view_note(token: str):
    note = _get_note_raw(token)
    if note is None:
        return render_template("expired.html"), 410

    # Password protected?
    if PASSWORD_PROTECT and "password_hash" in note:
        unlocked = session.get("unlocked_tokens", [])
        if token not in unlocked:
            # compute remaining TTL for display on password form
            try:
                remaining = app.redis_client.ttl(_note_key(token))
                if remaining is None or remaining < 0:
                    remaining = 0
            except Exception:
                remaining = 0
            # render view page which will contain a password form (no password in query)
            return render_template("view.html", note=None, token=token, need_password=True, remaining_seconds=remaining), 200

    # Serve the content (read-only)
    content = note.get("content", "")
    is_markdown = bool(note.get("markdown", False)) and MARKDOWN_ENABLED

    # If markdown rendering is enabled for this note, render + sanitize server-side
    if is_markdown:
        # Render markdown to HTML and sanitize with bleach
        raw_html = md.markdown(content, extensions=["extra", "sane_lists"])
        allowed_tags = bleach.sanitizer.ALLOWED_TAGS | {
            "p",
            "pre",
            "code",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "hr",
            "br",
        }
        allowed_attrs = {
            "a": ["href", "title", "rel", "target"],
            "img": ["src", "alt", "title"],
        }
        cleaned = bleach.clean(raw_html, tags=allowed_tags, attributes=allowed_attrs, strip=True)
        # Also linkify any URLs
        content = bleach.linkify(cleaned)

    # Determine remaining TTL to show client-side (Redis-managed TTL)
    try:
        remaining = app.redis_client.ttl(_note_key(token))
        if remaining is None or remaining < 0:
            remaining = 0
    except Exception:
        remaining = 0

    # Burn after read or view limits
    if BURN_AFTER_READ and note.get("burn_after_read"):
        # delete after computing remaining TTL so we can show it on the page
        _delete_note(token)
    elif VIEW_LIMIT_ENABLED:
        _decrement_view_limit(note)
        remaining_ttl = note.get("ttl_seconds", DEFAULT_TTL_SECONDS)
        # store back updated note if still >0
        if note.get("view_limit", None) and int(note.get("view_limit", 0)) > 0:
            _store_note(token, note, remaining_ttl)
        else:
            _delete_note(token)

    return render_template(
        "view.html",
        note={"content": content, "markdown": is_markdown},
        token=token,
        need_password=False,
        remaining_seconds=remaining,
    )


@app.route("/s/<token>/unlock", methods=["POST"])
@limiter.limit(RATE_LIMIT_VIEW)
def unlock_note(token: str):
    if not PASSWORD_PROTECT:
        return redirect(url_for("view_note", token=token))

    note = _get_note_raw(token)
    if note is None:
        return render_template("expired.html"), 410

    pwd = request.form.get("password", "")
    if not pwd:
        return render_template("view.html", token=token, need_password=True, error="Password required."), 400

    stored = note.get("password_hash")
    if not stored or not verify_password(stored, pwd):
        # Avoid leaking whether token exists; show generic message
        return render_template("view.html", token=token, need_password=True, error="Incorrect password."), 403

    # Mark token unlocked in session
    unlocked = session.get("unlocked_tokens", [])
    if token not in unlocked:
        unlocked.append(token)
        session["unlocked_tokens"] = unlocked

    return redirect(url_for("view_note", token=token))


@app.route("/s/<token>/delete", methods=["POST"])
def delete_note_handler(token: str):
    # Best-effort delete (no auth). This endpoint should be rate-limited by client IP via frontend
    _delete_note(token)
    return redirect(url_for("index"))


@app.route("/healthz", methods=["GET"])
def healthz():
    try:
        ok = app.redis_client.ping()
        if ok:
            return jsonify({"status": "ok"}), 200
        raise Exception("ping failed")
    except Exception:
        return jsonify({"status": "redis-unreachable"}), 500


# Admin-ish dashboard (read-only summaries; no note content displayed)
@app.route("/dashboard")
def dashboard():
    """Show a lightweight dashboard for local visibility (no plaintext note content).

    This endpoint is intentionally not exposed in tests and should be restricted in
    production behind auth or network controls.
    """
    try:
        keys = app.redis_client.keys("note:*") or []
    except Exception:
        keys = []

    notes = []
    # show most recent first (best-effort) and avoid reading content field
    for k in sorted(keys, reverse=True)[:200]:
        raw = app.redis_client.get(k)
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        token = k.split(":", 1)[1]
        notes.append(
            {
                "token": token,
                "token_mask": f"{token[:4]}...{token[-4:]}",
                "created_at": obj.get("created_at"),
                "ttl_seconds": obj.get("ttl_seconds"),
                "burn_after_read": obj.get("burn_after_read", False),
                "password_protected": "password_hash" in obj,
                "markdown": obj.get("markdown", False),
            }
        )

    total = len(keys)
    return render_template("dashboard.html", notes=notes, total=total)


# Informational pages
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# Error handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    return "Payload too large", 413


# Update the base template to include a link to the Test Redis page
@app.context_processor
def inject_nav_links():
    return {
        'nav_links': [
            {'name': 'Home', 'url': url_for('index')},
            {'name': 'Dashboard', 'url': url_for('dashboard')},
        ]
    }


# Run guard (for local dev)
if __name__ == "__main__":
    app.run(debug=True)
