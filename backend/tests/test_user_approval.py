"""新用户准入审批：登录置 pending、访问闸拦截、管理员审批、初始管理员兜底。"""
import asyncio
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from fastapi import HTTPException

from backend.main import app
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_admin, get_current_user
from backend.core.config import get_settings
from backend.models.user import User, UserRole, UserStatus
from backend.services.user_service import UserService
from backend.schemas.user import UserCreate


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def _mk(db, fid, role=UserRole.MEMBER, status=UserStatus.ACTIVE):
    return UserService.create(
        db, UserCreate(feishu_user_id=fid, name=fid), role=role, status=status)


# ---------- UserService ----------

def test_create_default_active(db_session):
    u = _mk(db_session, "u1")
    assert u.status == UserStatus.ACTIVE


def test_create_pending(db_session):
    u = _mk(db_session, "u2", status=UserStatus.PENDING)
    assert u.status == UserStatus.PENDING


def test_set_status(db_session):
    u = _mk(db_session, "u3", status=UserStatus.PENDING)
    u2 = UserService.set_status(db_session, u.id, UserStatus.ACTIVE)
    assert u2.status == UserStatus.ACTIVE


# ---------- 访问闸 get_current_user ----------

def _call_gate(db, user):
    """直接以已知 user 触发 get_current_user 的 status 逻辑：构造合法 token。"""
    from backend.core.security import create_access_token
    from fastapi.security import HTTPAuthorizationCredentials
    cred = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=create_access_token(data={"sub": str(user.id)}))
    return asyncio.run(get_current_user(credentials=cred, db=db))


def test_gate_active_passes(db_session):
    u = _mk(db_session, "ua", status=UserStatus.ACTIVE)
    assert _call_gate(db_session, u).id == u.id


def test_gate_pending_blocked(db_session):
    u = _mk(db_session, "up", status=UserStatus.PENDING)
    with pytest.raises(HTTPException) as e:
        _call_gate(db_session, u)
    assert e.value.status_code == 403
    assert e.value.detail == "account_pending"


def test_gate_disabled_blocked(db_session):
    u = _mk(db_session, "ud", status=UserStatus.DISABLED)
    with pytest.raises(HTTPException) as e:
        _call_gate(db_session, u)
    assert e.value.detail == "account_disabled"


def test_gate_initial_admin_rescued(db_session, monkeypatch):
    """初始管理员即便被置 pending，访问闸也兜底纠正为 active 放行。"""
    s = get_settings()
    monkeypatch.setattr(s, "INITIAL_ADMIN_FEISHU_IDS", ["ou_boss"])
    u = _mk(db_session, "ou_boss", role=UserRole.ADMIN, status=UserStatus.PENDING)
    out = _call_gate(db_session, u)
    assert out.status == UserStatus.ACTIVE


# ---------- PATCH /users/{id}/status ----------

@pytest.fixture
def client(db_session):
    admin = _mk(db_session, "admin", role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        with TestClient(app) as c:
            c._admin = admin  # type: ignore
            yield c
    finally:
        app.dependency_overrides.clear()


def test_admin_approves_user(client, db_session):
    target = _mk(db_session, "newbie", status=UserStatus.PENDING)
    r = client.patch(f"/api/v1/users/{target.id}/status", json={"status": "active"})
    assert r.status_code == 200
    assert r.json()["status"] == "active"


def test_admin_cannot_lock_self(client):
    admin = client._admin  # type: ignore
    r = client.patch(f"/api/v1/users/{admin.id}/status", json={"status": "disabled"})
    assert r.status_code == 400


def test_status_requires_admin(db_session):
    """非管理员调用 → 403（get_current_admin 守卫）。"""
    member = _mk(db_session, "m", role=UserRole.MEMBER, status=UserStatus.ACTIVE)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: member
    try:
        with TestClient(app) as c:
            r = c.patch(f"/api/v1/users/{member.id}/status", json={"status": "disabled"})
        assert r.status_code == 403
    finally:
        app.dependency_overrides.clear()
