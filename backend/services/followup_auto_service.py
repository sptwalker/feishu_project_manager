"""自动定时催办服务

按 DB 配置（followup_auto）在到点时自动向所有需催办的负责人私聊催办。
- weekly：每周指定星期 + 时间
- fixed_days：距上次满 N 天 + 时间
- follow_meeting：跟随周会催更（由 job_meeting_reminder_one/two 调用，不走 tick）

tick 每分钟调用一次：due_now 命中即 run_auto_followup_all 并写 last_run_date 防当天重复。
真实外发受 FEISHU_NOTIFY_ENABLED 控制（在 NotificationService 内）。
"""
import logging
from datetime import datetime, date
from typing import Optional

from sqlalchemy.orm import Session

from backend.services.settings_service import SettingsService
from backend.services.project_followup_service import ProjectFollowupService

logger = logging.getLogger(__name__)


def due_now(cfg: dict, now: datetime, last_run: Optional[date]) -> bool:
    """判断当前时刻是否应触发自动催办（weekly / fixed_days）。follow_meeting 始终返回 False。"""
    if not cfg.get("enabled"):
        return False
    mode = cfg.get("mode")
    if mode == "follow_meeting":
        return False
    # 当天已跑过则不重复
    if last_run is not None and last_run == now.date():
        return False
    # 时间点匹配到分钟
    hhmm = (cfg.get("time") or "").strip()
    if hhmm != now.strftime("%H:%M"):
        return False
    if mode == "weekly":
        return int(cfg.get("weekday", 0)) == now.weekday()
    if mode == "fixed_days":
        interval = int(cfg.get("interval_days", 7))
        if last_run is None:
            return True  # 从未跑过，到点即触发并记锚点
        return (now.date() - last_run).days >= interval
    return False


class FollowupAutoService:
    """自动定时催办调度"""

    @staticmethod
    def _parse_last_run(cfg: dict) -> Optional[date]:
        raw = (cfg.get("last_run_date") or "").strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None

    @staticmethod
    async def tick(db: Session, now: Optional[datetime] = None) -> int:
        """每分钟调度入口：到点则向所有可解析负责人自动催办，返回成功条数。"""
        now = now or datetime.now()
        cfg = SettingsService.get_followup_auto(db)
        last_run = FollowupAutoService._parse_last_run(cfg)
        if not due_now(cfg, now, last_run):
            return 0
        # 先写 last_run_date 防重复（即使本轮无人可催也算今天已执行，避免每分钟重试）
        cfg["last_run_date"] = now.date().isoformat()
        SettingsService.set_followup_auto(db, cfg)
        sent = await ProjectFollowupService.run_auto_followup_all(db, auto=True, now=now)
        logger.info("followup_auto tick fired: sent=%s mode=%s", sent, cfg.get("mode"))
        return sent
