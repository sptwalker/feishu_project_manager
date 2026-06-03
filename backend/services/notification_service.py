"""飞书消息通知服务

高层通知封装。所有发送都受配置开关 FEISHU_NOTIFY_ENABLED 控制：
关闭时（默认）所有方法为无操作（no-op），开发与测试期间不会真实外发。
方法仅接收原始值（而非 ORM 对象），以便在请求结束、数据库会话关闭后的
后台任务中安全执行。
"""
import logging
from typing import Optional, List, Dict, Any
from backend.core.config import get_settings
from backend.core.feishu import feishu_client, FeishuAPIError
from backend.utils import feishu_cards

logger = logging.getLogger(__name__)


class NotificationService:
    """飞书通知服务"""

    @staticmethod
    def _enabled() -> bool:
        return bool(get_settings().FEISHU_NOTIFY_ENABLED)

    @staticmethod
    async def _send_card(receive_id: Optional[str], card: dict,
                         receive_id_type: str = "user_id") -> bool:
        """发送卡片，返回是否实际发送。受开关与 receive_id 有效性保护。"""
        if not NotificationService._enabled():
            logger.debug("Feishu notify disabled; skip sending card")
            return False
        if not receive_id:
            logger.debug("No receive_id; skip sending card")
            return False
        try:
            await feishu_client.send_card(receive_id, card, receive_id_type=receive_id_type)
            return True
        except FeishuAPIError as e:
            # 通知为尽力而为，失败不应影响主流程
            logger.warning(f"Failed to send Feishu card: {e}")
            return False

    @staticmethod
    async def notify_task_status_change(
        receive_id: Optional[str],
        task_name: str,
        old_status: str,
        new_status: str,
        operator_name: str = "系统",
        project_name: str = "",
    ) -> bool:
        """任务状态变更通知"""
        card = feishu_cards.build_task_status_card(
            task_name, old_status, new_status, operator_name, project_name
        )
        return await NotificationService._send_card(receive_id, card)

    @staticmethod
    async def notify_risk_change(
        receive_id: Optional[str],
        risk_title: str,
        old_status: str,
        new_status: str,
        operator_name: str = "系统",
        project_name: str = "",
    ) -> bool:
        """风险状态变更通知"""
        card = feishu_cards.build_risk_card(
            risk_title, old_status, new_status, operator_name, project_name
        )
        return await NotificationService._send_card(receive_id, card)

    @staticmethod
    async def notify_reminder(
        receive_id: Optional[str],
        title: str,
        lines: list,
        urgent: bool = False,
    ) -> bool:
        """通用提醒通知（逾期/临期/里程碑/进度跟催/周报）"""
        card = feishu_cards.build_reminder_card(title, lines, urgent)
        return await NotificationService._send_card(receive_id, card)

    @staticmethod
    async def notify_project_followups(
        chat_id: Optional[str],
        items: List[Dict[str, Any]],
    ) -> bool:
        """项目进展催办（发送到群）。items 见 build_project_followup_card。"""
        if not items:
            return False
        frontend_url = get_settings().FRONTEND_URL or ""
        card = feishu_cards.build_project_followup_card(items, frontend_url)
        return await NotificationService._send_card(chat_id, card, receive_id_type="chat_id")

    @staticmethod
    async def notify_meeting_doc(
        chat_id: Optional[str],
        session: int,
        meeting_date: str,
        recorder: str,
        doc_url: str,
    ) -> bool:
        """周会纪要分享（发送到核心组群），含飞书文档链接。"""
        card = feishu_cards.build_meeting_doc_card(session, meeting_date, recorder or "", doc_url)
        return await NotificationService._send_card(chat_id, card, receive_id_type="chat_id")

    @staticmethod
    async def notify_meeting_open(
        chat_id: Optional[str],
        session: int,
        public_url: str,
        operator: Optional[str] = None,
    ) -> bool:
        """周会模式开启通知（发送到核心组群）。operator=None 为系统自动开启，有值为管理员手动开启。"""
        card = feishu_cards.build_meeting_open_card(session, public_url, operator)
        return await NotificationService._send_card(chat_id, card, receive_id_type="chat_id")
