import pytest
from fastapi.testclient import TestClient
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.models.user import User, UserRole
from backend.models.project import Project, ProjectStatus
# 确保所有模型都注册到 Base.metadata
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.core.security import create_access_token

@pytest.fixture
def db_session():
    """数据库会话 fixture"""
    # 使用内存数据库进行测试，StaticPool 确保所有线程共享同一连接
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
    """创建测试用户"""
    user = User(
        feishu_user_id="test_api_user",
        name="API测试用户",
        role=UserRole.ADMIN
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def client(db_session, test_user):
    """测试客户端 fixture"""
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
    """获取认证 token"""
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}

def test_create_project_api(client, auth_headers, test_user):
    """测试创建项目 API"""
    response = client.post(
        "/api/v1/projects/",
        json={
            "name": "API测试项目",
            "record_date": "2026-05-30",
            "content": "通过API创建",
            "owner_name": "负责人"
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API测试项目"
    assert "id" in data

def test_get_project_list_api(client, auth_headers):
    """测试获取项目列表 API"""
    response = client.get("/api/v1/projects/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def _create_project(client, auth_headers, test_user, name="项目X", status_value=None):
    payload = {
        "name": name,
        "record_date": "2026-05-30",
        "content": "测试内容",
        "owner_name": "负责人",
    }
    if status_value is not None:
        payload["status"] = status_value
    response = client.post("/api/v1/projects/", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()

def test_get_project_by_id_404(client, auth_headers):
    """GET /{id} 不存在时返回 404"""
    response = client.get("/api/v1/projects/99999", headers=auth_headers)
    assert response.status_code == 404

def test_update_project_404(client, auth_headers):
    """PUT /{id} 不存在时返回 404"""
    response = client.put(
        "/api/v1/projects/99999",
        json={"name": "新名称"},
        headers=auth_headers,
    )
    assert response.status_code == 404

def test_delete_project_204(client, auth_headers, test_user):
    """DELETE /{id} 删除成功返回 204, 后续 GET 返回 404"""
    project = _create_project(client, auth_headers, test_user, name="待删除项目")
    project_id = project["id"]

    response = client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert response.status_code == 404

def test_delete_project_404(client, auth_headers):
    """DELETE /{id} 不存在时返回 404"""
    response = client.delete("/api/v1/projects/99999", headers=auth_headers)
    assert response.status_code == 404

def test_get_projects_with_filter(client, auth_headers, test_user):
    """GET / 使用 status 过滤返回过滤后的结果"""
    _create_project(client, auth_headers, test_user, name="项目A", status_value="in_progress")
    _create_project(client, auth_headers, test_user, name="项目B", status_value="completed")

    response = client.get(
        "/api/v1/projects/?status=completed", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert all(p["status"] == "completed" for p in data)
    assert any(p["name"] == "项目B" for p in data)
    assert not any(p["name"] == "项目A" for p in data)

def test_get_projects_pagination(client, auth_headers, test_user):
    """GET / 的 skip/limit 分页参数正常工作"""
    for i in range(5):
        _create_project(client, auth_headers, test_user, name=f"分页项目{i}")

    response = client.get("/api/v1/projects/?skip=0&limit=2", headers=auth_headers)
    assert response.status_code == 200
    first_page = response.json()
    assert len(first_page) == 2

    response = client.get("/api/v1/projects/?skip=2&limit=2", headers=auth_headers)
    assert response.status_code == 200
    second_page = response.json()
    assert len(second_page) == 2

    first_ids = {p["id"] for p in first_page}
    second_ids = {p["id"] for p in second_page}
    assert first_ids.isdisjoint(second_ids)
