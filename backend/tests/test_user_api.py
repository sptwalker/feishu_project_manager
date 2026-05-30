import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.models.user import User, UserRole
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user


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


def _make_user(db, feishu_id, role=UserRole.MEMBER, name=None):
    u = User(feishu_user_id=feishu_id, name=name or feishu_id, role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _client(db_session, current_user):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_user():
        return current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


def _cleanup():
    app.dependency_overrides.clear()


def test_get_me(db_session):
    user = _make_user(db_session, "me_user", name="我自己")
    client = _client(db_session, user)
    try:
        r = client.get("/api/v1/users/me")
        assert r.status_code == 200
        assert r.json()["feishu_user_id"] == "me_user"
        assert r.json()["name"] == "我自己"
    finally:
        _cleanup()


def test_list_users(db_session):
    u1 = _make_user(db_session, "u1")
    _make_user(db_session, "u2")
    _make_user(db_session, "admin1", role=UserRole.ADMIN)
    client = _client(db_session, u1)
    try:
        r = client.get("/api/v1/users")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 3
    finally:
        _cleanup()


def test_list_users_filter_role(db_session):
    u1 = _make_user(db_session, "u1")
    _make_user(db_session, "admin1", role=UserRole.ADMIN)
    client = _client(db_session, u1)
    try:
        r = client.get("/api/v1/users?role=admin")
        assert r.status_code == 200
        data = r.json()
        assert all(u["role"] == "admin" for u in data)
        assert len(data) == 1
    finally:
        _cleanup()


def test_admin_can_update_role(db_session):
    admin = _make_user(db_session, "admin1", role=UserRole.ADMIN)
    target = _make_user(db_session, "target")
    client = _client(db_session, admin)
    try:
        r = client.patch(f"/api/v1/users/{target.id}/role", json={"role": "project_manager"})
        assert r.status_code == 200
        assert r.json()["role"] == "project_manager"
    finally:
        _cleanup()


def test_non_admin_cannot_update_role(db_session):
    member = _make_user(db_session, "member1", role=UserRole.MEMBER)
    target = _make_user(db_session, "target")
    client = _client(db_session, member)
    try:
        r = client.patch(f"/api/v1/users/{target.id}/role", json={"role": "admin"})
        assert r.status_code == 403
    finally:
        _cleanup()


def test_update_role_user_not_found(db_session):
    admin = _make_user(db_session, "admin1", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        r = client.patch("/api/v1/users/99999/role", json={"role": "member"})
        assert r.status_code == 404
    finally:
        _cleanup()


def test_update_role_invalid_value(db_session):
    admin = _make_user(db_session, "admin1", role=UserRole.ADMIN)
    target = _make_user(db_session, "target")
    client = _client(db_session, admin)
    try:
        r = client.patch(f"/api/v1/users/{target.id}/role", json={"role": "superuser"})
        assert r.status_code == 422
    finally:
        _cleanup()
