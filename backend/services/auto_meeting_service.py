"""周会定时自动开启服务

每周四（工作日）14:00 触发：若周会未开启，则自动开启新周期周会
（记录人默认 Shineleo、会议日期默认下周一），并向飞书核心群发开启通知。
受 AUTO_OPEN_MEETING_ENABLED（调度）与 FEISHU_NOTIFY_ENABLED（通知）双开关保护。
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.services.settings_service import SettingsService
from backend.services.meeting_record_service import MeetingRecordService
from backend.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def _is_workday_safe(d: date) -> bool:
    """判断 d 是否工作日：优先用 chinese_calendar（识别法定节假日/调休）；
    库缺失或年份超出覆盖范围（抛 NotImplementedError）时退化为“周一至周五”。"""
    try:
        from chinese_calendar import is_workday
        return bool(is_workday(d))
    except (NotImplementedError, ImportError) as e:
        logger.warning("chinese_calendar 不可用(%s)，退化为按星期判断工作日：%s", e, d)
        return d.weekday() < 5


class AutoMeetingService:
    """周会定时自动开启"""

    @staticmethod
    async def auto_open_if_due(db: Session, today: Optional[date] = None) -> bool:
        """周四 14:00 调度入口：满足条件则自动开周会并发群通知。返回是否真的开启。"""
        settings = get_settings()
        if today is None:
            # 用配置时区取“今天”，避免服务器 UTC 与北京时间跨日错位
            today = datetime.now(ZoneInfo(settings.TIMEZONE)).date()

        # 1. 非工作日（法定节假日/调休）跳过本轮，不顺延
        if not _is_workday_safe(today):
            logger.info("auto_open_meeting 跳过：%s 非工作日", today)
            return False

        # 2. 运行时开关（系统设置 UI 可控）：关闭则不自动开，改后立即生效无需重启
        if not SettingsService.get_auto_open_meeting_enabled(db):
            logger.info("auto_open_meeting 跳过：运行时开关已关闭")
            return False

        # 3. 已开启周会则不重复开
        state = SettingsService.get_meeting_state(db, today)
        if state["active"]:
            logger.info("auto_open_meeting 跳过：周会已处于开启状态")
            return False

        # 4. 计算新周期次数与会议日期（下周一）
        session = state["next_count"]
        next_monday = today + timedelta(days=(7 - today.weekday()))  # 周四 -> 下周一
        recorder = settings.AUTO_MEETING_RECORDER

        # 5. 开启周会（created_by=None 表示系统自动）
        MeetingRecordService.open_meeting(
            db, session=session, recorder=recorder,
            meeting_date=next_monday, created_by=None,
        )
        logger.info("auto_open_meeting 已开启第 %s 次周会（记录人=%s，会议日期=%s）",
                    session, recorder, next_monday)

        # 6. 发文案A通知到核心群（operator=None 表示系统触发）
        chat_id = SettingsService.get_core_group_chat_id(db)
        await NotificationService.notify_meeting_open(
            chat_id, session=session,
            public_url=settings.SYSTEM_PUBLIC_URL, operator=None,
        )
        return True
