"""周报生成与推送

汇总系统范围的项目/任务状态，生成简要周报文本，推送给配置的接收人
（FEISHU_REPORT_RECEIVER_ID）。受 FEISHU_NOTIFY_ENABLED 控制。
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.models.task import Task, TaskStatus
from backend.models.project import Project, ProjectStatus
from backend.models.risk import Risk, RiskStatus
from backend.core.config import get_settings
from backend.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ReportService:
    """报表服务"""

    @staticmethod
    def build_weekly_summary(db: Session) -> Dict[str, Any]:
        """构建周报汇总数据（纯统计，便于单测）"""
        projects = db.query(Project).all()
        tasks = db.query(Task).all()
        risks = db.query(Risk).all()

        return {
            "project_total": len(projects),
            "project_in_progress": sum(1 for p in projects if p.status == ProjectStatus.IN_PROGRESS),
            "project_completed": sum(1 for p in projects if p.status == ProjectStatus.COMPLETED),
            "task_total": len(tasks),
            "task_pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
            "task_in_progress": sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS),
            "task_completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "task_blocked": sum(1 for t in tasks if t.status == TaskStatus.BLOCKED),
            "risk_open": sum(1 for r in risks if r.status == RiskStatus.OPEN),
            "risk_monitoring": sum(1 for r in risks if r.status == RiskStatus.MONITORING),
        }

    @staticmethod
    def _summary_lines(s: Dict[str, Any]) -> list:
        return [
            f"**项目**：共 {s['project_total']}，进行中 {s['project_in_progress']}，已完成 {s['project_completed']}",
            f"**任务**：共 {s['task_total']}，待办 {s['task_pending']}，进行中 {s['task_in_progress']}，"
            f"已完成 {s['task_completed']}，阻塞 {s['task_blocked']}",
            f"**风险**：未关闭 {s['risk_open']}，监控中 {s['risk_monitoring']}",
        ]

    @staticmethod
    async def send_weekly_report(db: Session, receiver_id: Optional[str] = None) -> bool:
        """发送周报，返回是否实际发送"""
        receiver_id = receiver_id if receiver_id is not None else get_settings().FEISHU_REPORT_RECEIVER_ID
        if not receiver_id:
            logger.debug("No report receiver configured; skip weekly report")
            return False
        summary = ReportService.build_weekly_summary(db)
        return await NotificationService.notify_reminder(
            receiver_id,
            "项目周报",
            ReportService._summary_lines(summary),
            urgent=False,
        )
