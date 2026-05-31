import io
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.models.user import User, UserRole
from backend.models.project import Project
from backend.models.task import Task
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.utils.excel import build_xlsx, parse_xlsx

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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
    u = User(feishu_user_id="report_user", name="报表用户", role=UserRole.ADMIN)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def test_project(db_session, test_user):
    p = Project(name="报表项目", record_date=date(2026, 5, 30), owner_name="负责人")
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


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
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_dashboard_api(client, test_project):
    r = client.get("/api/v1/statistics/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert "projects" in data and "tasks" in data and "risks" in data
    assert data["projects"]["total"] == 1


def test_project_progress_api(client, test_project):
    r = client.get(f"/api/v1/statistics/projects/{test_project.id}/progress")
    assert r.status_code == 200
    assert r.json()["project_id"] == test_project.id


def test_project_progress_api_404(client):
    r = client.get("/api/v1/statistics/projects/99999/progress")
    assert r.status_code == 404


def test_export_projects_api(client, test_project):
    r = client.get("/api/v1/reports/projects/export")
    assert r.status_code == 200
    assert r.headers["content-type"] == XLSX_MEDIA_TYPE
    assert "attachment" in r.headers["content-disposition"]
    parsed = parse_xlsx(r.content)
    assert any(row["项目名称"] == "报表项目" for row in parsed)


def test_export_tasks_api(client, test_project, db_session, test_user):
    db_session.add(Task(project_id=test_project.id, name="导出任务", owner_name="负责人"))
    db_session.commit()
    r = client.get(f"/api/v1/reports/projects/{test_project.id}/tasks/export")
    assert r.status_code == 200
    parsed = parse_xlsx(r.content)
    assert any(row["任务名称"] == "导出任务" for row in parsed)


def test_export_tasks_api_project_404(client):
    r = client.get("/api/v1/reports/projects/99999/tasks/export")
    assert r.status_code == 404


def test_import_tasks_api(client, test_project, test_user):
    data = build_xlsx(
        ["任务名称", "负责人", "状态"],
        [["上传任务1", test_user.id, "pending"], ["上传任务2", test_user.id, "in_progress"]],
    )
    files = {"file": ("tasks.xlsx", io.BytesIO(data), XLSX_MEDIA_TYPE)}
    r = client.post(f"/api/v1/reports/projects/{test_project.id}/tasks/import", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["created"] == 2
    assert body["error_count"] == 0


def test_import_tasks_api_bad_file(client, test_project):
    files = {"file": ("bad.xlsx", io.BytesIO(b"not xlsx"), XLSX_MEDIA_TYPE)}
    r = client.post(f"/api/v1/reports/projects/{test_project.id}/tasks/import", files=files)
    assert r.status_code == 400


def test_import_tasks_api_project_404(client, test_user):
    data = build_xlsx(["任务名称", "负责人"], [["t", test_user.id]])
    files = {"file": ("tasks.xlsx", io.BytesIO(data), XLSX_MEDIA_TYPE)}
    r = client.post("/api/v1/reports/projects/99999/tasks/import", files=files)
    assert r.status_code == 404
