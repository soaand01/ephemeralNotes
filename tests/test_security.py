import pytest
from fakeredis import FakeRedis
from app import app as flask_app, _note_key
import app as app_module


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = FakeRedis(decode_responses=True)
    monkeypatch.setattr(app_module, "redis_client", fake)
    monkeypatch.setattr(flask_app, "redis_client", fake)
    yield fake


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as c:
        yield c


def test_password_protected_flow(client, fake_redis):
    # Create password protected note
    resp = client.post("/notes", data={"content": "secret", "password": "s3cret!"})
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    start = html.find("/s/")
    token = html[start + 3 :].split('"')[0].split(">")[0]

    # GET should prompt for password
    get_resp = client.get(f"/s/{token}")
    assert "password" in get_resp.get_data(as_text=True).lower()

    # Wrong password
    wrong = client.post(f"/s/{token}/unlock", data={"password": "wrong"})
    assert wrong.status_code in (400, 403)
    assert "incorrect" in wrong.get_data(as_text=True).lower()

    # Correct password
    ok = client.post(f"/s/{token}/unlock", data={"password": "s3cret!"}, follow_redirects=True)
    assert ok.status_code == 200
    assert "secret" in ok.get_data(as_text=True)


def test_csp_header_present(client):
    r = client.get("/")
    assert "Content-Security-Policy" in r.headers
