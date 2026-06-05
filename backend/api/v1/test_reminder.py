"""【临时测试】测试催更 + 催更链路诊断端点

用途：在「系统设置 › 其他设置」用按钮操作，无需命令行即可排查催更为何不发：
- POST /settings/test-reminder ：安排约3分钟后执行一次真实催更，并把执行结果(含守卫/飞书直发错误)记录到 DB
- GET  /settings/diagnostics   ：一键返回完整诊断报告文本(服务器时间/调度器各任务触发时区/4守卫/最近测试结果)，前端展示到文本框供复制

⚠️ 临时测试代码，验证完成后请删除本文件及 main.py 中对应的 import 与路由注册。
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

TEST_REMINDER_DELAY_MIN = 3
LAST_RESULT_KEY = "last_test_reminder_result"   # 最近一次测试催更结果（存 DB 供诊断读取）


async def _run_test_reminder() -> None:
    """一次性测试催更：跑真实催更①，并尝试一次飞书直发(捕获真实错误)，结果写入 DB 供 UI 诊断查看。"""
    db = SessionLocal()
    try:
        s = get_settings()
        tz = ZoneInfo(s.TIMEZONE)
        ts = datetime.now(tz).strftime("%m-%d %H:%M:%S")
        parts = []

        # 1. 守卫快照
        ar = SettingsService.get_auto_reminder_enabled(db)
        active = SettingsService.get_active_meeting_record(db)
        chat = SettingsService.get_core_group_chat_id(db)
        notify = bool(s.FEISHU_NOTIFY_ENABLED)
        parts.append(
            f"守卫[催更开关={ar} active周会={bool(active)} chat_id={'有' if chat else '无'} 通知={notify}]"
        )

        # 2. 真实催更逻辑（带守卫，与定时任务完全一致）
        try:
            sent = await MeetingReminderService.send_reminder_one(db)
            parts.append(f"真实催更 sent={sent}（True=已发群 / False=被守卫拦截或通知关闭）")
        except Exception as e:
            parts.append(f"真实催更异常={e}")

        # 3. 飞书直发测试：绕过守卫，直接发一条测试消息到核心群，捕获飞书 API 的真实错误
        if chat and notify:
            try:
                from backend.core.feishu import feishu_client
                await feishu_client.send_message(
                    chat, "text",
                    {"text": "【催更诊断】这是一条测试消息，用于验证机器人能否发到本群，请忽略。"},
                    receive_id_type="chat_id",
                )
                parts.append("飞书直发测试=成功（群应已收到测试消息）")
            except Exception as fe:
                parts.append(f"飞书直发测试=失败：{fe}")
        else:
            parts.append("飞书直发测试=跳过（chat_id未配置或通知关闭）")

        result = f"[{ts}] " + " | ".join(parts)
        SettingsService.set_setting(db, LAST_RESULT_KEY, result)
        logger.info("【测试催更】%s", result)
    except Exception as e:
        logger.exception("【测试催更】执行异常: %s", e)
        try:
            SettingsService.set_setting(db, LAST_RESULT_KEY, f"执行异常: {e}")
        except Exception:
            pass
    finally:
        db.close()


@router.post("/settings/test-reminder")
def schedule_test_reminder(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """【临时】安排一次性测试催更（约3分钟后执行），返回当前守卫状态。"""
    s = get_settings()
    sch = get_scheduler()
    if sch is None:
        raise HTTPException(
            status_code=503,
            detail="调度器未启动：需 .env 设 AUTO_OPEN_MEETING_ENABLED=True 或 SCHEDULER_ENABLED=True",
        )
    tz = ZoneInfo(s.TIMEZONE)
    run_at = datetime.now(tz) + timedelta(minutes=TEST_REMINDER_DELAY_MIN)
    sch.add_job(
        _run_test_reminder,
        DateTrigger(run_date=run_at),
        id="test_meeting_reminder", replace_existing=True,
    )
    SettingsService.set_setting(db, LAST_RESULT_KEY, f"已安排，等待 {run_at:%H:%M:%S} 执行 ...")
    logger.info("【测试催更】已安排，将于 %s 执行", run_at.strftime("%Y-%m-%d %H:%M:%S %Z"))

    guards = {
        "auto_reminder_enabled": SettingsService.get_auto_reminder_enabled(db),
        "active_meeting": bool(SettingsService.get_active_meeting_record(db)),
        "core_chat_id_configured": bool(SettingsService.get_core_group_chat_id(db)),
        "feishu_notify_enabled": bool(s.FEISHU_NOTIFY_ENABLED),
    }
    return {
        "ok": True,
        "run_at": run_at.strftime("%Y-%m-%d %H:%M:%S"),
        "delay_min": TEST_REMINDER_DELAY_MIN,
        "guards": guards,
        "message": f"测试催更已安排，约 {run_at:%H:%M:%S}（{s.TIMEZONE}）执行，3分钟后点「获取诊断信息」查看结果",
    }


@router.get("/settings/diagnostics")
def diagnostics(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """【临时】一键催更链路诊断，返回可复制的报告文本。"""
    s = get_settings()
    tz = ZoneInfo(s.TIMEZONE)
    now = datetime.now(tz)
    sch = get_scheduler()

    L = []
    L.append("========== 催更链路诊断 ==========")
    L.append(f"服务器当前时间: {now:%Y-%m-%d %H:%M:%S} ({s.TIMEZONE})")
    L.append("")
    L.append("[配置 .env]")
    L.append(f"  AUTO_OPEN_MEETING_ENABLED = {s.AUTO_OPEN_MEETING_ENABLED}  (决定调度器是否启动并注册催更任务)")
    L.append(f"  FEISHU_NOTIFY_ENABLED     = {s.FEISHU_NOTIFY_ENABLED}  (飞书真实外发总开关)")
    L.append(f"  TIMEZONE                  = {s.TIMEZONE}")
    L.append("")
    L.append("[调度器]")
    if sch is None:
        L.append("  ✗ 调度器未启动！(AUTO_OPEN_MEETING_ENABLED 与 SCHEDULER_ENABLED 都为 False)")
    else:
        L.append("  ✓ 运行中，已注册任务及下次触发时间:")
        for j in sch.get_jobs():
            L.append(f"    - {j.id}: {j.next_run_time}")
        L.append("  (催更=meeting_reminder_one/two；下次触发须为 +08:00 北京时间，若是 +00:00 则为时区bug)")
    L.append("")
    L.append("[催更守卫 — 4个全部满足才会真正发送]")
    ar = SettingsService.get_auto_reminder_enabled(db)
    active = SettingsService.get_active_meeting_record(db)
    chat = SettingsService.get_core_group_chat_id(db)
    notify = bool(s.FEISHU_NOTIFY_ENABLED)
    L.append(f"  {'✓' if ar else '✗'} 催更开关(DB auto_reminder) = {ar}")
    if active:
        L.append(f"  ✓ active进行中周会 = True (第{active.session}次, 会议日期{active.meeting_date}, 记录人{active.recorder})")
    else:
        L.append("  ✗ active进行中周会 = False  ← 无进行中周会时催更会跳过")
    L.append(f"  {'✓' if chat else '✗'} 核心群chat_id = {chat or '未配置'}")
    L.append(f"  {'✓' if notify else '✗'} 飞书通知开关 = {notify}")
    L.append("")
    L.append("[最近一次测试催更结果]")
    last = SettingsService.get_setting(db, LAST_RESULT_KEY, "")
    L.append(f"  {last or '(尚无；请先点上方“测试催更”按钮，约3分钟后再点本按钮查看执行结果)'}")
    L.append("==================================")

    return {"report": "\n".join(L)}
