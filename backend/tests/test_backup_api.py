from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.user import User, UserRole
from backend.models.department import Department
from backend.models.project import Project, ProjectStatus, ProjectUrgency
from backend.models import (  # noqa: F401 确保所有表注册
    User as _U, Project as _P, Task as _T, Event as _E, Risk as _R,
    Department as _D, SystemSetting as _S,
)
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.services.backup_service import BackupService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", echo=False,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed(db):
    db.add(User(feishu_user_id="u1", name="刘丹", role=UserRole.ADMIN, name_en="Liu Dan", position="经理"))
    db.add(Department(name="产品部", short_name="产品", color="rgb(1,2,3)"))
    db.add(Project(
        name="项目A", record_date=date(2026, 6, 1), status=ProjectStatus.IN_PROGRESS,
        urgency=ProjectUrgency.URGENT, department="产品部", owner_name="刘丹",
        completion=40, is_long_term=False,
        progress_log=[{"time": "2026-06-01 10:00", "content": "讨论", "status": "待讨论", "id": "x1"}],
    ))
    db.commit()


def _make_user(db, fid, role=UserRole.MEMBER):
    u = User(feishu_user_id=fid, name=fid, role=role)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _client(db_session, current_user):
    def override_get_db():
        yield db_session

    def override_get_current_user():
        return current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


def _cleanup():
    app.dependency_overrides.clear()


# ---------- service 往返 ----------

def test_export_structure(db_session):
    _seed(db_session)
    snap = BackupService.export_all(db_session)
    assert snap["version"] == 1
    assert set(snap["tables"]) >= {"users", "departments", "projects", "tasks", "risks", "events", "system_settings"}
    assert len(snap["tables"]["projects"]) == 1
    assert snap["tables"]["projects"][0]["status"] == "in_progress"
    assert snap["tables"]["projects"][0]["is_long_term"] is False


def test_round_trip_replaces_all(db_session):
    _seed(db_session)
    snap = BackupService.export_all(db_session)
    # 清掉原数据 + 加一条多余的，导入后应被全量替换
    db_session.add(Project(name="多余", record_date=date(2026, 6, 2)))
    db_session.commit()
    assert db_session.query(Project).count() == 2

    counts = BackupService.import_all(db_session, snap)
    assert counts["projects"] == 1
    assert db_session.query(Project).count() == 1
    p = db_session.query(Project).first()
    assert p.name == "项目A"
    assert p.status == ProjectStatus.IN_PROGRESS
    assert p.record_date == date(2026, 6, 1)
    assert p.progress_log[0]["id"] == "x1"
    assert db_session.query(User).first().name_en == "Liu Dan"


def test_import_bad_version_rolls_back(db_session):
    _seed(db_session)
    before = db_session.query(Project).count()
    with pytest.raises(ValueError):
        BackupService.import_all(db_session, {"version": 999, "tables": {}})
    assert db_session.query(Project).count() == before


def test_import_missing_table_raises(db_session):
    _seed(db_session)
    with pytest.raises(ValueError):
        BackupService.import_all(db_session, {"version": 1, "tables": {"users": []}})


# ---------- API 权限 ----------

def test_export_admin_ok(db_session):
    admin = _make_user(db_session, "admin1", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        r = client.get("/api/v1/backup/export")
        assert r.status_code == 200
        assert "attachment" in r.headers.get("content-disposition", "")
        assert "tables" in r.json()
    finally:
        _cleanup()


def test_export_non_admin_403(db_session):
    member = _make_user(db_session, "m1")
    client = _client(db_session, member)
    try:
        r = client.get("/api/v1/backup/export")
        assert r.status_code == 403
    finally:
        _cleanup()


def test_import_non_admin_403(db_session):
    member = _make_user(db_session, "m1")
    client = _client(db_session, member)
    try:
        r = client.post("/api/v1/backup/import", files={"file": ("b.json", b"{}", "application/json")})
        assert r.status_code == 403
    finally:
        _cleanup()


def test_import_bad_json_400(db_session):
    admin = _make_user(db_session, "admin1", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        r = client.post("/api/v1/backup/import", files={"file": ("b.json", b"not json", "application/json")})
        assert r.status_code == 400
    finally:
        _cleanup()
