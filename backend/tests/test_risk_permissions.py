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
# 确保所有模型都注册到 Base.metadata
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.core.security import create_access_token


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


def _make_client(db_session, current_user):
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


def _make_user(db_session, feishu_id, role=UserRole.MEMBER):
    user = User(feishu_user_id=feishu_id, name=feishu_id, role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_project_with_risk(db_session, project_owner, risk_owner_id):
    project = Project(name="权限项目", record_date=date(2026, 5, 30), owner_id=project_owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    risk = Risk(project_id=project.id, title="权限风险", owner_id=risk_owner_id)
    db_session.add(risk)
    db_session.commit()
    db_session.refresh(risk)
    return project, risk


def test_risk_owner_can_update_own_risk(db_session):
    """风险负责人可以更新自己负责的风险"""
    owner = _make_user(db_session, "p_owner")
    risk_owner = _make_user(db_session, "r_owner")
    _, risk = _make_project_with_risk(db_session, owner, risk_owner.id)

    token = create_access_token({"sub": str(risk_owner.id)})
    client = _make_client(db_session, risk_owner)
    try:
        response = client.put(
            f"/api/v1/risks/{risk.id}",
            json={"title": "改标题"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "改标题"
    finally:
        _cleanup()


def test_project_owner_can_update_risk(db_session):
    """所属项目所有者可以更新项目内的风险"""
    owner = _make_user(db_session, "p_owner2")
    risk_owner = _make_user(db_session, "r_owner2")
    _, risk = _make_project_with_risk(db_session, owner, risk_owner.id)

    token = create_access_token({"sub": str(owner.id)})
    client = _make_client(db_session, owner)
    try:
        response = client.put(
            f"/api/v1/risks/{risk.id}",
            json={"title": "项目主改"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
    finally:
        _cleanup()


def test_other_user_cannot_update_risk(db_session):
    """无关用户不能更新风险，返回 403"""
    owner = _make_user(db_session, "p_owner3")
    risk_owner = _make_user(db_session, "r_owner3")
    other = _make_user(db_session, "other3")
    _, risk = _make_project_with_risk(db_session, owner, risk_owner.id)

    token = create_access_token({"sub": str(other.id)})
    client = _make_client(db_session, other)
    try:
        response = client.put(
            f"/api/v1/risks/{risk.id}",
            json={"title": "越权"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
    finally:
        _cleanup()


def test_other_user_cannot_delete_unowned_risk(db_session):
    """无关用户不能删除无负责人的风险，返回 403"""
    owner = _make_user(db_session, "p_owner4")
    other = _make_user(db_session, "other4")
    # 风险无负责人 (owner_id=None)
    _, risk = _make_project_with_risk(db_session, owner, None)

    token = create_access_token({"sub": str(other.id)})
    client = _make_client(db_session, other)
    try:
        response = client.delete(
            f"/api/v1/risks/{risk.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
    finally:
        _cleanup()


def test_admin_can_delete_any_risk(db_session):
    """管理员可以删除任何风险"""
    owner = _make_user(db_session, "p_owner5")
    risk_owner = _make_user(db_session, "r_owner5")
    admin = _make_user(db_session, "admin5", role=UserRole.ADMIN)
    _, risk = _make_project_with_risk(db_session, owner, risk_owner.id)

    token = create_access_token({"sub": str(admin.id)})
    client = _make_client(db_session, admin)
    try:
        response = client.delete(
            f"/api/v1/risks/{risk.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204
    finally:
        _cleanup()


def test_update_nonexistent_risk_returns_404(db_session):
    """无权用户对不存在的风险执行 PUT 应返回 404 而不是 403"""
    other = _make_user(db_session, "other6")
    token = create_access_token({"sub": str(other.id)})
    client = _make_client(db_session, other)
    try:
        response = client.put(
            "/api/v1/risks/999999",
            json={"title": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
    finally:
        _cleanup()
