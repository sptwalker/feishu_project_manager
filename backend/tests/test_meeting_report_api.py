"""周会汇报页相关 API 测试（起止时间 / 汇报顺序 / 计时设置）。
本项目无 conftest.py，fixture 内联。"""
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


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def _make_user(db, feishu_id, role=UserRole.MEMBER):
    user = User(feishu_user_id=feishu_id, name=feishu_id, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _client(db_session, current_user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


def _cleanup():
    app.dependency_overrides.clear()


def test_meeting_record_has_started_and_ended_columns(db_session):
    """MeetingRecord 应有 started_at / ended_at 两列，默认 None。"""
    rec = MeetingRecord(session=99, meeting_date=date(2026, 6, 6), status="active")
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)
    assert rec.started_at is None
    assert rec.ended_at is None


from backend.services.settings_service import SettingsService


def test_report_order_default_empty(db_session):
    """未设置时，汇报顺序默认空结构。"""
    order = SettingsService.get_meeting_report_order(db_session)
    assert order == {"departments": [], "members": {}}


def test_report_order_roundtrip(db_session):
    """写入后读回一致（含中文不转义）。"""
    SettingsService.set_meeting_report_order(
        db_session,
        departments=["研发部", "市场部"],
        members={"研发部": ["张三", "李四"], "市场部": ["王五"]},
    )
    order = SettingsService.get_meeting_report_order(db_session)
    assert order["departments"] == ["研发部", "市场部"]
    assert order["members"]["研发部"] == ["张三", "李四"]


def test_timer_settings_defaults_and_roundtrip(db_session):
    """计时设置默认 30/5，写入后读回。"""
    assert SettingsService.get_meeting_total_minutes(db_session) == 30
    assert SettingsService.get_meeting_person_threshold_minutes(db_session) == 5
    SettingsService.set_meeting_total_minutes(db_session, 45)
    SettingsService.set_meeting_person_threshold_minutes(db_session, 8)
    assert SettingsService.get_meeting_total_minutes(db_session) == 45
    assert SettingsService.get_meeting_person_threshold_minutes(db_session) == 8


def test_get_report_order_default_any_user(db_session):
    member = _make_user(db_session, "m1")
    client = _client(db_session, member)
    try:
        r = client.get("/api/v1/settings/meeting-report-order")
        assert r.status_code == 200
        assert r.json() == {"departments": [], "members": {}}
    finally:
        _cleanup()


def test_put_report_order_admin_then_get(db_session):
    admin = _make_user(db_session, "a1", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        payload = {"departments": ["研发部"], "members": {"研发部": ["张三", "李四"]}}
        r = client.put("/api/v1/settings/meeting-report-order", json=payload)
        assert r.status_code == 200
        assert r.json()["departments"] == ["研发部"]
        r2 = client.get("/api/v1/settings/meeting-report-order")
        assert r2.json()["members"]["研发部"] == ["张三", "李四"]
    finally:
        _cleanup()


def test_put_report_order_non_admin_403(db_session):
    member = _make_user(db_session, "m2")
    client = _client(db_session, member)
    try:
        r = client.put("/api/v1/settings/meeting-report-order",
                       json={"departments": [], "members": {}})
        assert r.status_code == 403
    finally:
        _cleanup()


def test_timer_get_defaults_then_put(db_session):
    admin = _make_user(db_session, "a2", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        r = client.get("/api/v1/settings/meeting-timer")
        assert r.json() == {"total_minutes": 30, "person_threshold_minutes": 5}
        r2 = client.put("/api/v1/settings/meeting-timer",
                        json={"total_minutes": 45, "person_threshold_minutes": 8})
        assert r2.status_code == 200
        assert r2.json()["total_minutes"] == 45
        assert client.get("/api/v1/settings/meeting-timer").json()["person_threshold_minutes"] == 8
    finally:
        _cleanup()


def test_timer_put_validation_rejects_zero(db_session):
    admin = _make_user(db_session, "a3", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        r = client.put("/api/v1/settings/meeting-timer",
                       json={"total_minutes": 0, "person_threshold_minutes": 5})
        assert r.status_code == 422
    finally:
        _cleanup()


from backend.services.meeting_record_service import MeetingRecordService


def test_start_report_sets_started_at_idempotent(db_session):
    """start_report 首次写 started_at，重复调用不覆盖。"""
    rec = MeetingRecord(session=10, meeting_date=date(2026, 6, 6), status="active")
    db_session.add(rec)
    db_session.commit()

    MeetingRecordService.start_report(db_session, 10)
    db_session.refresh(rec)
    first = rec.started_at
    assert first is not None

    MeetingRecordService.start_report(db_session, 10)
    db_session.refresh(rec)
    assert rec.started_at == first  # 不被覆盖


def test_archive_sets_ended_at(db_session):
    """归档时写 ended_at。"""
    rec = MeetingRecord(session=11, meeting_date=date(2026, 6, 6), status="active")
    db_session.add(rec)
    db_session.commit()

    MeetingRecordService.archive_meeting(db_session, 11)
    db_session.refresh(rec)
    assert rec.status == "archived"
    assert rec.ended_at is not None


from backend.models.operation_log import OperationLog


def test_start_report_endpoint_admin(db_session):
    """管理员调用 start-report → 200，且写一条操作日志。"""
    admin = _make_user(db_session, "a4", role=UserRole.ADMIN)
    rec = MeetingRecord(session=20, meeting_date=date(2026, 6, 6), status="active")
    db_session.add(rec)
    db_session.commit()
    client = _client(db_session, admin)
    try:
        r = client.post("/api/v1/meeting-records/20/start-report")
        assert r.status_code == 200
        db_session.refresh(rec)
        assert rec.started_at is not None
        logs = db_session.query(OperationLog).filter(
            OperationLog.action == "meeting_report_start").all()
        assert len(logs) == 1
    finally:
        _cleanup()


def test_start_report_endpoint_non_admin_403(db_session):
    member = _make_user(db_session, "m4")
    rec = MeetingRecord(session=21, meeting_date=date(2026, 6, 6), status="active")
    db_session.add(rec)
    db_session.commit()
    client = _client(db_session, member)
    try:
        r = client.post("/api/v1/meeting-records/21/start-report")
        assert r.status_code == 403
    finally:
        _cleanup()


def test_close_meeting_writes_end_log(db_session):
    """关闭周会写 meeting_report_end 日志。"""
    admin = _make_user(db_session, "a5", role=UserRole.ADMIN)
    rec = MeetingRecord(session=22, meeting_date=date(2026, 6, 6), status="active")
    db_session.add(rec)
    db_session.commit()
    client = _client(db_session, admin)
    try:
        r = client.post("/api/v1/meeting-records/close")
        assert r.status_code == 200
        logs = db_session.query(OperationLog).filter(
            OperationLog.action == "meeting_report_end").all()
        assert len(logs) == 1
    finally:
        _cleanup()
