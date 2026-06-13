"""按负责人聚合 + 私聊催办测试"""
import asyncio
import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.models.project import Project, ProjectStatus, ProjectUrgency
from backend.models.user import User, UserRole
from backend.services.project_followup_service import ProjectFollowupService
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


def _mk_project(db, name, owner, status=ProjectStatus.IN_PROGRESS, progress_log=None):
    p = Project(name=name, record_date=date(2026, 6, 1), status=status,
                urgency=ProjectUrgency.MEDIUM, owner_name=owner, progress_log=progress_log or [])
    db.add(p); db.commit(); db.refresh(p)
    return p


def _mk_user(db, name, feishu_id="ou_x", name_en=None):
    u = User(feishu_user_id=feishu_id, name=name, name_en=name_en, role=UserRole.MEMBER)
    db.add(u); db.commit(); db.refresh(u)
    return u


NOW = datetime(2026, 6, 10, 12, 0)
OLD = "2026-01-01 10:00"   # 远超 30 天停滞


# ---------- group_at_risk_by_owner ----------

def test_group_two_dimensions_and_counts(db_session):
    # 申华：一个停滞项目 + 一个待办项目
    _mk_project(db_session, "停滞项目", "申华", progress_log=[{"time": OLD, "content": "x", "status": "正常", "id": "a"}])
    _mk_project(db_session, "待办项目", "申华", progress_log=[
        {"time": "2026-06-09 10:00", "content": "讨论", "status": "待讨论", "id": "b"}])
    groups = ProjectFollowupService.group_at_risk_by_owner(db_session, now=NOW)
    g = next(x for x in groups if x["owner"] == "申华")
    assert g["stalled_count"] == 1
    assert g["pending_count"] == 1
    assert {p["name"] for p in g["projects"]} == {"停滞项目", "待办项目"}


def test_group_project_in_both_dimensions(db_session):
    # 同一项目既停滞又有未闭合待办 → 两个维度都出现，但 projects 去重为一行
    _mk_project(db_session, "双重项目", "李四", progress_log=[
        {"time": OLD, "content": "讨论", "status": "待讨论", "id": "a"}])
    g = ProjectFollowupService.group_at_risk_by_owner(db_session, now=NOW)[0]
    assert g["stalled_count"] == 1 and g["pending_count"] == 1
    assert len(g["projects"]) == 1


def test_group_resolvable_flag(db_session):
    _mk_user(db_session, "申华", feishu_id="ou_shen")
    _mk_project(db_session, "P1", "申华", progress_log=[{"time": OLD, "content": "x", "status": "正常", "id": "a"}])
    _mk_project(db_session, "P2", "查无此人", progress_log=[{"time": OLD, "content": "x", "status": "正常", "id": "b"}])
    groups = {g["owner"]: g for g in ProjectFollowupService.group_at_risk_by_owner(db_session, now=NOW)}
    assert groups["申华"]["resolvable"] is True
    assert groups["查无此人"]["resolvable"] is False


def test_reason_texts(db_session):
    p = _mk_project(db_session, "P", "王五", progress_log=[
        {"time": "2026-06-09 10:00", "content": "确认", "status": "待确认", "id": "a"}])
    entries = ProjectFollowupService.find_at_risk_projects(db_session, now=NOW)
    e = next(x for x in entries if x["project"].id == p.id)
    reasons = ProjectFollowupService._reason_texts(e)
    assert "有未处理的待确认事项" in reasons


def test_reason_texts_stalled_days(db_session):
    p = _mk_project(db_session, "P", "王五", progress_log=[{"time": OLD, "content": "x", "status": "正常", "id": "a"}])
    e = next(x for x in ProjectFollowupService.find_at_risk_projects(db_session, now=NOW) if x["project"].id == p.id)
    reasons = ProjectFollowupService._reason_texts(e)
    assert any("没有反馈进展信息" in r for r in reasons)


def test_reason_texts_no_progress(db_session):
    p = _mk_project(db_session, "P", "王五", progress_log=[])
    e = next(x for x in ProjectFollowupService.find_at_risk_projects(db_session, now=NOW) if x["project"].id == p.id)
    assert "暂无任何进展记录" in ProjectFollowupService._reason_texts(e)


# ---------- send_owner_followup ----------

def test_send_owner_unresolved_not_sent(db_session):
    _mk_project(db_session, "P", "无账号人", progress_log=[{"time": OLD, "content": "x", "status": "正常", "id": "a"}])
    res = asyncio.run(ProjectFollowupService.send_owner_followup(db_session, "无账号人"))
    assert res["sent"] is False
    assert res["reason"] == "未关联飞书账号"


