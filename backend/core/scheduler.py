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
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from backend.core.config import get_settings
from backend.services import scheduler_jobs

logger = logging.getLogger(__name__)

# 全局调度器实例
_scheduler: Optional[AsyncIOScheduler] = None


def _job_event_listener(event) -> None:
    """定时任务事件监听：记录每个任务的执行/错过(misfire)/异常，确保不遗漏错失。"""
    if event.code == EVENT_JOB_MISSED:
        # 错过触发（如容器在触发时刻不可用）。配合 misfire_grace_time，宽限期内仍会补跑；
        # 超过宽限期才会真正丢失，这里 warning 留痕便于追溯。
        logger.warning("定时任务 [%s] 错过触发（misfire），计划时间=%s", event.job_id, event.scheduled_run_time)
    elif event.code == EVENT_JOB_ERROR:
        logger.error("定时任务 [%s] 执行异常: %s", event.job_id, event.exception)
    else:  # EVENT_JOB_EXECUTED
        logger.info("定时任务 [%s] 执行完成，计划时间=%s，返回=%s",
                    event.job_id, event.scheduled_run_time, event.retval)


def _build_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    # 显式用 ZoneInfo 作为时区：APScheduler 3.x 下 CronTrigger 不显式带 timezone 时会回退到
    # 容器本地时区(UTC)，导致 hour=14 实际按 UTC 触发(=北京 22:00)。故所有 trigger 统一带此 tz。
    tz = ZoneInfo(settings.TIMEZONE)

    def _cron(**kw) -> CronTrigger:
        return CronTrigger(timezone=tz, **kw)

    # 全局防漏：coalesce 合并堆积的多次触发为一次；misfire_grace_time 给错过的任务补执行宽限期。
    # 对所有 job 生效（常规提醒/跟催/周报 + 周会自动开启/催更）。
    scheduler = AsyncIOScheduler(
        timezone=tz,
        job_defaults={
            "coalesce": True,
            "misfire_grace_time": settings.SCHEDULER_MISFIRE_GRACE_TIME,
        },
    )
    # 注册事件监听器：每次执行/错过/异常都留日志，确保不遗漏错失
    scheduler.add_listener(
        _job_event_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
    )

    # 自动定时催办 tick：无条件注册（只要调度器在跑就存在），每分钟检查 DB 配置是否到点。
    # 运行时由 followup_auto.enabled + due_now 守卫控制是否真正发送，改配置即时生效无需重启。
    scheduler.add_job(
        scheduler_jobs.job_followup_auto_tick,
        _cron(minute="*"),
        id="followup_auto_tick", replace_existing=True,
    )

    # 常规提醒/跟催/周报作业：受 SCHEDULER_ENABLED 控制
    if settings.SCHEDULER_ENABLED:
        scheduler.add_job(
            scheduler_jobs.job_overdue_task_reminders,
            _cron(hour=settings.REMINDER_HOUR, minute=0),
            id="overdue_task_reminders", replace_existing=True,
        )
        scheduler.add_job(
            scheduler_jobs.job_due_soon_reminders,
            _cron(hour=settings.REMINDER_HOUR, minute=5),
            id="due_soon_reminders", replace_existing=True,
        )
        scheduler.add_job(
            scheduler_jobs.job_milestone_reminders,
            _cron(hour=settings.REMINDER_HOUR, minute=10),
            id="milestone_reminders", replace_existing=True,
        )
        scheduler.add_job(
            scheduler_jobs.job_progress_followups,
            _cron(hour=settings.FOLLOWUP_HOUR, minute=0),
            id="progress_followups", replace_existing=True,
        )
        scheduler.add_job(
            scheduler_jobs.job_weekly_report,
            _cron(day_of_week=settings.WEEKLY_REPORT_DAY,
                  hour=settings.WEEKLY_REPORT_HOUR, minute=0),
            id="weekly_report", replace_existing=True,
        )
        scheduler.add_job(
            scheduler_jobs.job_project_followups,
            _cron(hour=settings.PROJECT_FOLLOWUP_HOUR,
                  minute=settings.PROJECT_FOLLOWUP_MINUTE),
            id="project_followups", replace_existing=True,
        )

    # 周会定时自动开启：独立开关，与上面互不依赖
    if settings.AUTO_OPEN_MEETING_ENABLED:
        scheduler.add_job(
            scheduler_jobs.job_auto_open_meeting,
            _cron(day_of_week=settings.AUTO_MEETING_DAY,
                  hour=settings.AUTO_MEETING_HOUR,
                  minute=settings.AUTO_MEETING_MINUTE),
            id="auto_open_meeting", replace_existing=True,
        )
        # 周会自动催更①/②（每周五/周日 14:00）；运行时由 DB 开关 + active 守卫控制是否真发
        scheduler.add_job(
            scheduler_jobs.job_meeting_reminder_one,
            _cron(day_of_week=settings.AUTO_REMINDER1_DAY,
                  hour=settings.AUTO_REMINDER_HOUR,
                  minute=settings.AUTO_REMINDER_MINUTE),
            id="meeting_reminder_one", replace_existing=True,
        )
        scheduler.add_job(
            scheduler_jobs.job_meeting_reminder_two,
            _cron(day_of_week=settings.AUTO_REMINDER2_DAY,
                  hour=settings.AUTO_REMINDER_HOUR,
                  minute=settings.AUTO_REMINDER_MINUTE),
            id="meeting_reminder_two", replace_existing=True,
        )
    return scheduler


def start_scheduler() -> Optional[AsyncIOScheduler]:
    """启动调度器（SCHEDULER_ENABLED 或 AUTO_OPEN_MEETING_ENABLED 任一开启即启动）。返回实例或 None。"""
    global _scheduler
    settings = get_settings()
    if not (settings.SCHEDULER_ENABLED or settings.AUTO_OPEN_MEETING_ENABLED):
        logger.info("Scheduler disabled (both SCHEDULER_ENABLED and AUTO_OPEN_MEETING_ENABLED are False); not starting")
        return None
    if _scheduler is not None and _scheduler.running:
        return _scheduler
    _scheduler = _build_scheduler()
    _scheduler.start()
    jobs = _scheduler.get_jobs()
    logger.info("Scheduler started with %d job(s)", len(jobs))
    # 逐个打印下次触发时间，启动即可确认所有定时任务的调度计划
    for j in jobs:
        logger.info("  · 定时任务 [%s] 下次触发=%s", j.id, j.next_run_time)
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
