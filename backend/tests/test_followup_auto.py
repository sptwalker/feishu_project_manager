"""自动定时催办测试（due_now 判定 + tick 守卫）"""
import asyncio
import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.models.project import Project, ProjectStatus, ProjectUrgency
from backend.models.user import User, UserRole
from backend.services.followup_auto_service import FollowupAutoService, due_now
from backend.services.settings_service import SettingsService


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


# 2026-06-12 是周五（weekday=4）14:00
FRI_1400 = datetime(2026, 6, 12, 14, 0)


# ---------- due_now ----------

def test_due_disabled():
    cfg = {"enabled": False, "mode": "weekly", "weekday": 4, "time": "14:00"}
    assert due_now(cfg, FRI_1400, None) is False


def test_due_weekly_match():
    cfg = {"enabled": True, "mode": "weekly", "weekday": 4, "time": "14:00"}
    assert due_now(cfg, FRI_1400, None) is True


def test_due_weekly_wrong_day():
    cfg = {"enabled": True, "mode": "weekly", "weekday": 0, "time": "14:00"}  # 周一
    assert due_now(cfg, FRI_1400, None) is False


def test_due_weekly_wrong_time():
    cfg = {"enabled": True, "mode": "weekly", "weekday": 4, "time": "09:00"}
    assert due_now(cfg, FRI_1400, None) is False


def test_due_same_day_no_repeat():
    cfg = {"enabled": True, "mode": "weekly", "weekday": 4, "time": "14:00"}
    assert due_now(cfg, FRI_1400, date(2026, 6, 12)) is False  # 当天已跑


def test_due_fixed_days_first_run():
    cfg = {"enabled": True, "mode": "fixed_days", "interval_days": 5, "time": "14:00"}
    assert due_now(cfg, FRI_1400, None) is True  # 从未跑过，到点即触发


def test_due_fixed_days_interval_elapsed():
    cfg = {"enabled": True, "mode": "fixed_days", "interval_days": 5, "time": "14:00"}
    assert due_now(cfg, FRI_1400, date(2026, 6, 7)) is True   # 距 5 天
    assert due_now(cfg, FRI_1400, date(2026, 6, 9)) is False  # 距 3 天，未到


def test_due_follow_meeting_never_via_tick():
    cfg = {"enabled": True, "mode": "follow_meeting", "follow": ["one"], "time": "14:00"}
    assert due_now(cfg, FRI_1400, None) is False


# ---------- tick ----------

def _mk(db, name, owner, fid=None):
    if fid:
        db.add(User(feishu_user_id=fid, name=owner, role=UserRole.MEMBER))
    p = Project(name=name, record_date=date(2026, 1, 1), status=ProjectStatus.IN_PROGRESS,
                urgency=ProjectUrgency.MEDIUM, owner_name=owner,
                progress_log=[{"time": "2026-01-01 10:00", "content": "x", "status": "正常", "id": "a"}])
    db.add(p); db.commit()


def test_tick_fires_and_sets_last_run(db_session, monkeypatch):
    _mk(db_session, "P", "申华", fid="ou_shen")
    SettingsService.set_followup_auto(db_session, {
        "enabled": True, "mode": "weekly", "weekday": 4, "time": "14:00"})
    sent = []

    async def fake_notify(open_id, owner, lines, auto=False):
        sent.append((owner, auto)); return True

    monkeypatch.setattr(
        "backend.services.project_followup_service.NotificationService.notify_owner_followup",
        fake_notify)
    n = asyncio.run(FollowupAutoService.tick(db_session, FRI_1400))
    assert n == 1
    assert sent == [("申华", True)]
    # last_run_date 已写入，再次 tick 当天不重复
    again = asyncio.run(FollowupAutoService.tick(db_session, FRI_1400))
    assert again == 0


def test_tick_not_due_does_nothing(db_session, monkeypatch):
    _mk(db_session, "P", "申华", fid="ou_shen")
    SettingsService.set_followup_auto(db_session, {
        "enabled": True, "mode": "weekly", "weekday": 0, "time": "14:00"})  # 周一，不匹配周五
    called = []

    async def fake_notify(*a, **k):
        called.append(1); return True

    monkeypatch.setattr(
        "backend.services.project_followup_service.NotificationService.notify_owner_followup",
        fake_notify)
    n = asyncio.run(FollowupAutoService.tick(db_session, FRI_1400))
    assert n == 0
    assert called == []