def test_send_owner_no_risk(db_session):
    _mk_user(db_session, "闲人", feishu_id="ou_idle")
    res = asyncio.run(ProjectFollowupService.send_owner_followup(db_session, "闲人"))
    assert res["sent"] is False
    assert res["reason"] == "无需催办"


def test_send_owner_resolved_sends(db_session, monkeypatch):
    _mk_user(db_session, "申华", feishu_id="ou_shen")
    _mk_project(db_session, "P", "申华", progress_log=[{"time": OLD, "content": "x", "status": "正常", "id": "a"}])
    captured = {}

    async def fake_notify(open_id, owner, lines, auto=False):
        captured["open_id"] = open_id
        captured["owner"] = owner
        captured["auto"] = auto
        captured["lines"] = lines
        return True

    monkeypatch.setattr(
        "backend.services.project_followup_service.NotificationService.notify_owner_followup",
        fake_notify)
    res = asyncio.run(ProjectFollowupService.send_owner_followup(db_session, "申华", auto=True))
    assert res["sent"] is True
    assert captured["open_id"] == "ou_shen"
    assert captured["auto"] is True
    assert captured["lines"]


def test_run_auto_all_skips_unresolvable(db_session, monkeypatch):
    _mk_user(db_session, "申华", feishu_id="ou_shen")
    _mk_project(db_session, "P1", "申华", progress_log=[{"time": OLD, "content": "x", "status": "正常", "id": "a"}])
    _mk_project(db_session, "P2", "无账号", progress_log=[{"time": OLD, "content": "x", "status": "正常", "id": "b"}])
    sent_to = []

    async def fake_notify(open_id, owner, lines, auto=False):
        sent_to.append(owner)
        return True

    monkeypatch.setattr(
        "backend.services.project_followup_service.NotificationService.notify_owner_followup",
        fake_notify)
    n = asyncio.run(ProjectFollowupService.run_auto_followup_all(db_session, auto=True))
    assert n == 1
    assert sent_to == ["申华"]


def test_send_owner_logs_manual(db_session, monkeypatch):
    """手动催办成功后写日志，操作人=触发管理员。"""
    from backend.models.operation_log import OperationLog
    admin = _mk_user(db_session, "管理员", feishu_id="ou_admin")
    admin.role = UserRole.ADMIN
    _mk_user(db_session, "申华", feishu_id="ou_shen")
    _mk_project(db_session, "P", "申华", progress_log=[{"time": OLD, "content": "x", "status": "正常", "id": "a"}])

    async def fake_notify(*a, **k):
        return True
    monkeypatch.setattr(
        "backend.services.project_followup_service.NotificationService.notify_owner_followup",
        fake_notify)
    asyncio.run(ProjectFollowupService.send_owner_followup(db_session, "申华", auto=False, operator=admin))
    rows = db_session.query(OperationLog).filter(OperationLog.action == "followup").all()
    assert len(rows) == 1
    assert rows[0].user_name == "管理员"
    assert rows[0].target == "申华"
    assert "手动催办" in rows[0].description


def test_send_owner_logs_auto_system(db_session, monkeypatch):
    """自动催办成功后写日志，操作人=系统。"""
    from backend.models.operation_log import OperationLog
    _mk_user(db_session, "申华", feishu_id="ou_shen")
    _mk_project(db_session, "P", "申华", progress_log=[{"time": OLD, "content": "x", "status": "正常", "id": "a"}])

    async def fake_notify(*a, **k):
        return True
    monkeypatch.setattr(
        "backend.services.project_followup_service.NotificationService.notify_owner_followup",
        fake_notify)
    asyncio.run(ProjectFollowupService.send_owner_followup(db_session, "申华", auto=True))
    rows = db_session.query(OperationLog).filter(OperationLog.action == "followup").all()
    assert len(rows) == 1
    assert rows[0].user_name == "系统"
    assert "自动催办" in rows[0].description


def test_unresolved_not_logged(db_session):
    """未发送（未关联账号）不写日志。"""
    from backend.models.operation_log import OperationLog
    _mk_project(db_session, "P", "无账号人", progress_log=[{"time": OLD, "content": "x", "status": "正常", "id": "a"}])
    asyncio.run(ProjectFollowupService.send_owner_followup(db_session, "无账号人"))
    assert db_session.query(OperationLog).filter(OperationLog.action == "followup").count() == 0
