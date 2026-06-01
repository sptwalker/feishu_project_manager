"""项目进展跟催服务测试"""
import asyncio
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.models.project import Project, ProjectStatus, ProjectUrgency
from backend.models.user import User, UserRole
from backend.services.project_followup_service import (
    ProjectFollowupService, progress_stall_days, unclosed_pending_statuses,
    get_stall_days_threshold, SETTING_FOLLOWUP_STALL_DAYS, DEFAULT_FOLLOWUP_STALL_DAYS,
)
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


def _mk_project(db, name="P", status=ProjectStatus.IN_PROGRESS, owner_name=None, progress_log=None):
    from datetime import date
    p = Project(
        name=name, record_date=date(2026, 6, 1), status=status,
        urgency=ProjectUrgency.MEDIUM, owner_name=owner_name,
        progress_log=progress_log or [],
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ---------- progress_stall_days ----------

def test_stall_days_no_progress_returns_none(db_session):
    p = _mk_project(db_session, progress_log=[])
    assert progress_stall_days(p) is None


def test_stall_days_computed_from_latest(db_session):
    now = datetime(2026, 6, 1, 12, 0)
    p = _mk_project(db_session, progress_log=[
        {"time": "2026-05-01 10:00", "content": "旧", "status": "正常", "id": "e1"},
        {"time": "2026-05-20 10:00", "content": "新", "status": "正常", "id": "e2"},
    ])
    # 最新是 5-20，距 6-1 共 12 天
    assert progress_stall_days(p, now) == 12


# ---------- unclosed_pending_statuses ----------

def test_unclosed_pending_basic(db_session):
    p = _mk_project(db_session, progress_log=[
        {"time": "2026-05-01 10:00", "content": "讨论", "status": "待讨论", "id": "e1"},
    ])
    assert unclosed_pending_statuses(p) == ["待讨论"]


def test_unclosed_pending_closed_by_feedback(db_session):
    """有反馈闭合的 pending 不算未闭合（修复过的双问号场景）"""
    p = _mk_project(db_session, progress_log=[
        {"time": "2026-05-01 10:00", "content": "讨论", "status": "待讨论", "id": "e1"},
        {"time": "2026-05-02 10:00", "content": "已反馈", "status": "待讨论", "id": "e2", "reply_to": "e1"},
        {"time": "2026-05-03 10:00", "content": "确认", "status": "待确认", "id": "e3"},
    ])
    # e1 被 e2 反馈闭合，e2 自身是反馈不算，仅剩 e3 待确认
    assert unclosed_pending_statuses(p) == ["待确认"]


def test_unclosed_pending_order_preserved(db_session):
    p = _mk_project(db_session, progress_log=[
        {"time": "2026-05-03 10:00", "content": "执行", "status": "待执行", "id": "e3"},
        {"time": "2026-05-01 10:00", "content": "讨论", "status": "待讨论", "id": "e1"},
    ])
    # 按 PENDING_STATUSES 顺序：待讨论在前
    assert unclosed_pending_statuses(p) == ["待讨论", "待执行"]


# ---------- get_stall_days_threshold ----------

def test_threshold_default(db_session):
    assert get_stall_days_threshold(db_session) == DEFAULT_FOLLOWUP_STALL_DAYS


def test_threshold_from_setting(db_session):
    SettingsService.set_setting(db_session, SETTING_FOLLOWUP_STALL_DAYS, "7")
    assert get_stall_days_threshold(db_session) == 7


def test_threshold_invalid_falls_back(db_session):
    SettingsService.set_setting(db_session, SETTING_FOLLOWUP_STALL_DAYS, "abc")
    assert get_stall_days_threshold(db_session) == DEFAULT_FOLLOWUP_STALL_DAYS
    SettingsService.set_setting(db_session, SETTING_FOLLOWUP_STALL_DAYS, "0")
    assert get_stall_days_threshold(db_session) == DEFAULT_FOLLOWUP_STALL_DAYS


# ---------- find_at_risk_projects ----------

def test_find_at_risk_stalled(db_session):
    now = datetime(2026, 6, 1, 12, 0)
    _mk_project(db_session, name="停滞", progress_log=[
        {"time": "2026-04-01 10:00", "content": "很久没更新", "status": "正常", "id": "e1"},
    ])
    risk = ProjectFollowupService.find_at_risk_projects(db_session, stall_days_threshold=30, now=now)
    assert len(risk) == 1
    assert risk[0]["project"].name == "停滞"
    assert any("停滞" in r for r in risk[0]["reasons"])


def test_find_at_risk_no_progress(db_session):
    now = datetime(2026, 6, 1, 12, 0)
    _mk_project(db_session, name="无进展", progress_log=[])
    risk = ProjectFollowupService.find_at_risk_projects(db_session, stall_days_threshold=30, now=now)
    assert len(risk) == 1
    assert risk[0]["no_progress"] is True
    assert "无进展记录" in risk[0]["reasons"]


def test_find_at_risk_unclosed_pending(db_session):
    now = datetime(2026, 6, 1, 12, 0)
    # 最近有进展（不停滞），但有未闭合待办
    _mk_project(db_session, name="有待办", progress_log=[
        {"time": "2026-05-31 10:00", "content": "待确认", "status": "待确认", "id": "e1"},
    ])
    risk = ProjectFollowupService.find_at_risk_projects(db_session, stall_days_threshold=30, now=now)
    assert len(risk) == 1
    assert risk[0]["pending_list"] == ["待确认"]


def test_find_at_risk_healthy_excluded(db_session):
    now = datetime(2026, 6, 1, 12, 0)
    # 最近有进展且无待办 → 不催办
    _mk_project(db_session, name="健康", progress_log=[
        {"time": "2026-05-31 10:00", "content": "正常推进", "status": "正常", "id": "e1"},
    ])
    risk = ProjectFollowupService.find_at_risk_projects(db_session, stall_days_threshold=30, now=now)
    assert len(risk) == 0


def test_find_at_risk_completed_excluded(db_session):
    now = datetime(2026, 6, 1, 12, 0)
    _mk_project(db_session, name="已完成", status=ProjectStatus.COMPLETED, progress_log=[
        {"time": "2026-01-01 10:00", "content": "很久前", "status": "正常", "id": "e1"},
    ])
    risk = ProjectFollowupService.find_at_risk_projects(db_session, stall_days_threshold=30, now=now)
    assert len(risk) == 0


# ---------- resolve_owner_feishu_id ----------

def test_resolve_owner_by_name(db_session):
    user = User(feishu_user_id="ou_zhangsan", name="张三", role=UserRole.MEMBER)
    db_session.add(user)
    db_session.commit()
    assert ProjectFollowupService.resolve_owner_feishu_id(db_session, "张三") == "ou_zhangsan"


def test_resolve_owner_by_name_en(db_session):
    user = User(feishu_user_id="ou_lisi", name="李四", name_en="Lisi", role=UserRole.MEMBER)
    db_session.add(user)
    db_session.commit()
    assert ProjectFollowupService.resolve_owner_feishu_id(db_session, "Lisi") == "ou_lisi"


def test_resolve_owner_unknown_returns_none(db_session):
    assert ProjectFollowupService.resolve_owner_feishu_id(db_session, "查无此人") is None
    assert ProjectFollowupService.resolve_owner_feishu_id(db_session, None) is None
    assert ProjectFollowupService.resolve_owner_feishu_id(db_session, "  ") is None


# ---------- send_project_followups（开关关闭时 no-op） ----------

def test_send_followups_noop_without_chat_id(db_session, monkeypatch):
    """未配置群 chat_id 时不发送"""
    from backend.core import config
    settings = config.get_settings()
    monkeypatch.setattr(settings, "FEISHU_PROJECT_GROUP_CHAT_ID", "")
    _mk_project(db_session, name="停滞", progress_log=[
        {"time": "2026-04-01 10:00", "content": "x", "status": "正常", "id": "e1"},
    ])
    sent = asyncio.run(ProjectFollowupService.send_project_followups(db_session))
    assert sent == 0
