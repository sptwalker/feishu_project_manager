"""【临时测试】测试催更端点

用途：在「系统设置 › 其他设置」点击"测试催更"按钮后，安排一个一次性任务，
约 3 分钟后执行一次真实催更逻辑（MeetingReminderService.send_reminder_one），
用于在外网真实环境验证催更链路（调度器是否工作 / 守卫是否通过 / 能否发到群）。

诊断要点：
- 端点会立即返回当前 4 个守卫状态，点一下即可看出哪个条件不满足；
- 一次性任务用 DateTrigger(now+3min)，不依赖 cron 时区，可隔离"时区问题"；
- 3 分钟后看后端日志（事件监听器 + 本文件日志）确认实际执行结果。

⚠️ 这是临时测试代码，验证完成后请删除本文件及 main.py 中对应的路由注册。
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from apscheduler.triggers.date import DateTrigger

from backend.api.deps import get_db
from backend.core.dependencies import get_current_admin
from backend.core.config import get_settings
from backend.core.scheduler import get_scheduler
from backend.db.session import SessionLocal
from backend.models.user import User
from backend.services.settings_service import SettingsService
from backend.services.meeting_reminder_service import MeetingReminderService

logger = logging.getLogger(__name__)

router = APIRouter()

# 测试任务延迟（分钟）
TEST_REMINDER_DELAY_MIN = 3


async def _run_test_reminder() -> None:
    """一次性测试催更任务：开独立 db 会话执行真实催更①，并记录详细日志。"""
    logger.info("【测试催更】开始执行 ...")
    db = SessionLocal()
    try:
        sent = await MeetingReminderService.send_reminder_one(db)
        logger.info("【测试催更】执行完成：send_reminder_one 返回 sent=%s "
                    "(True=已发群 / False=被守卫拦截或通知关闭，详见上方日志)", sent)
    except Exception as e:
        logger.exception("【测试催更】执行异常: %s", e)
    finally:
        db.close()


@router.post("/settings/test-reminder")
def schedule_test_reminder(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """【临时】安排一次性测试催更（约 N 分钟后执行），并返回当前守卫状态用于诊断。"""
    settings = get_settings()
    sch = get_scheduler()
    if sch is None:
        # 调度器未启动本身就是催更不执行的根因之一（AUTO_OPEN_MEETING_ENABLED/SCHEDULER_ENABLED 都为 False）
        raise HTTPException(
            status_code=503,
            detail="调度器未启动：需 AUTO_OPEN_MEETING_ENABLED 或 SCHEDULER_ENABLED 为 True（.env）",
        )

    tz = ZoneInfo(settings.TIMEZONE)
    run_at = datetime.now(tz) + timedelta(minutes=TEST_REMINDER_DELAY_MIN)
    sch.add_job(
        _run_test_reminder,
        DateTrigger(run_date=run_at),
        id="test_meeting_reminder", replace_existing=True,
    )
    logger.info("【测试催更】已安排，将于 %s 执行", run_at.strftime("%Y-%m-%d %H:%M:%S %Z"))

    # 当前 4 个守卫状态：点一下即可看出哪个条件不满足
    guards = {
        "auto_reminder_enabled": SettingsService.get_auto_reminder_enabled(db),   # 催更运行时开关
        "active_meeting": bool(SettingsService.get_active_meeting_record(db)),     # 是否存在进行中的周会
        "core_chat_id_configured": bool(SettingsService.get_core_group_chat_id(db)),  # 核心群是否配置
        "feishu_notify_enabled": bool(settings.FEISHU_NOTIFY_ENABLED),            # 飞书真实外发总开关
    }
    return {
        "ok": True,
        "run_at": run_at.strftime("%Y-%m-%d %H:%M:%S"),
        "delay_min": TEST_REMINDER_DELAY_MIN,
        "guards": guards,
        "message": f"测试催更已安排，约 {run_at:%H:%M:%S}（{settings.TIMEZONE}）执行，请留意核心群与后端日志",
    }
