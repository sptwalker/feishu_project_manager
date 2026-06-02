"""周会记录归档服务测试"""
import asyncio
import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.models.project import Project, ProjectStatus, ProjectUrgency
from backend.models.department import Department
from backend.models.meeting_record import MeetingRecord
from backend.services.meeting_record_service import MeetingRecordService
from backend.services.settings_service import SettingsService, MEETING_ACTIVE


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


def _mk_project(db, name="P", department=None, owner_name=None,
                urgency=ProjectUrgency.MEDIUM, progress_log=None):
    p = Project(
        name=name, record_date=date(2026, 6, 1), status=ProjectStatus.IN_PROGRESS,
        urgency=urgency, department=department, owner_name=owner_name,
        progress_log=progress_log or [],
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ---------- build_snapshot ----------

def test_build_snapshot_filters_by_session(db_session):
    _mk_project(db_session, name="A", progress_log=[
        {"time": "2026-06-01 10:00", "content": "旧", "status": "正常", "id": "e1", "meeting_session": 21},
        {"time": "2026-06-08 10:00", "content": "本次", "status": "正常", "id": "e2", "meeting_session": 22},
    ])
    snap = MeetingRecordService.build_snapshot(db_session, 22)
    assert len(snap) == 1
    assert snap[0]["project"] == "A"
    assert snap[0]["content"] == "本次"


def test_build_snapshot_latest_per_project(db_session):
    _mk_project(db_session, name="A", progress_log=[
        {"time": "2026-06-08 09:00", "content": "早", "status": "正常", "meeting_session": 22},
        {"time": "2026-06-08 15:00", "content": "晚", "status": "待确认", "meeting_session": 22},
    ])
    snap = MeetingRecordService.build_snapshot(db_session, 22)
    assert len(snap) == 1
    assert snap[0]["content"] == "晚"
    assert snap[0]["status"] == "待确认"


def test_build_snapshot_sort_dept_owner_urgency(db_session):
    db_session.add(Department(name="研发", short_name="研发", color="#1A73E8"))
    db_session.commit()
    _mk_project(db_session, name="P-low", department="研发", owner_name="张三",
                urgency=ProjectUrgency.LOW, progress_log=[
                    {"time": "2026-06-08 10:00", "content": "c", "status": "正常", "meeting_session": 22}])
    _mk_project(db_session, name="P-urgent", department="研发", owner_name="张三",
                urgency=ProjectUrgency.URGENT, progress_log=[
                    {"time": "2026-06-08 10:00", "content": "c", "status": "正常", "meeting_session": 22}])
    snap = MeetingRecordService.build_snapshot(db_session, 22)
    # 同部门同负责人，重要在前
    assert [s["project"] for s in snap] == ["P-urgent", "P-low"]
    assert snap[0]["dept_short"] == "研发"
    assert snap[0]["dept_color"] == "#1A73E8"


# ---------- open / archive / 跨周结束 ----------

def test_open_meeting_sets_active_and_record(db_session):
    detail = MeetingRecordService.open_meeting(db_session, 22, "刘丹", date(2026, 6, 8))
    assert detail["session"] == 22
    assert detail["recorder"] == "刘丹"
    assert detail["meeting_date"] == "2026-06-08"
    assert SettingsService.get_setting(db_session, MEETING_ACTIVE) == "true"
    rec = db_session.query(MeetingRecord).filter(MeetingRecord.session == 22).first()
    assert rec.status == "active"


def test_open_meeting_ends_previous_active(db_session):
    # 先开第 22 次
    MeetingRecordService.open_meeting(db_session, 22, "甲", date(2026, 6, 1))
    # 跨周开第 23 次 → 应结束上一次（22 归档）
    MeetingRecordService.open_meeting(db_session, 23, "乙", date(2026, 6, 8))
    rec22 = db_session.query(MeetingRecord).filter(MeetingRecord.session == 22).first()
    rec23 = db_session.query(MeetingRecord).filter(MeetingRecord.session == 23).first()
    assert rec22.status == "archived"
    assert rec23.status == "active"


def test_archive_snapshot_is_frozen(db_session):
    p = _mk_project(db_session, name="A", progress_log=[
        {"time": "2026-06-08 10:00", "content": "原始", "status": "正常", "meeting_session": 22}])
    MeetingRecordService.open_meeting(db_session, 22, "甲", date(2026, 6, 8))
    MeetingRecordService.archive_meeting(db_session, 22)
    # 归档后修改项目进展
    p.progress_log = [
        {"time": "2026-06-08 10:00", "content": "被改了", "status": "正常", "meeting_session": 22}]
    db_session.commit()
    detail = MeetingRecordService.get_session_detail(db_session, 22)
    # 归档快照应保持原始内容，不随后续编辑变化
    assert detail["status"] == "archived"
    assert detail["items"][0]["content"] == "原始"


def test_close_meeting_archives_and_deactivates(db_session):
    _mk_project(db_session, name="A", progress_log=[
        {"time": "2026-06-08 10:00", "content": "c", "status": "正常", "meeting_session": 22}])
    MeetingRecordService.open_meeting(db_session, 22, "甲", date(2026, 6, 8))
    MeetingRecordService.close_meeting(db_session)
    rec = db_session.query(MeetingRecord).filter(MeetingRecord.session == 22).first()
    assert rec.status == "archived"
    assert SettingsService.get_setting(db_session, MEETING_ACTIVE) == "false"


# ---------- detail 回退 / sessions ----------

def test_get_detail_dynamic_fallback_when_not_archived(db_session):
    # 无归档记录，纯动态扫描
    _mk_project(db_session, name="A", progress_log=[
        {"time": "2026-06-08 10:00", "content": "动态", "status": "正常", "meeting_session": 22}])
    detail = MeetingRecordService.get_session_detail(db_session, 22)
    assert detail["items"][0]["content"] == "动态"
    assert detail["meeting_date"] == "2026-06-08"  # 取快照内最新 time 的日期


def test_list_sessions_includes_archived_scanned_current(db_session):
    _mk_project(db_session, name="A", progress_log=[
        {"time": "2026-05-18 10:00", "content": "c", "status": "正常", "meeting_session": 20}])
    MeetingRecordService.open_meeting(db_session, 22, "甲", date(2026, 6, 1))
    out = MeetingRecordService.list_sessions(db_session)
    assert 20 in out["sessions"]   # progress_log 扫描到
    assert 22 in out["sessions"]   # 归档表
    assert out["current"] in out["sessions"]


# ---------- send_meeting no-op ----------

def test_send_meeting_noop_when_notify_disabled(db_session, monkeypatch):
    from backend.core import config
    settings = config.get_settings()
    monkeypatch.setattr(settings, "FEISHU_NOTIFY_ENABLED", False)
    _mk_project(db_session, name="A", progress_log=[
        {"time": "2026-06-08 10:00", "content": "c", "status": "正常", "meeting_session": 22}])
    res = asyncio.run(MeetingRecordService.send_meeting(db_session, 22))
    assert res["ok"] is False
    assert "未开启" in res["message"]


def test_send_meeting_empty(db_session, monkeypatch):
    from backend.core import config
    settings = config.get_settings()
    monkeypatch.setattr(settings, "FEISHU_NOTIFY_ENABLED", True)
    res = asyncio.run(MeetingRecordService.send_meeting(db_session, 99))
    assert res["ok"] is False
    assert "暂无记录" in res["message"]
