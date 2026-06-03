"""周会定时自动开启 + 事件驱动周期 测试"""
import asyncio
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.base import Base
from backend.models.meeting_record import MeetingRecord
from backend.services.settings_service import (
    SettingsService, MEETING_BASE_MONDAY, MEETING_BASE_COUNT,
)
from backend.services import auto_meeting_service
from backend.services.auto_meeting_service import AutoMeetingService, _is_workday_safe


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _mk_record(db, session, meeting_date, status="archived"):
    rec = MeetingRecord(session=session, meeting_date=meeting_date, status=status,
                        recorder="x", content_snapshot=[])
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


# ---------- 事件驱动周期判断 ----------

def test_can_open_new_cycle_after_3_days(db_session):
    """会议日期周一(6-01)，今天周四(6-04)，间隔3天 -> 可开新周期，next_count=23"""
    _mk_record(db_session, 22, date(2026, 6, 1))
    st = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 4))
    assert st["can_open_new_cycle"] is True
    assert st["days_since_last"] == 3
    assert st["next_count"] == 23


def test_cannot_open_within_3_days(db_session):
    """会议日期周一(6-01)，今天周二(6-02)，间隔1天 -> 不可开新周期，next_count 不跳号"""
    _mk_record(db_session, 22, date(2026, 6, 1))
    st = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 2))
    assert st["can_open_new_cycle"] is False
    assert st["days_since_last"] == 1
    assert st["next_count"] == 22


def test_empty_table_fallback_to_base(db_session):
    """无任何 meeting_record -> 回退 base(2026-06-01, 22)，今天周四可开第23次"""
    st = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 4))
    assert st["last_meeting"]["count"] == 22
    assert st["can_open_new_cycle"] is True
    assert st["next_count"] == 23


def test_active_blocks_new_cycle(db_session):
    """存在进行中的周会 -> 不可开新周期，且 this_week_count=该active次数"""
    _mk_record(db_session, 23, date(2026, 6, 8), status="active")
    SettingsService.set_active(db_session, True)
    st = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 11))
    assert st["active"] is True
    assert st["this_week_count"] == 23
    assert st["can_open_new_cycle"] is False


# ---------- 自动开启 ----------

def test_auto_open_skips_non_workday(db_session, monkeypatch):
    """非工作日 -> 跳过，不建记录"""
    monkeypatch.setattr(auto_meeting_service, "_is_workday_safe", lambda d: False)
    result = asyncio.get_event_loop().run_until_complete(
        AutoMeetingService.auto_open_if_due(db_session, today=date(2026, 6, 4))
    )
    assert result is False
    assert db_session.query(MeetingRecord).count() == 0


def test_auto_open_skips_when_active(db_session, monkeypatch):
    """已 active -> no-op（开关已开，确保走到 active 检查）"""
    monkeypatch.setattr(auto_meeting_service, "_is_workday_safe", lambda d: True)
    SettingsService.set_auto_open_meeting_enabled(db_session, True)
    _mk_record(db_session, 23, date(2026, 6, 8), status="active")
    SettingsService.set_active(db_session, True)
    result = asyncio.get_event_loop().run_until_complete(
        AutoMeetingService.auto_open_if_due(db_session, today=date(2026, 6, 4))
    )
    assert result is False


def test_auto_open_creates_meeting_and_notifies(db_session, monkeypatch):
    """工作日 + 无 active -> 建 session=23/recorder=Shineleo/会议日期=下周一，并发文案A(operator=None)"""
    monkeypatch.setattr(auto_meeting_service, "_is_workday_safe", lambda d: True)
    SettingsService.set_auto_open_meeting_enabled(db_session, True)  # 开启运行时开关
    _mk_record(db_session, 22, date(2026, 6, 1))  # 上次第22次

    sent = {}
    async def fake_notify(chat_id, session, public_url, operator=None):
        sent.update(session=session, operator=operator)
        return True
    monkeypatch.setattr(
        auto_meeting_service.NotificationService, "notify_meeting_open", fake_notify
    )

    # today=周四 6-04
    result = asyncio.get_event_loop().run_until_complete(
        AutoMeetingService.auto_open_if_due(db_session, today=date(2026, 6, 4))
    )
    assert result is True
    rec = db_session.query(MeetingRecord).filter(MeetingRecord.status == "active").first()
    assert rec is not None
    assert rec.session == 23
    assert rec.recorder == "Shineleo"
    assert rec.meeting_date == date(2026, 6, 8)  # 周四的下周一
    assert sent == {"session": 23, "operator": None}


# ---------- 运行时开关（UI 可控） ----------

def test_auto_open_switch_default_disabled(db_session):
    """运行时开关默认关闭"""
    assert SettingsService.get_auto_open_meeting_enabled(db_session) is False


def test_auto_open_switch_set_get_roundtrip(db_session):
    """开关 set True -> get True；set False -> get False"""
    SettingsService.set_auto_open_meeting_enabled(db_session, True)
    assert SettingsService.get_auto_open_meeting_enabled(db_session) is True
    SettingsService.set_auto_open_meeting_enabled(db_session, False)
    assert SettingsService.get_auto_open_meeting_enabled(db_session) is False


def test_auto_open_noop_when_switch_off(db_session, monkeypatch):
    """开关关闭时：工作日 + 无 active 也不自动开（no-op，不建记录）"""
    monkeypatch.setattr(auto_meeting_service, "_is_workday_safe", lambda d: True)
    # 不设开关（默认 false）
    _mk_record(db_session, 22, date(2026, 6, 1))
    result = asyncio.get_event_loop().run_until_complete(
        AutoMeetingService.auto_open_if_due(db_session, today=date(2026, 6, 4))
    )
    assert result is False
    assert db_session.query(MeetingRecord).filter(MeetingRecord.status == "active").count() == 0


# ---------- 工作日判断退化 ----------

def test_is_workday_safe_fallback_on_error(monkeypatch):
    """chinese_calendar 抛 NotImplementedError(年份超范围) -> 退化为按星期判断"""
    import chinese_calendar
    def boom(d):
        raise NotImplementedError("year out of range")
    monkeypatch.setattr(chinese_calendar, "is_workday", boom)
    assert _is_workday_safe(date(2030, 1, 3)) is True   # 周四
    assert _is_workday_safe(date(2030, 1, 5)) is False  # 周六
