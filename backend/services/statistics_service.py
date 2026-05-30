"""统计服务：看板与进度统计

提供仪表盘聚合数据，复用提醒服务的逾期查询。所有方法为纯查询，便于单测。
"""
from typing import Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session
from backend.models.project import Project, ProjectStatus
from backend.models.task import Task, TaskStatus
from backend.models.risk import Risk, RiskStatus
from backend.services.reminder_service import ReminderService


class StatisticsService:
    """统计服务"""

    @staticmethod
    def _count_by_enum(items, enum_cls, attr="status") -> Dict[str, int]:
        counts = {e.value: 0 for e in enum_cls}
        for it in items:
            val = getattr(it, attr)
            if val is not None:
                counts[val.value] = counts.get(val.value, 0) + 1
        return counts

    @staticmethod
    def dashboard(db: Session, today: Optional[date] = None) -> Dict[str, Any]:
        """仪表盘统计：项目/任务/风险分布 + 逾期计数 + 平均完成度"""
        today = today or date.today()
        projects = db.query(Project).all()
        tasks = db.query(Task).all()
        risks = db.query(Risk).all()

        avg_completion = (
            round(sum(p.completion or 0 for p in projects) / len(projects), 1)
            if projects else 0.0
        )

        return {
            "projects": {
                "total": len(projects),
                "by_status": StatisticsService._count_by_enum(projects, ProjectStatus),
                "avg_completion": avg_completion,
                "overdue": len(ReminderService.find_overdue_projects(db, today)),
            },
            "tasks": {
                "total": len(tasks),
                "by_status": StatisticsService._count_by_enum(tasks, TaskStatus),
                "overdue": len(ReminderService.find_overdue_tasks(db, today)),
            },
            "risks": {
                "total": len(risks),
                "by_status": StatisticsService._count_by_enum(risks, RiskStatus),
            },
        }

    @staticmethod
    def project_progress(db: Session, project_id: int) -> Optional[Dict[str, Any]]:
        """单个项目进度统计：任务状态分布与完成率"""
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        return {
            "project_id": project.id,
            "project_name": project.name,
            "status": project.status.value if project.status else None,
            "completion": project.completion or 0,
            "task_total": total,
            "task_completed": completed,
            "task_completion_rate": round(completed / total * 100, 1) if total else 0.0,
            "task_by_status": StatisticsService._count_by_enum(tasks, TaskStatus),
        }
