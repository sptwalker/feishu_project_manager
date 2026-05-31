"""提醒查询与通知服务

提供面向定时任务的查询逻辑（纯函数，便于单测）与通知编排：
- 逾期任务：due_date < today 且未完成
- 临期任务：today <= due_date <= today+N 且未完成
- 进度跟催：进行中(in_progress)且 updated_at 早于 N 天
- 里程碑（项目预计完成）：estimated_end_date < today 且项目未完成/未取消

项目数据已与用户账号解耦，负责人仅为姓名字符串，无法定向推送到个人飞书。
因此提醒统一发送给配置的接收人 FEISHU_REPORT_RECEIVER_ID（如管理者/群），
并在正文中标注负责人姓名。受 FEISHU_NOTIFY_ENABLED 控制。
"""
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.task import Task, TaskStatus
from backend.models.project import Project, ProjectStatus
from backend.core.config import get_settings
from backend.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# 视为“未完成”的任务状态
_OPEN_TASK_STATUSES = (TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED)
# 视为“进行中”的项目状态（用于里程碑提醒）
_OPEN_PROJECT_STATUSES = (ProjectStatus.PLANNED, ProjectStatus.IN_PROGRESS)


def _owner_line(owner_name: Optional[str]) -> str:
    return f"**负责人**：{owner_name}" if owner_name else "**负责人**：未指定"


def _receiver() -> Optional[str]:
    return get_settings().FEISHU_REPORT_RECEIVER_ID or None


class ReminderService:
    """提醒服务"""

    # ---------- 纯查询（可独立单测） ----------

    @staticmethod
    def find_overdue_tasks(db: Session, today: Optional[date] = None) -> List[Task]:
        """查找逾期任务：有截止日期、已过期且未完成"""
        today = today or date.today()
        return (
            db.query(Task)
            .filter(Task.due_date.isnot(None))
            .filter(Task.due_date < today)
            .filter(Task.status.in_(_OPEN_TASK_STATUSES))
            .all()
        )

    @staticmethod
    def find_due_soon_tasks(db: Session, today: Optional[date] = None,
                            days: int = 3) -> List[Task]:
        """查找临期任务：今天到 today+days 之间到期且未完成"""
        today = today or date.today()
        horizon = today + timedelta(days=days)
        return (
            db.query(Task)
            .filter(Task.due_date.isnot(None))
            .filter(Task.due_date >= today)
            .filter(Task.due_date <= horizon)
            .filter(Task.status.in_(_OPEN_TASK_STATUSES))
            .all()
        )

    @staticmethod
    def find_stale_in_progress_tasks(db: Session, now: Optional[datetime] = None,
                                     days: int = 3) -> List[Task]:
        """查找需跟催任务：进行中且 updated_at 早于 now-days"""
        now = now or datetime.now()
        threshold = now - timedelta(days=days)
        return (
            db.query(Task)
            .filter(Task.status == TaskStatus.IN_PROGRESS)
            .filter(Task.updated_at < threshold)
            .all()
        )

    @staticmethod
    def find_overdue_projects(db: Session, today: Optional[date] = None) -> List[Project]:
        """查找逾期项目（里程碑）：预计完成日已过且项目未完成/未取消"""
        today = today or date.today()
        return (
            db.query(Project)
            .filter(Project.estimated_end_date.isnot(None))
            .filter(Project.estimated_end_date < today)
            .filter(Project.status.in_(_OPEN_PROJECT_STATUSES))
            .all()
        )

    # ---------- 通知编排（统一发给配置的接收人） ----------

    @staticmethod
    async def send_overdue_task_reminders(db: Session, today: Optional[date] = None) -> int:
        """发送逾期任务提醒，返回实际发送条数"""
        today = today or date.today()
        receive_id = _receiver()
        sent = 0
        for task in ReminderService.find_overdue_tasks(db, today):
            overdue_days = (today - task.due_date).days
            ok = await NotificationService.notify_reminder(
                receive_id,
                f"任务逾期提醒：{task.name}",
                [
                    _owner_line(task.owner_name),
                    f"**截止日期**：{task.due_date.isoformat()}",
                    f"**已逾期**：{overdue_days} 天",
                    f"**当前状态**：{task.status.value if task.status else ''}",
                ],
                urgent=True,
            )
            sent += 1 if ok else 0
        return sent

    @staticmethod
    async def send_due_soon_reminders(db: Session, today: Optional[date] = None,
                                      days: int = 3) -> int:
        """发送临期任务提醒，返回实际发送条数"""
        today = today or date.today()
        receive_id = _receiver()
        sent = 0
        for task in ReminderService.find_due_soon_tasks(db, today, days):
            remain = (task.due_date - today).days
            ok = await NotificationService.notify_reminder(
                receive_id,
                f"任务临期提醒：{task.name}",
                [
                    _owner_line(task.owner_name),
                    f"**截止日期**：{task.due_date.isoformat()}",
                    f"**剩余**：{remain} 天",
                ],
                urgent=False,
            )
            sent += 1 if ok else 0
        return sent

    @staticmethod
    async def send_progress_followups(db: Session, now: Optional[datetime] = None,
                                      days: int = 3) -> int:
        """发送进度跟催，返回实际发送条数"""
        now = now or datetime.now()
        receive_id = _receiver()
        sent = 0
        for task in ReminderService.find_stale_in_progress_tasks(db, now, days):
            ok = await NotificationService.notify_reminder(
                receive_id,
                f"进度跟催：{task.name}",
                [
                    _owner_line(task.owner_name),
                    f"**当前完成度**：{task.completion or 0}%",
                    f"该任务已进行中且超过 {days} 天未更新，请反馈最新进度。",
                ],
                urgent=False,
            )
            sent += 1 if ok else 0
        return sent

    @staticmethod
    async def send_milestone_reminders(db: Session, today: Optional[date] = None) -> int:
        """发送里程碑（项目预计完成）逾期提醒，返回实际发送条数"""
        today = today or date.today()
        receive_id = _receiver()
        sent = 0
        for project in ReminderService.find_overdue_projects(db, today):
            overdue_days = (today - project.estimated_end_date).days
            ok = await NotificationService.notify_reminder(
                receive_id,
                f"项目里程碑逾期：{project.name}",
                [
                    _owner_line(project.owner_name),
                    f"**预计完成**：{project.estimated_end_date.isoformat()}",
                    f"**已逾期**：{overdue_days} 天",
                    f"**完成度**：{project.completion or 0}%",
                ],
                urgent=True,
            )
            sent += 1 if ok else 0
        return sent
