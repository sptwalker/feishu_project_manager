"""Excel 导出服务

将项目/任务数据导出为 xlsx 字节，供 API 以附件形式下载。
"""
from typing import List
from sqlalchemy.orm import Session
from backend.models.project import Project
from backend.models.task import Task
from backend.utils.excel import build_xlsx


def _date_str(d) -> str:
    return d.isoformat() if d else ""


class ExportService:
    """导出服务"""

    PROJECT_HEADERS = [
        "项目ID", "项目名称", "状态", "紧急程度", "完成度", "部门", "负责人",
        "记录日期", "预计完成", "实际完成",
    ]
    TASK_HEADERS = [
        "任务ID", "任务名称", "项目ID", "负责人", "状态", "优先级",
        "完成度", "开始日期", "截止日期", "完成日期", "父任务ID",
    ]

    @staticmethod
    def export_projects(db: Session) -> bytes:
        """导出全部项目为 xlsx"""
        projects: List[Project] = db.query(Project).all()
        rows = [
            [
                p.id, p.name,
                p.status.value if p.status else "",
                p.urgency.value if p.urgency else "",
                p.completion or 0,
                p.department or "",
                p.owner_name or "",
                _date_str(p.record_date),
                _date_str(p.estimated_end_date),
                _date_str(p.actual_end_date),
            ]
            for p in projects
        ]
        return build_xlsx(ExportService.PROJECT_HEADERS, rows, sheet_title="Projects")

    @staticmethod
    def export_tasks(db: Session, project_id: int) -> bytes:
        """导出指定项目的任务为 xlsx"""
        tasks: List[Task] = db.query(Task).filter(Task.project_id == project_id).all()
        rows = [
            [
                t.id, t.name, t.project_id, t.owner_name or "",
                t.status.value if t.status else "",
                t.priority.value if t.priority else "",
                t.completion or 0,
                _date_str(t.start_date),
                _date_str(t.due_date),
                _date_str(t.end_date),
                t.parent_task_id or "",
            ]
            for t in tasks
        ]
        return build_xlsx(ExportService.TASK_HEADERS, rows, sheet_title="Tasks")
