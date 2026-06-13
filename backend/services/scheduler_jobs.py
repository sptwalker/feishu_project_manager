"""定时任务作业

每个作业自管理数据库会话，调用提醒/报表服务。作业为 async 函数，
可被 APScheduler 调度，也可在测试中直接 await 调用。
作业内部捕获异常并记录日志，避免单次失败影响调度器。
"""
import logging
from backend.db.session import SessionLocal
from backend.services.reminder_service import ReminderService
from backend.services.report_service import ReportService
from backend.services.project_followup_service import ProjectFollowupService
from backend.services.auto_meeting_service import AutoMeetingService
from backend.services.meeting_reminder_service import MeetingReminderService
from backend.services.followup_auto_service import FollowupAutoService

logger = logging.getLogger(__name__)


async def _run_with_session(coro_factory, job_name: str) -> int:
    """打开会话执行作业，统一异常处理，返回发送条数"""
    db = SessionLocal()
    try:
        result = await coro_factory(db)
        logger.info(f"Scheduled job '{job_name}' sent {result} notification(s)")
        return result if isinstance(result, int) else (1 if result else 0)
    except Exception as e:  # noqa: BLE001 - 调度作业需吞掉异常保证调度器存活
        logger.exception(f"Scheduled job '{job_name}' failed: {e}")
        return 0
    finally:
        db.close()


async def job_overdue_task_reminders() -> int:
    return await _run_with_session(ReminderService.send_overdue_task_reminders, "overdue_task_reminders")


async def job_due_soon_reminders() -> int:
    return await _run_with_session(ReminderService.send_due_soon_reminders, "due_soon_reminders")


async def job_progress_followups() -> int:
    return await _run_with_session(ReminderService.send_progress_followups, "progress_followups")


async def job_milestone_reminders() -> int:
    return await _run_with_session(ReminderService.send_milestone_reminders, "milestone_reminders")


async def job_weekly_report() -> int:
    return await _run_with_session(ReportService.send_weekly_report, "weekly_report")


async def job_project_followups() -> int:
    return await _run_with_session(ProjectFollowupService.send_project_followups, "project_followups")


async def job_auto_open_meeting() -> int:
    """每周四自动开启周会（工作日判断 + 开启 + 发群通知）"""
    return await _run_with_session(AutoMeetingService.auto_open_if_due, "auto_open_meeting")


async def job_meeting_reminder_one() -> int:
    """周会自动催更①（每周五）：进展更新条数排名前三 + （如配置）跟随周会的个人催办"""
    return await _run_with_session(
        lambda db: _meeting_reminder_with_follow(db, "one"), "meeting_reminder_one")


async def job_meeting_reminder_two() -> int:
    """周会自动催更②（每周日）：待更新数量排名前三 + （如配置）跟随周会的个人催办"""
    return await _run_with_session(
        lambda db: _meeting_reminder_with_follow(db, "two"), "meeting_reminder_two")


async def _meeting_reminder_with_follow(db, which: str) -> int:
    """先发周会群催更，再按「跟随周会催更」配置向负责人私聊催办（仅周会进行中）。"""
    from backend.services.settings_service import SettingsService
    from backend.services.project_followup_service import ProjectFollowupService
    if which == "one":
        sent = await MeetingReminderService.send_reminder_one(db)
    else:
        sent = await MeetingReminderService.send_reminder_two(db)
    extra = 0
    cfg = SettingsService.get_followup_auto(db)
    if (cfg.get("enabled") and cfg.get("mode") == "follow_meeting"
            and which in (cfg.get("follow") or [])
            and SettingsService.get_active_meeting_record(db) is not None):
        extra = await ProjectFollowupService.run_auto_followup_all(db, auto=True)
    return (1 if sent else 0) + extra


async def job_followup_auto_tick() -> int:
    """每分钟检查自动定时催办配置（weekly/fixed_days），到点则向负责人私聊催办"""
    return await _run_with_session(FollowupAutoService.tick, "followup_auto_tick")
