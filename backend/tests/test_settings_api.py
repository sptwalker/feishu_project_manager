from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.user import User, UserRole
from backend.models.project import Project
from backend.models import (  # noqa: F401  确保所有表注册到 Base.metadata
    User as _U, Project as _P, Task as _T, Event as _E, Risk as _R,
    Department as _D, SystemSetting as _S,
)
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.services.settings_service import SettingsService, compute_count, monday_of


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


def _make_user(db, feishu_id, role=UserRole.MEMBER):
    u = User(feishu_user_id=feishu_id, name=feishu_id, role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
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


# ---------- 纯算法 ----------

def test_monday_of():
    assert monday_of(date(2026, 6, 1)) == date(2026, 6, 1)   # 周一
    assert monday_of(date(2026, 6, 7)) == date(2026, 6, 1)   # 周日
    assert monday_of(date(2026, 5, 31)) == date(2026, 5, 25)


def test_compute_count_by_natural_week():
    bm = date(2026, 6, 1)
    assert compute_count(date(2026, 5, 31), bm, 22) == 21   # 上一周
    assert compute_count(date(2026, 6, 1), bm, 22) == 22
    assert compute_count(date(2026, 6, 3), bm, 22) == 22    # 同周不变
    assert compute_count(date(2026, 6, 7), bm, 22) == 22
    assert compute_count(date(2026, 6, 8), bm, 22) == 23    # 跨周 +1
    assert compute_count(date(2026, 6, 15), bm, 22) == 24


# ---------- 状态 / 事件驱动周期 ----------

def test_meeting_state_event_driven_cycle(db_session):
    """事件驱动周期：以 meeting_records 表的上次会议日期 + NEW_CYCLE_DAYS 判定新周期。"""
    from backend.models.meeting_record import MeetingRecord
    # 上次周会 session=22，会议日期 2026-06-01（周一），已归档
    db_session.add(MeetingRecord(session=22, meeting_date=date(2026, 6, 1),
                                 status="archived", recorder="x", content_snapshot=[]))
    db_session.commit()

    # 今天周三 2026-06-03（间隔2天 < 3）-> 不可开新周期；但次数仍递进(冷却只决定何时能开)
    st = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 3))
    assert st["this_week_count"] == 22
    assert st["this_week_recorded"] is False        # 无 active 记录
    assert st["last_meeting"] == {"date": "2026-06-01", "count": 22}
    assert st["can_open_new_cycle"] is False
    assert st["next_count"] == 23

    # 今天周四 2026-06-04（间隔3天）-> 可开新周期，next=23
    st2 = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 4))
    assert st2["can_open_new_cycle"] is True
    assert st2["days_since_last"] == 3
    assert st2["next_count"] == 23
    assert st2["calibration_count"] == 23           # 兼容旧字段=next_count


def test_meeting_state_active_blocks_new_cycle(db_session):
    """存在 active 记录时：this_week_count=该次数、recorded=True、不可开新周期。"""
    from backend.models.meeting_record import MeetingRecord
    db_session.add(MeetingRecord(session=23, meeting_date=date(2026, 6, 8),
                                 status="active", recorder="x", content_snapshot=[]))
    db_session.commit()
    SettingsService.set_active(db_session, True)
    st = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 11))
    assert st["active"] is True
    assert st["this_week_count"] == 23
    assert st["this_week_recorded"] is True
    assert st["can_open_new_cycle"] is False


def test_meeting_state_empty_table_fallback_to_base(db_session):
    """无任何 meeting_record -> 回退 base 锚点(2026-06-01, 22)作为上次周会。"""
    st = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 4))
    assert st["last_meeting"]["count"] == 22
    assert st["can_open_new_cycle"] is True
    assert st["next_count"] == 23


def test_set_count_resets_base(db_session):
    # 本周未记录时校准本周次数
    SettingsService.set_count(db_session, 30, today=date(2026, 6, 1))
    st = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 1))
    assert st["this_week_count"] == 30
    assert st["base_count"] == 30
    assert st["base_monday"] == "2026-06-01"


# ---------- API 权限 ----------

def test_get_meeting_state_any_user(db_session):
    member = _make_user(db_session, "m1")
    client = _client(db_session, member)
    try:
        r = client.get("/api/v1/settings/meeting")
        assert r.status_code == 200
        assert "active" in r.json()
        assert "this_week_count" in r.json()
    finally:
        _cleanup()


def test_set_active_admin(db_session):
    admin = _make_user(db_session, "admin1", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        r = client.put("/api/v1/settings/meeting/active", json={"active": True})
        assert r.status_code == 200
        assert r.json()["active"] is True
        r2 = client.put("/api/v1/settings/meeting/active", json={"active": False})
        assert r2.json()["active"] is False
    finally:
        _cleanup()


def test_set_active_non_admin_403(db_session):
    member = _make_user(db_session, "m1")
    client = _client(db_session, member)
    try:
        r = client.put("/api/v1/settings/meeting/active", json={"active": True})
        assert r.status_code == 403
    finally:
        _cleanup()


def test_set_count_non_admin_403(db_session):
    member = _make_user(db_session, "m1")
    client = _client(db_session, member)
    try:
        r = client.put("/api/v1/settings/meeting/count", json={"count": 25})
        assert r.status_code == 403
    finally:
        _cleanup()


# ---------- 核心群 chat_id ----------

def test_get_core_chat_id_default_empty(db_session):
    """未配置时 GET 返回空字符串（纯 DB，不依赖 .env）"""
    member = _make_user(db_session, "m1")
    client = _client(db_session, member)
    try:
        r = client.get("/api/v1/settings/core-group-chat-id")
        assert r.status_code == 200
        assert r.json()["chat_id"] == ""
    finally:
        _cleanup()


def test_put_then_get_core_chat_id(db_session):
    """管理员 PUT 后 GET 回读一致"""
    admin = _make_user(db_session, "admin1", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        r = client.put("/api/v1/settings/core-group-chat-id", json={"chat_id": "oc_abc123"})
        assert r.status_code == 200
        assert r.json()["chat_id"] == "oc_abc123"
        r2 = client.get("/api/v1/settings/core-group-chat-id")
        assert r2.json()["chat_id"] == "oc_abc123"
    finally:
        _cleanup()


def test_put_core_chat_id_non_admin_403(db_session):
    """普通成员无权设置 chat_id"""
    member = _make_user(db_session, "m1")
    client = _client(db_session, member)
    try:
        r = client.put("/api/v1/settings/core-group-chat-id", json={"chat_id": "oc_x"})
        assert r.status_code == 403
    finally:
        _cleanup()


def test_put_empty_clears_core_chat_id(db_session):
    """PUT 空字符串清空 DB 值，GET 返回空字符串"""
    admin = _make_user(db_session, "admin1", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        client.put("/api/v1/settings/core-group-chat-id", json={"chat_id": "oc_abc"})
        r = client.put("/api/v1/settings/core-group-chat-id", json={"chat_id": ""})
        assert r.status_code == 200
        assert r.json()["chat_id"] == ""
        r2 = client.get("/api/v1/settings/core-group-chat-id")
        assert r2.json()["chat_id"] == ""
    finally:
        _cleanup()
