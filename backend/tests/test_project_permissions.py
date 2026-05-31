"""项目权限测试（基于角色，与项目数据解耦）

权限规则：ADMIN / PROJECT_MANAGER 可增删改；MEMBER / OBSERVER 只读。
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.models.user import User, UserRole
from backend.models.project import Project
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


def _make_user(db, feishu_id, role=UserRole.MEMBER):
    u = User(feishu_user_id=feishu_id, name=feishu_id, role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_project(db, owner_name="负责人"):
    p = Project(name="权限项目", record_date=date(2026, 5, 30), owner_name=owner_name)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _client(db_session, current_user):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


def _cleanup():
    app.dependency_overrides.clear()


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.PROJECT_MANAGER])
def test_manager_roles_can_update_project(db_session, role):
    user = _make_user(db_session, f"mgr_{role.value}", role=role)
    project = _make_project(db_session)
    client = _client(db_session, user)
    try:
        r = client.put(f"/api/v1/projects/{project.id}", json={"name": "改名"})
        assert r.status_code == 200
        assert r.json()["name"] == "改名"
    finally:
        _cleanup()


@pytest.mark.parametrize("role", [UserRole.MEMBER, UserRole.OBSERVER])
def test_non_manager_roles_cannot_update_project(db_session, role):
    user = _make_user(db_session, f"u_{role.value}", role=role)
    project = _make_project(db_session)
    client = _client(db_session, user)
    try:
        r = client.put(f"/api/v1/projects/{project.id}", json={"name": "越权"})
        assert r.status_code == 403
    finally:
        _cleanup()


def test_admin_can_create_project(db_session):
    admin = _make_user(db_session, "admin", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        r = client.post("/api/v1/projects/", json={
            "name": "新项目", "record_date": "2026-05-30",
        })
        assert r.status_code == 201
    finally:
        _cleanup()


def test_member_cannot_create_project(db_session):
    member = _make_user(db_session, "member", role=UserRole.MEMBER)
    client = _client(db_session, member)
    try:
        r = client.post("/api/v1/projects/", json={
            "name": "新项目", "record_date": "2026-05-30",
        })
        assert r.status_code == 403
    finally:
        _cleanup()


def test_member_cannot_delete_project(db_session):
    member = _make_user(db_session, "member", role=UserRole.MEMBER)
    project = _make_project(db_session)
    client = _client(db_session, member)
    try:
        r = client.delete(f"/api/v1/projects/{project.id}")
        assert r.status_code == 403
    finally:
        _cleanup()


def test_admin_can_delete_project(db_session):
    admin = _make_user(db_session, "admin", role=UserRole.ADMIN)
    project = _make_project(db_session)
    client = _client(db_session, admin)
    try:
        r = client.delete(f"/api/v1/projects/{project.id}")
        assert r.status_code == 204
    finally:
        _cleanup()


def test_update_nonexistent_project_404(db_session):
    admin = _make_user(db_session, "admin", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        r = client.put("/api/v1/projects/99999", json={"name": "x"})
        assert r.status_code == 404
    finally:
        _cleanup()
