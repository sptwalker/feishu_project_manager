import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.models.user import User, UserRole
from backend.models.project import Project
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


@pytest.fixture
def test_user(db_session):
    user = User(feishu_user_id="risk_api_user", name="风险API用户", role=UserRole.ADMIN)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_project(db_session, test_user):
    proj = Project(name="风险API项目", record_date=date(2026, 5, 30), owner_name="负责人")
    db_session.add(proj)
    db_session.commit()
    db_session.refresh(proj)
    return proj


@pytest.fixture
def client(db_session, test_user):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


def _create_risk(client, auth_headers, project_id, title="风险X", **extra):
    payload = {"title": title, **extra}
    response = client.post(
        f"/api/v1/projects/{project_id}/risks", json=payload, headers=auth_headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_risk_api(client, auth_headers, test_project):
    """创建风险 API"""
    response = client.post(
        f"/api/v1/projects/{test_project.id}/risks",
        json={"title": "API风险"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "API风险"
    assert data["project_id"] == test_project.id
    assert "id" in data


def test_create_risk_project_not_found(client, auth_headers):
    """在不存在的项目下创建风险返回 404"""
    response = client.post(
        "/api/v1/projects/99999/risks",
        json={"title": "孤儿风险"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_risks_api(client, auth_headers, test_project):
    """获取风险列表 API"""
    _create_risk(client, auth_headers, test_project.id, title="L1")
    response = client.get(
        f"/api/v1/projects/{test_project.id}/risks", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(r["title"] == "L1" for r in data)


def test_list_risks_filter_status(client, auth_headers, test_project):
    """按状态过滤风险列表"""
    _create_risk(client, auth_headers, test_project.id, title="开启", status="open")
    _create_risk(client, auth_headers, test_project.id, title="解决", status="resolved")

    response = client.get(
        f"/api/v1/projects/{test_project.id}/risks?status=resolved", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert all(r["status"] == "resolved" for r in data)


def test_list_risks_pagination(client, auth_headers, test_project):
    """风险列表分页"""
    for i in range(5):
        _create_risk(client, auth_headers, test_project.id, title=f"P{i}")

    first = client.get(
        f"/api/v1/projects/{test_project.id}/risks?skip=0&limit=2", headers=auth_headers
    ).json()
    second = client.get(
        f"/api/v1/projects/{test_project.id}/risks?skip=2&limit=2", headers=auth_headers
    ).json()
    assert len(first) == 2
    assert len(second) == 2
    assert {r["id"] for r in first}.isdisjoint({r["id"] for r in second})


def test_get_risk_by_id(client, auth_headers, test_project):
    """获取单个风险"""
    risk = _create_risk(client, auth_headers, test_project.id, title="单个")
    response = client.get(f"/api/v1/risks/{risk['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["title"] == "单个"


def test_get_risk_by_id_404(client, auth_headers):
    """获取不存在的风险返回 404"""
    response = client.get("/api/v1/risks/99999", headers=auth_headers)
    assert response.status_code == 404


def test_update_risk_api(client, auth_headers, test_project):
    """更新风险 API"""
    risk = _create_risk(client, auth_headers, test_project.id, title="待改")
    response = client.put(
        f"/api/v1/risks/{risk['id']}",
        json={"title": "已改", "status": "monitoring"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "已改"
    assert data["status"] == "monitoring"


def test_update_risk_404(client, auth_headers):
    """更新不存在的风险返回 404"""
    response = client.put(
        "/api/v1/risks/99999", json={"title": "x"}, headers=auth_headers
    )
    assert response.status_code == 404


def test_delete_risk_api(client, auth_headers, test_project):
    """删除风险 API 返回 204，后续 GET 返回 404"""
    risk = _create_risk(client, auth_headers, test_project.id, title="待删")
    response = client.delete(f"/api/v1/risks/{risk['id']}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get(f"/api/v1/risks/{risk['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_delete_risk_404(client, auth_headers):
    """删除不存在的风险返回 404"""
    response = client.delete("/api/v1/risks/99999", headers=auth_headers)
    assert response.status_code == 404
