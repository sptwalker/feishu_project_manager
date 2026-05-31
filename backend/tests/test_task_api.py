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
    user = User(feishu_user_id="task_api_user", name="任务API用户", role=UserRole.ADMIN)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_project(db_session, test_user):
    proj = Project(name="任务API项目", record_date=date(2026, 5, 30), owner_name="负责人")
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


def _create_task(client, auth_headers, project_id, owner_id, name="任务X", **extra):
    payload = {"name": name, "owner_id": owner_id, **extra}
    response = client.post(
        f"/api/v1/projects/{project_id}/tasks", json=payload, headers=auth_headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_task_api(client, auth_headers, test_project, test_user):
    """创建任务 API"""
    response = client.post(
        f"/api/v1/projects/{test_project.id}/tasks",
        json={"name": "API任务", "owner_name": "负责人"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API任务"
    assert data["project_id"] == test_project.id
    assert "id" in data


def test_create_task_project_not_found(client, auth_headers, test_user):
    """在不存在的项目下创建任务返回 404"""
    response = client.post(
        "/api/v1/projects/99999/tasks",
        json={"name": "孤儿任务", "owner_name": "负责人"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_task_invalid_parent(client, auth_headers, test_project, test_user):
    """parent_task_id 无效返回 400"""
    response = client.post(
        f"/api/v1/projects/{test_project.id}/tasks",
        json={"name": "任务", "owner_name": "负责人", "parent_task_id": 99999},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_list_tasks_api(client, auth_headers, test_project, test_user):
    """获取任务列表 API"""
    _create_task(client, auth_headers, test_project.id, test_user.id, name="L1")
    response = client.get(
        f"/api/v1/projects/{test_project.id}/tasks", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(t["name"] == "L1" for t in data)


def test_list_tasks_filter_status(client, auth_headers, test_project, test_user):
    """按状态过滤任务列表"""
    _create_task(client, auth_headers, test_project.id, test_user.id, name="进行", status="in_progress")
    _create_task(client, auth_headers, test_project.id, test_user.id, name="完成", status="completed")

    response = client.get(
        f"/api/v1/projects/{test_project.id}/tasks?status=completed", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert all(t["status"] == "completed" for t in data)


def test_list_tasks_pagination(client, auth_headers, test_project, test_user):
    """任务列表分页"""
    for i in range(5):
        _create_task(client, auth_headers, test_project.id, test_user.id, name=f"P{i}")

    first = client.get(
        f"/api/v1/projects/{test_project.id}/tasks?skip=0&limit=2", headers=auth_headers
    ).json()
    second = client.get(
        f"/api/v1/projects/{test_project.id}/tasks?skip=2&limit=2", headers=auth_headers
    ).json()
    assert len(first) == 2
    assert len(second) == 2
    assert {t["id"] for t in first}.isdisjoint({t["id"] for t in second})


def test_get_task_by_id(client, auth_headers, test_project, test_user):
    """获取单个任务"""
    task = _create_task(client, auth_headers, test_project.id, test_user.id, name="单个")
    response = client.get(f"/api/v1/tasks/{task['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "单个"


def test_get_task_by_id_404(client, auth_headers):
    """获取不存在的任务返回 404"""
    response = client.get("/api/v1/tasks/99999", headers=auth_headers)
    assert response.status_code == 404


def test_create_subtask_api(client, auth_headers, test_project, test_user):
    """创建子任务 API，继承父任务项目"""
    parent = _create_task(client, auth_headers, test_project.id, test_user.id, name="父")
    response = client.post(
        f"/api/v1/tasks/{parent['id']}/subtasks",
        json={"name": "子", "owner_name": "负责人"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["parent_task_id"] == parent["id"]
    assert data["project_id"] == test_project.id


def test_get_subtasks_api(client, auth_headers, test_project, test_user):
    """获取子任务列表 API"""
    parent = _create_task(client, auth_headers, test_project.id, test_user.id, name="父2")
    client.post(
        f"/api/v1/tasks/{parent['id']}/subtasks",
        json={"name": "子A", "owner_name": "负责人"},
        headers=auth_headers,
    )
    response = client.get(f"/api/v1/tasks/{parent['id']}/subtasks", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "子A"


def test_update_task_api(client, auth_headers, test_project, test_user):
    """更新任务 API"""
    task = _create_task(client, auth_headers, test_project.id, test_user.id, name="待改")
    response = client.put(
        f"/api/v1/tasks/{task['id']}",
        json={"name": "已改", "completion": 70},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "已改"
    assert data["completion"] == 70


def test_update_task_404(client, auth_headers):
    """更新不存在的任务返回 404"""
    response = client.put(
        "/api/v1/tasks/99999", json={"name": "x"}, headers=auth_headers
    )
    assert response.status_code == 404


def test_delete_task_api(client, auth_headers, test_project, test_user):
    """删除任务 API 返回 204，后续 GET 返回 404"""
    task = _create_task(client, auth_headers, test_project.id, test_user.id, name="待删")
    response = client.delete(f"/api/v1/tasks/{task['id']}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get(f"/api/v1/tasks/{task['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_delete_task_404(client, auth_headers):
    """删除不存在的任务返回 404"""
    response = client.delete("/api/v1/tasks/99999", headers=auth_headers)
    assert response.status_code == 404
