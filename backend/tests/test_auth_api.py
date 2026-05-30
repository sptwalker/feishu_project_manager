import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.config import get_settings
from backend.services.auth_service import AuthenticationError
from backend.api.v1 import auth as auth_module


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # 不自动跟随重定向，以便断言 Location
    with TestClient(app, follow_redirects=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_callback_success_redirects_to_frontend_with_tokens(client, monkeypatch):
    mock = AsyncMock(return_value={
        "access_token": "acc123",
        "refresh_token": "ref456",
        "token_type": "bearer",
    })
    monkeypatch.setattr(auth_module.AuthService, "feishu_login", mock)

    r = client.get("/api/v1/auth/feishu/callback?code=valid_code")
    assert r.status_code in (302, 307)
    loc = r.headers["location"]
    frontend = get_settings().FRONTEND_URL.rstrip("/")
    assert loc.startswith(f"{frontend}/auth/callback?")
    assert "access_token=acc123" in loc
    assert "refresh_token=ref456" in loc


def test_callback_auth_failure_redirects_to_login(client, monkeypatch):
    mock = AsyncMock(side_effect=AuthenticationError("bad code"))
    monkeypatch.setattr(auth_module.AuthService, "feishu_login", mock)

    r = client.get("/api/v1/auth/feishu/callback?code=bad")
    assert r.status_code in (302, 307)
    loc = r.headers["location"]
    frontend = get_settings().FRONTEND_URL.rstrip("/")
    assert loc.startswith(f"{frontend}/login?")
    assert "error=authentication_failed" in loc


def test_callback_unexpected_error_redirects_to_login(client, monkeypatch):
    mock = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(auth_module.AuthService, "feishu_login", mock)

    r = client.get("/api/v1/auth/feishu/callback?code=x")
    assert r.status_code in (302, 307)
    loc = r.headers["location"]
    assert "error=server_error" in loc


def test_callback_missing_code_returns_422(client):
    r = client.get("/api/v1/auth/feishu/callback")
    assert r.status_code == 422


def test_feishu_login_redirects_to_feishu(client):
    r = client.get("/api/v1/auth/feishu/login")
    assert r.status_code in (302, 307)
    assert "open.feishu.cn" in r.headers["location"]
