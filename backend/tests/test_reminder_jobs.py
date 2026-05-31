import asyncio
import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.models.project import Project, ProjectStatus
from backend.models.task import Task, TaskStatus
from backend.models.risk import Risk, RiskStatus
from backend.core.config import get_settings
from backend.services.reminder_service import ReminderService
from backend.services.report_service import ReportService
from backend.services import notification_service as ns

RECEIVER = "report_receiver_open_id"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def enable_notify():
    """开启通知并配置接收人（提醒统一发给配置接收人，不再定向到负责人个人）"""
    s = get_settings()
    old_enabled, old_recv = s.FEISHU_NOTIFY_ENABLED, s.FEISHU_REPORT_RECEIVER_ID
    s.FEISHU_NOTIFY_ENABLED = True
    s.FEISHU_REPORT_RECEIVER_ID = RECEIVER
    yield
    s.FEISHU_NOTIFY_ENABLED = old_enabled
    s.FEISHU_REPORT_RECEIVER_ID = old_recv


TODAY = date(2026, 6, 1)


def _project(db, **kw):
    p = Project(name=kw.pop("name", "P"), record_date=date(2026, 5, 1), **kw)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_send_overdue_reminders_sends_to_receiver(db_session, enable_notify, monkeypatch):
    mock = AsyncMock(return_value={"message_id": "m"})
    monkeypatch.setattr(ns.feishu_client, "send_card", mock)

    project = _project(db_session, owner_name="张三")
    db_session.add(Task(project_id=project.id, name="逾期", owner_name="张三",
                        due_date=date(2026, 5, 20), status=TaskStatus.IN_PROGRESS))
    db_session.commit()

    sent = asyncio.run(ReminderService.send_overdue_task_reminders(db_session, TODAY))
    assert sent == 1
    mock.assert_awaited_once()
    args, _ = mock.call_args
    assert args[0] == RECEIVER  # 统一发送给配置的接收人


def test_send_overdue_reminders_disabled_sends_nothing(db_session, monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(ns.feishu_client, "send_card", mock)

    project = _project(db_session, owner_name="张三")
    db_session.add(Task(project_id=project.id, name="逾期", owner_name="张三",
                        due_date=date(2026, 5, 20), status=TaskStatus.IN_PROGRESS))
    db_session.commit()

    # 未启用 FEISHU_NOTIFY_ENABLED -> no-op
    sent = asyncio.run(ReminderService.send_overdue_task_reminders(db_session, TODAY))
    assert sent == 0
    mock.assert_not_called()


def test_build_weekly_summary(db_session):
    p = _project(db_session, owner_name="张三", status=ProjectStatus.IN_PROGRESS)
    db_session.add_all([
        Task(project_id=p.id, name="t1", owner_name="张三", status=TaskStatus.PENDING),
        Task(project_id=p.id, name="t2", owner_name="张三", status=TaskStatus.COMPLETED),
        Risk(project_id=p.id, title="r1", status=RiskStatus.OPEN),
    ])
    db_session.commit()

    s = ReportService.build_weekly_summary(db_session)
    assert s["project_total"] == 1
    assert s["project_in_progress"] == 1
    assert s["task_total"] == 2
    assert s["task_completed"] == 1
    assert s["risk_open"] == 1


def test_send_weekly_report_no_receiver_is_noop(db_session, enable_notify, monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(ns.feishu_client, "send_card", mock)
    sent = asyncio.run(ReportService.send_weekly_report(db_session, receiver_id=""))
    assert sent is False
    mock.assert_not_called()


def test_send_weekly_report_with_receiver(db_session, enable_notify, monkeypatch):
    mock = AsyncMock(return_value={"message_id": "m"})
    monkeypatch.setattr(ns.feishu_client, "send_card", mock)
    sent = asyncio.run(ReportService.send_weekly_report(db_session, receiver_id="admin_feishu"))
    assert sent is True
    mock.assert_awaited_once()
    args, _ = mock.call_args
    assert args[0] == "admin_feishu"
