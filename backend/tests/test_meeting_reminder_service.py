"""周会自动催更服务测试"""
import asyncio
import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.models.project import Project, ProjectStatus, ProjectUrgency
from backend.models.meeting_record import MeetingRecord
from backend.services.meeting_reminder_service import (
    MeetingReminderService, _join_top, _join_top_with_count,
)
from backend.services.settings_service import (
    SettingsService, AUTO_REMINDER_ENABLED_KEY, FEISHU_CORE_GROUP_CHAT_ID_KEY,
)


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


def _mk_project(db, name="P", owner="申华", status=ProjectStatus.IN_PROGRESS, progress_log=None):
    p = Project(
        name=name, record_date=date(2026, 6, 1), status=status,
        urgency=ProjectUrgency.MEDIUM, owner_name=owner, progress_log=progress_log or [],
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _mk_meeting(db, session, meeting_date, status="active"):
    rec = MeetingRecord(session=session, meeting_date=meeting_date, recorder="R",
                        status=status, content_snapshot=[])
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


# ---- helpers ----

def test_join_top():
    assert _join_top(["A", "B", "C"]) == "A，B和C"
    assert _join_top(["A", "B"]) == "A和B"
    assert _join_top(["A"]) == "A"
    assert _join_top([]) == "暂无"


def test_join_top_with_count():
    assert _join_top_with_count([("A", 3), ("B", 2), ("C", 1)]) == "A（3条），B（2条）和C（1条）"
    assert _join_top_with_count([("A", 3)]) == "A（3条）"
    assert _join_top_with_count([]) == "暂无"


# ---- rank_update_counts (催更①) ----

def test_rank_update_counts(db_session):
    # 申华: 2 条 session=23；刘伟: 1 条；潘帅: session=22 不计；空owner跳过
    _mk_project(db_session, name="P1", owner="申华", progress_log=[
        {"id": "a", "meeting_session": 23, "time": "2026-06-05 10:00"},
        {"id": "b", "meeting_session": 23, "time": "2026-06-05 11:00"},
    ])
    _mk_project(db_session, name="P2", owner="刘伟", progress_log=[
        {"id": "c", "meeting_session": 23, "time": "2026-06-05 12:00"},
        {"id": "d", "meeting_session": 22, "time": "2026-05-28 12:00"},  # 旧次数不计
    ])
    _mk_project(db_session, name="P3", owner="", progress_log=[
        {"id": "e", "meeting_session": 23, "time": "2026-06-05 09:00"},  # 空owner跳过
    ])
    ranked = MeetingReminderService.rank_update_counts(db_session, session=23)
    assert ranked == [("申华", 2), ("刘伟", 1)]


def test_rank_update_counts_top3(db_session):
    for i, owner in enumerate(["A", "B", "C", "D"]):
        log = [{"id": f"{owner}{j}", "meeting_session": 23, "time": "2026-06-05 10:00"}
               for j in range(4 - i)]  # A:4 B:3 C:2 D:1
        _mk_project(db_session, name=f"P{owner}", owner=owner, progress_log=log)
    ranked = MeetingReminderService.rank_update_counts(db_session, session=23)
    assert ranked == [("A", 4), ("B", 3), ("C", 2)]  # 前三，D 落选


# ---- rank_pending_counts (催更②) ----

def test_rank_pending_counts(db_session):
    anchor = date(2026, 5, 28)  # 上周周会
    # 申华: 2 个 in_progress 项目都未在 anchor 后更新 -> 待更新 2
    _mk_project(db_session, name="S1", owner="申华", progress_log=[
        {"time": "2026-05-20 10:00"},  # anchor 之前
    ])
    _mk_project(db_session, name="S2", owner="申华", progress_log=[])  # 无进展
    # 刘伟: 1 个项目 anchor 后已更新 -> 不计；1 个未更新 -> 待更新 1
    _mk_project(db_session, name="L1", owner="刘伟", progress_log=[
        {"time": "2026-05-30 10:00"},  # anchor 之后，已更新
    ])
    _mk_project(db_session, name="L2", owner="刘伟", progress_log=[
        {"time": "2026-05-25 10:00"},  # 未更新
    ])
    # 已完成项目不计入
    _mk_project(db_session, name="DONE", owner="潘帅",
                status=ProjectStatus.COMPLETED, progress_log=[])
    ranked = MeetingReminderService.rank_pending_counts(db_session, anchor)
    assert ranked == [("申华", 2), ("刘伟", 1)]


def test_rank_pending_excludes_non_inprogress(db_session):
    anchor = date(2026, 5, 28)
    _mk_project(db_session, name="P1", owner="A", status=ProjectStatus.PAUSED, progress_log=[])
    _mk_project(db_session, name="P2", owner="A", status=ProjectStatus.PLANNED, progress_log=[])
    ranked = MeetingReminderService.rank_pending_counts(db_session, anchor)
    assert ranked == []


# ---- _anchor_date ----

def test_anchor_date_from_prev_meeting(db_session):
    _mk_meeting(db_session, 22, date(2026, 5, 25), status="archived")
    active = _mk_meeting(db_session, 23, date(2026, 6, 1), status="active")
    assert MeetingReminderService._anchor_date(db_session, active) == date(2026, 5, 25)


def test_anchor_date_fallback_minus7(db_session):
    active = _mk_meeting(db_session, 23, date(2026, 6, 1), status="active")
    # 无更早周会 -> 会议日期 - 7 天
    assert MeetingReminderService._anchor_date(db_session, active) == date(2026, 5, 25)


# ---- send guards ----

def test_send_reminder_one_guard_switch_off(db_session):
    _mk_meeting(db_session, 23, date(2026, 6, 1), status="active")
    SettingsService.set_setting(db_session, FEISHU_CORE_GROUP_CHAT_ID_KEY, "oc_x")
    # 开关默认关
    sent = asyncio.run(MeetingReminderService.send_reminder_one(db_session))
    assert sent is False


def test_send_reminder_one_guard_no_active(db_session):
    SettingsService.set_setting(db_session, AUTO_REMINDER_ENABLED_KEY, "true")
    SettingsService.set_setting(db_session, FEISHU_CORE_GROUP_CHAT_ID_KEY, "oc_x")
    # 无 active 周会
    sent = asyncio.run(MeetingReminderService.send_reminder_one(db_session))
    assert sent is False


def test_send_reminder_one_guard_no_chat(db_session):
    SettingsService.set_setting(db_session, AUTO_REMINDER_ENABLED_KEY, "true")
    _mk_meeting(db_session, 23, date(2026, 6, 1), status="active")
    # 核心群未配置
    sent = asyncio.run(MeetingReminderService.send_reminder_one(db_session))
    assert sent is False


def test_send_reminder_one_sends_when_ready(db_session, monkeypatch):
    SettingsService.set_setting(db_session, AUTO_REMINDER_ENABLED_KEY, "true")
    SettingsService.set_setting(db_session, FEISHU_CORE_GROUP_CHAT_ID_KEY, "oc_x")
    _mk_meeting(db_session, 23, date(2026, 6, 1), status="active")
    _mk_project(db_session, name="P1", owner="申华", progress_log=[
        {"id": "a", "meeting_session": 23, "time": "2026-06-05 10:00"},
    ])
    captured = {}

    async def fake_notify(chat_id, session, body):
        captured["chat_id"] = chat_id
        captured["session"] = session
        captured["body"] = body
        return True

    monkeypatch.setattr(
        "backend.services.meeting_reminder_service.NotificationService.notify_meeting_reminder",
        fake_notify,
    )
    sent = asyncio.run(MeetingReminderService.send_reminder_one(db_session))
    assert sent is True
    assert captured["chat_id"] == "oc_x"
    assert captured["session"] == 23
    assert "申华" in captured["body"]
    assert "值得鼓励" in captured["body"]


def test_send_reminder_two_sends_when_ready(db_session, monkeypatch):
    SettingsService.set_setting(db_session, AUTO_REMINDER_ENABLED_KEY, "true")
    SettingsService.set_setting(db_session, FEISHU_CORE_GROUP_CHAT_ID_KEY, "oc_x")
    _mk_meeting(db_session, 22, date(2026, 5, 25), status="archived")
    _mk_meeting(db_session, 23, date(2026, 6, 1), status="active")
    _mk_project(db_session, name="S1", owner="申华", progress_log=[])  # 待更新
    captured = {}

    async def fake_notify(chat_id, session, body):
        captured["body"] = body
        return True

    monkeypatch.setattr(
        "backend.services.meeting_reminder_service.NotificationService.notify_meeting_reminder",
        fake_notify,
    )
    sent = asyncio.run(MeetingReminderService.send_reminder_two(db_session))
    assert sent is True
    assert "明天将召开周例会" in captured["body"]
    assert "申华（1条）" in captured["body"]
    assert "请加油" in captured["body"]
