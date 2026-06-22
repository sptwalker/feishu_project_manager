"""结束周会的主控权限：仅主控端可结束（无主控时任意管理员可清理）。"""
import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.main import app
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.models.user import User, UserRole
from backend.models.meeting_record import MeetingRecord
from backend.services.settings_service import SettingsService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    try:
        yield db
    finally:
        db.close()


def _admin(db, fid="admin"):
    u = User(feishu_user_id=fid, name=fid, role=UserRole.ADMIN)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _active_meeting(db, controller=None):
    rec = MeetingRecord(session=5, meeting_date=date(2026, 6, 22), status="active",
                        content_snapshot=[], controller_client_id=controller)
    db.add(rec)
    SettingsService.set_active(db, True)
    db.commit()
    return rec


def _client(db_session, user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_controller_can_close(db_session):
    _active_meeting(db_session, controller="ctrlA")
    c = _client(db_session, _admin(db_session))
    r = c.post("/api/v1/meeting-records/close", json={"client_id": "ctrlA"})
    assert r.status_code == 200
    assert r.json()["active"] is False
    assert db_session.query(MeetingRecord).filter(MeetingRecord.status == "active").count() == 0


def test_non_controller_cannot_close(db_session):
    _active_meeting(db_session, controller="ctrlA")
    c = _client(db_session, _admin(db_session))
    r = c.post("/api/v1/meeting-records/close", json={"client_id": "otherB"})
    assert r.status_code == 403
    # 会议仍在进行（未被结束）
    assert db_session.query(MeetingRecord).filter(MeetingRecord.status == "active").count() == 1


def test_missing_client_id_blocked_when_controller_present(db_session):
    _active_meeting(db_session, controller="ctrlA")
    c = _client(db_session, _admin(db_session))
    r = c.post("/api/v1/meeting-records/close", json={})
    assert r.status_code == 403


def test_any_admin_can_close_when_no_controller(db_session):
    """无主控（已释放/从未认领）→ 任意管理员可结束（清理兜底）。"""
    _active_meeting(db_session, controller=None)
    c = _client(db_session, _admin(db_session))
    r = c.post("/api/v1/meeting-records/close", json={"client_id": "anyone"})
    assert r.status_code == 200
    assert r.json()["active"] is False
