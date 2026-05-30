"""APScheduler 调度器配置

仅在 SCHEDULER_ENABLED=True 时启动后台调度线程，注册以下作业：
- 逾期任务提醒（每天 REMINDER_HOUR:00）
- 临期任务提醒（每天 REMINDER_HOUR:00）
- 里程碑逾期提醒（每天 REMINDER_HOUR:00）
- 进度跟催（每天 FOLLOWUP_HOUR:00）
- 周报（每周 WEEKLY_REPORT_DAY WEEKLY_REPORT_HOUR:00）

作业的实际外发仍受 FEISHU_NOTIFY_ENABLED 控制。
"""
import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.core.config import get_settings
from backend.services import scheduler_jobs

logger = logging.getLogger(__name__)

# 全局调度器实例
_scheduler: Optional[AsyncIOScheduler] = None


def _build_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)

    scheduler.add_job(
        scheduler_jobs.job_overdue_task_reminders,
        CronTrigger(hour=settings.REMINDER_HOUR, minute=0),
        id="overdue_task_reminders", replace_existing=True,
    )
    scheduler.add_job(
        scheduler_jobs.job_due_soon_reminders,
        CronTrigger(hour=settings.REMINDER_HOUR, minute=5),
        id="due_soon_reminders", replace_existing=True,
    )
    scheduler.add_job(
        scheduler_jobs.job_milestone_reminders,
        CronTrigger(hour=settings.REMINDER_HOUR, minute=10),
        id="milestone_reminders", replace_existing=True,
    )
    scheduler.add_job(
        scheduler_jobs.job_progress_followups,
        CronTrigger(hour=settings.FOLLOWUP_HOUR, minute=0),
        id="progress_followups", replace_existing=True,
    )
    scheduler.add_job(
        scheduler_jobs.job_weekly_report,
        CronTrigger(day_of_week=settings.WEEKLY_REPORT_DAY,
                    hour=settings.WEEKLY_REPORT_HOUR, minute=0),
        id="weekly_report", replace_existing=True,
    )
    return scheduler


def start_scheduler() -> Optional[AsyncIOScheduler]:
    """启动调度器（受 SCHEDULER_ENABLED 控制）。返回调度器实例或 None。"""
    global _scheduler
    settings = get_settings()
    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler disabled (SCHEDULER_ENABLED=False); not starting")
        return None
    if _scheduler is not None and _scheduler.running:
        return _scheduler
    _scheduler = _build_scheduler()
    _scheduler.start()
    logger.info("Scheduler started with %d job(s)", len(_scheduler.get_jobs()))
    return _scheduler


def shutdown_scheduler() -> None:
    """关闭调度器"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    _scheduler = None


def get_scheduler() -> Optional[AsyncIOScheduler]:
    return _scheduler
