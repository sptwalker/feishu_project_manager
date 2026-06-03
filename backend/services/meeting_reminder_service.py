"""周会自动催更服务

周会模式开启后，定时（每周五/周日 14:00）在飞书核心群发进展更新催办：
- 催更①（周五）：鼓励式，公布"周会模式开启后进展更新条数"前三的负责人。
- 催更②（周日，会议前一天）：敦促式，公布"待更新"前三的负责人及其待更新项目数。

受 AUTO_REMINDER_ENABLED（运行时 DB 开关）+ 存在 active 周会 + 核心群已配置
三重守卫；真实外发再受 FEISHU_NOTIFY_ENABLED 保护。
"""
import logging
from datetime import date, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.models.project import Project, ProjectStatus
from backend.models.meeting_record import MeetingRecord
from backend.services.settings_service import SettingsService
from backend.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def _join_top(names: List[str]) -> str:
    """把前几名拼成"A，B和C"；空时返回"暂无"。"""
    names = [n for n in names if n]
    if not names:
        return "暂无"
    if len(names) == 1:
        return names[0]
    return "，".join(names[:-1]) + "和" + names[-1]


def _join_top_with_count(items: List[Tuple[str, int]]) -> str:
    """把前几名拼成"A（3条），B（2条）和C（1条）"；空时返回"暂无"。"""
    parts = [f"{n}（{c}条）" for n, c in items if n]
    if not parts:
        return "暂无"
    if len(parts) == 1:
        return parts[0]
    return "，".join(parts[:-1]) + "和" + parts[-1]


class MeetingReminderService:
    """周会自动催更"""

    # ---------- 排名口径 ----------

    @staticmethod
    def rank_update_counts(db: Session, session: int, top: int = 3) -> List[Tuple[str, int]]:
        """催更①：统计各项目 progress_log 中 meeting_session==session 的条目数，
        按 owner_name 分组求和，降序取前 top。空 owner 跳过。"""
        counts: dict[str, int] = {}
        for p in db.query(Project).all():
            owner = (p.owner_name or "").strip()
            if not owner:
                continue
            n = sum(
                1 for e in (p.progress_log or [])
                if isinstance(e, dict) and e.get("meeting_session") == session
            )
            if n:
                counts[owner] = counts.get(owner, 0) + n
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return ranked[:top]

    @staticmethod
    def rank_pending_counts(db: Session, anchor_date: date, top: int = 3) -> List[Tuple[str, int]]:
        """催更②：对 in_progress 项目，若其 progress_log 中无任何 time 日期 > anchor_date
        的条目，则计为该负责人一个"待更新项目"。按 owner 分组计项目数，降序取前 top。"""
        anchor_str = anchor_date.isoformat()  # 'YYYY-MM-DD'
        counts: dict[str, int] = {}
        in_progress = db.query(Project).filter(Project.status == ProjectStatus.IN_PROGRESS).all()
        for p in in_progress:
            owner = (p.owner_name or "").strip()
            if not owner:
                continue
            updated = any(
                isinstance(e, dict) and (e.get("time") or "")[:10] > anchor_str
                for e in (p.progress_log or [])
            )
            if not updated:
                counts[owner] = counts.get(owner, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return ranked[:top]

    @staticmethod
    def _anchor_date(db: Session, active: MeetingRecord) -> date:
        """上一次周会日期：meeting_records 中 session < 当前session 的最大者的 meeting_date，
        无则回退为 当前会议日期 - 7 天。"""
        prev = (
            db.query(MeetingRecord)
            .filter(MeetingRecord.session < active.session)
            .order_by(MeetingRecord.session.desc())
            .first()
        )
        if prev and prev.meeting_date:
            return prev.meeting_date
        return active.meeting_date - timedelta(days=7)

    # ---------- 发送编排 ----------

    @staticmethod
    def _guard(db: Session) -> Optional[Tuple[MeetingRecord, str]]:
        """三重守卫：催更开关开 + 存在 active 周会 + 核心群已配置。
        通过则返回 (active_record, chat_id)，否则 None。"""
        if not SettingsService.get_auto_reminder_enabled(db):
            logger.info("auto_reminder 跳过：运行时开关已关闭")
            return None
        active = SettingsService.get_active_meeting_record(db)
        if not active:
            logger.info("auto_reminder 跳过：当前无进行中的周会")
            return None
        chat_id = SettingsService.get_core_group_chat_id(db)
        if not chat_id:
            logger.info("auto_reminder 跳过：核心群 chat_id 未配置")
            return None
        return active, chat_id

    @staticmethod
    async def send_reminder_one(db: Session) -> bool:
        """催更①（周五）：进展更新条数排名前三。返回是否发送。"""
        guarded = MeetingReminderService._guard(db)
        if not guarded:
            return False
        active, chat_id = guarded
        url = get_settings().SYSTEM_PUBLIC_URL
        ranked = MeetingReminderService.rank_update_counts(db, active.session)
        top_str = _join_top([n for n, _ in ranked])
        body = (
            f"请注意：核心项目管理系统的周会模式开启中，请各部门和项目负责人及时登录{url}"
            f"更新自己负责项目的最新进展信息。目前项目进展更新数量排名前三名为：{top_str}，值得鼓励！"
        )
        return await NotificationService.notify_meeting_reminder(chat_id, active.session, body)

    @staticmethod
    async def send_reminder_two(db: Session) -> bool:
        """催更②（周日）：待更新数量排名前三。返回是否发送。"""
        guarded = MeetingReminderService._guard(db)
        if not guarded:
            return False
        active, chat_id = guarded
        url = get_settings().SYSTEM_PUBLIC_URL
        anchor = MeetingReminderService._anchor_date(db, active)
        ranked = MeetingReminderService.rank_pending_counts(db, anchor)
        top_str = _join_top_with_count(ranked)
        body = (
            f"请注意：核心项目管理系统的周会模式开启中，明天将召开周例会，请各部门和项目负责人及时登录{url}"
            f"更新自己负责项目的最新进展信息。目前项目进展待更新数量排名前三名为：{top_str}，请加油！"
        )
        return await NotificationService.notify_meeting_reminder(chat_id, active.session, body)
