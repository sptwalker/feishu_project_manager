import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.config import get_settings
from backend.utils import feishu_crypto


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def set_token():
    s = get_settings()
    old = s.FEISHU_VERIFICATION_TOKEN
    s.FEISHU_VERIFICATION_TOKEN = "vtok"
    yield
    s.FEISHU_VERIFICATION_TOKEN = old


def test_url_verification_returns_challenge(client, set_token):
    r = client.post(
        "/api/v1/feishu/webhook",
        json={"type": "url_verification", "challenge": "abc123", "token": "vtok"},
    )
    assert r.status_code == 200
    assert r.json()["challenge"] == "abc123"


def test_url_verification_bad_token(client, set_token):
    r = client.post(
        "/api/v1/feishu/webhook",
        json={"type": "url_verification", "challenge": "abc", "token": "WRONG"},
    )
    assert r.status_code == 403


def test_event_callback_dispatched(client, set_token):
    r = client.post(
        "/api/v1/feishu/webhook",
        json={"header": {"event_type": "im.message.receive_v1", "token": "vtok"}, "event": {}},
    )
    assert r.status_code == 200
    assert r.json()["code"] == 0


def test_event_callback_bad_token(client, set_token):
    r = client.post(
        "/api/v1/feishu/webhook",
        json={"header": {"event_type": "x", "token": "nope"}, "event": {}},
    )
    assert r.status_code == 403


def test_encrypted_url_verification(client):
    s = get_settings()
    old_key, old_tok = s.FEISHU_ENCRYPT_KEY, s.FEISHU_VERIFICATION_TOKEN
    s.FEISHU_ENCRYPT_KEY = "ekey-secret"
    s.FEISHU_VERIFICATION_TOKEN = ""
    try:
        payload = {"type": "url_verification", "challenge": "ch-xyz"}
        enc = feishu_crypto.encrypt("ekey-secret", json.dumps(payload))
        r = client.post("/api/v1/feishu/webhook", json={"encrypt": enc})
        assert r.status_code == 200
        assert r.json()["challenge"] == "ch-xyz"
    finally:
        s.FEISHU_ENCRYPT_KEY = old_key
        s.FEISHU_VERIFICATION_TOKEN = old_tok


def test_encrypted_event_without_key_configured(client):
    s = get_settings()
    old_key = s.FEISHU_ENCRYPT_KEY
    s.FEISHU_ENCRYPT_KEY = ""
    try:
        r = client.post("/api/v1/feishu/webhook", json={"encrypt": "anything"})
        assert r.status_code == 400
    finally:
        s.FEISHU_ENCRYPT_KEY = old_key
