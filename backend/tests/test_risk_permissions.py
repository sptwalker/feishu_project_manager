"""风险权限测试（基于角色）：ADMIN/PROJECT_MANAGER 可改，MEMBER/OBSERVER 只读。"""
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.models.user import User, UserRole
from backend.models.project import Project
from backend.models.risk import Risk
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


def _make_project_with_risk(db):
    project = Project(name="权限项目", record_date=date(2026, 5, 30), owner_name="负责人")
    db.add(project)
    db.commit()
    db.refresh(project)
    risk = Risk(project_id=project.id, title="权限风险", owner_name="负责人")
    db.add(risk)
    db.commit()
    db.refresh(risk)
    return project, risk


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
def test_manager_roles_can_update_risk(db_session, role):
    user = _make_user(db_session, f"mgr_{role.value}", role=role)
    _, risk = _make_project_with_risk(db_session)
    client = _client(db_session, user)
    try:
        r = client.put(f"/api/v1/risks/{risk.id}", json={"title": "改标题"})
        assert r.status_code == 200
    finally:
        _cleanup()


@pytest.mark.parametrize("role", [UserRole.MEMBER, UserRole.OBSERVER])
def test_non_manager_roles_cannot_update_risk(db_session, role):
    user = _make_user(db_session, f"u_{role.value}", role=role)
    _, risk = _make_project_with_risk(db_session)
    client = _client(db_session, user)
    try:
        r = client.put(f"/api/v1/risks/{risk.id}", json={"title": "越权"})
        assert r.status_code == 403
    finally:
        _cleanup()


def test_member_cannot_delete_risk(db_session):
    member = _make_user(db_session, "member", role=UserRole.MEMBER)
    _, risk = _make_project_with_risk(db_session)
    client = _client(db_session, member)
    try:
        r = client.delete(f"/api/v1/risks/{risk.id}")
        assert r.status_code == 403
    finally:
        _cleanup()


def test_admin_can_delete_risk(db_session):
    admin = _make_user(db_session, "admin", role=UserRole.ADMIN)
    _, risk = _make_project_with_risk(db_session)
    client = _client(db_session, admin)
    try:
        r = client.delete(f"/api/v1/risks/{risk.id}")
        assert r.status_code == 204
    finally:
        _cleanup()


def test_member_cannot_create_risk(db_session):
    member = _make_user(db_session, "member", role=UserRole.MEMBER)
    project, _ = _make_project_with_risk(db_session)
    client = _client(db_session, member)
    try:
        r = client.post(f"/api/v1/projects/{project.id}/risks", json={"title": "新风险"})
        assert r.status_code == 403
    finally:
        _cleanup()


def test_update_nonexistent_risk_404(db_session):
    admin = _make_user(db_session, "admin", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        r = client.put("/api/v1/risks/99999", json={"title": "x"})
        assert r.status_code == 404
    finally:
        _cleanup()
