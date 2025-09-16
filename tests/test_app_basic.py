import json
import pytest
from fakeredis import FakeRedis
import os
from app import app as flask_app, create_redis_client, _note_key
import app as app_module
from datetime import datetime, timezone


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = FakeRedis(decode_responses=True)
    monkeypatch.setattr(app_module, "redis_client", fake)
    monkeypatch.setattr(flask_app, "redis_client", fake)
    # also patch limiter storage to avoid external Redis use during tests
    yield fake


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as c:
        yield c


def test_create_and_view_note(client):
    resp = client.post("/notes", data={"content": "hello world"})
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "/s/" in html

    # Extract token from the returned HTML (simple parse)
    start = html.find("/s/")
    token = html[start + 3 :].split('"')[0].split(">")[0]
    view = client.get(f"/s/{token}")
    assert view.status_code == 200
    assert "hello world" in view.get_data(as_text=True)


def test_expired_note_shows_410(client, fake_redis):
    resp = client.post("/notes", data={"content": "temp note"})
    html = resp.get_data(as_text=True)
    start = html.find("/s/")
    token = html[start + 3 :].split('"')[0].split(">")[0]

    # Simulate expiry by deleting key
    fake_redis.delete(_note_key(token))

    r = client.get(f"/s/{token}")
    assert r.status_code == 410
    assert "expired" in r.get_data(as_text=True).lower()


def test_burn_after_read(client, fake_redis):
    # Burn after read enabled in this app configuration
    resp = client.post("/notes", data={"content": "burn me"})
    html = resp.get_data(as_text=True)
    start = html.find("/s/")
    token = html[start + 3 :].split('"')[0].split(">")[0]

    first = client.get(f"/s/{token}")
    assert first.status_code == 200
    assert "burn me" in first.get_data(as_text=True)

    second = client.get(f"/s/{token}")
    assert second.status_code == 410


def test_healthz_ok(client, fake_redis):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json["status"] == "ok"
