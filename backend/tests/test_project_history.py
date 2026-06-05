"""项目历史修改记录：端点 + 按项目过滤 + 不级联删除 测试"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from datetime import date

from backend.main import app
from backend.db.base import Base
from backend.models.user import User, UserRole
from backend.models.project import Project, ProjectStatus, ProjectUrgency
from backend.models.operation_log import OperationLog
from backend.services.operation_log_service import OperationLogService
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user, get_current_admin


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _mk_user(db, name="admin", role=UserRole.ADMIN):
    u = User(feishu_user_id=f"ou_{name}", name=name, role=role)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _mk_project(db, name="P"):
    p = Project(name=name, record_date=date(2026, 6, 1), status=ProjectStatus.IN_PROGRESS,
                urgency=ProjectUrgency.MEDIUM, completion=0, progress_log=[])
    db.add(p); db.commit(); db.refresh(p)
    return p


def _client(db, user):
    def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_admin] = lambda: user
    return TestClient(app)


def _cleanup():
    app.dependency_overrides.clear()


def test_query_filter_by_project(db_session):
    """query(project_id=) 只返回该项目的日志"""
    u = _mk_user(db_session)
    OperationLogService.log(db_session, user=u, action="edit_project", description="改了P1", project_id=1)
    OperationLogService.log(db_session, user=u, action="edit_project", description="改了P2", project_id=2)
    OperationLogService.log(db_session, user=u, action="login", description="登录")  # 无 project_id
    rows = OperationLogService.query(db_session, project_id=1)
    assert [r.description for r in rows] == ["改了P1"]


def test_history_endpoint(db_session):
    u = _mk_user(db_session)
    p = _mk_project(db_session, "甲项目")
    OperationLogService.log(db_session, user=u, action="edit_project",
                            description='修改了项目"甲项目"：完成度 0%→100%', project_id=p.id)
    client = _client(db_session, u)
    try:
        r = client.get(f"/api/v1/projects/{p.id}/history")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["project_id"] == p.id
        assert "完成度 0%→100%" in data[0]["description"]
    finally:
        _cleanup()


def test_history_404_for_missing_project(db_session):
    u = _mk_user(db_session)
    client = _client(db_session, u)
    try:
        assert client.get("/api/v1/projects/9999/history").status_code == 404
    finally:
        _cleanup()


def test_history_isolated_between_projects(db_session):
    u = _mk_user(db_session)
    p1 = _mk_project(db_session, "P1")
    p2 = _mk_project(db_session, "P2")
    OperationLogService.log(db_session, user=u, action="edit_project", description="P1改动", project_id=p1.id)
    OperationLogService.log(db_session, user=u, action="edit_project", description="P2改动", project_id=p2.id)
    client = _client(db_session, u)
    try:
        d1 = client.get(f"/api/v1/projects/{p1.id}/history").json()
        assert [x["description"] for x in d1] == ["P1改动"]
    finally:
        _cleanup()


def test_logs_survive_project_delete(db_session):
    """不级联删除：删项目后其日志仍在库（符合需求）"""
    u = _mk_user(db_session)
    p = _mk_project(db_session, "待删项目")
    pid = p.id
    OperationLogService.log(db_session, user=u, action="edit_project", description="改动", project_id=pid)
    client = _client(db_session, u)
    try:
        assert client.delete(f"/api/v1/projects/{pid}").status_code == 204
    finally:
        _cleanup()
    # 项目已删，但其日志仍保留（含删除动作日志 + 之前的编辑日志）
    remaining = OperationLogService.query(db_session, project_id=pid)
    descs = [r.description for r in remaining]
    assert "改动" in descs
    assert any("删除了项目" in d for d in descs)
