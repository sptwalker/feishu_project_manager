import asyncio
import pytest
from unittest.mock import AsyncMock
from backend.core.config import get_settings
from backend.core import scheduler as sched
from backend.services import scheduler_jobs


def test_scheduler_disabled_by_default(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "SCHEDULER_ENABLED", False)
    result = sched.start_scheduler()
    assert result is None
    assert sched.get_scheduler() is None


def test_scheduler_starts_when_enabled(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "SCHEDULER_ENABLED", True)

    async def _run():
        # AsyncIOScheduler 需在运行中的事件循环内启动（与 FastAPI lifespan 一致）
        scheduler = sched.start_scheduler()
        assert scheduler is not None
        assert scheduler.running
        job_ids = {j.id for j in scheduler.get_jobs()}
        assert job_ids == {
            "overdue_task_reminders", "due_soon_reminders",
            "milestone_reminders", "progress_followups", "weekly_report",
            "project_followups",
        }
        sched.shutdown_scheduler()

    try:
        asyncio.run(_run())
        assert sched.get_scheduler() is None
    finally:
        sched.shutdown_scheduler()


def test_job_swallows_exceptions(monkeypatch):
    """作业内部异常应被吞掉并返回 0，不向上抛出"""
    async def boom(db):
        raise RuntimeError("db error")

    monkeypatch.setattr(
        "backend.services.scheduler_jobs.ReminderService.send_overdue_task_reminders",
        boom,
    )
    result = asyncio.run(scheduler_jobs.job_overdue_task_reminders())
    assert result == 0
