"""Excel 导入服务

解析 xlsx 中的任务行，校验并批量创建任务到指定项目。
返回导入结果（成功数与逐行错误），单行错误不影响其余行。
"""
from datetime import date, datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from pydantic import ValidationError
from backend.utils.excel import parse_xlsx, ExcelParseError
from backend.schemas.task import TaskCreate
from backend.services.task_service import TaskService

# 导入模板要求的最少列
REQUIRED_TASK_COLUMNS = ["任务名称", "负责人ID"]


def _to_int(value: Any) -> Optional[int]:
    if value is None or str(value).strip() == "":
        return None
    return int(float(value))


def _to_date(value: Any) -> Optional[date]:
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value).strip()[:10])


class ImportResult:
    """导入结果"""
    def __init__(self):
        self.created = 0
        self.errors: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {"created": self.created, "errors": self.errors, "error_count": len(self.errors)}


class ImportService:
    """导入服务"""

    @staticmethod
    def _row_to_task_create(row: Dict[str, Any]) -> TaskCreate:
        """单行 -> TaskCreate（不含 project_id）"""
        payload: Dict[str, Any] = {
            "name": str(row.get("任务名称")).strip() if row.get("任务名称") else None,
            "owner_id": _to_int(row.get("负责人ID")),
        }
        if row.get("状态"):
            payload["status"] = str(row["状态"]).strip()
        if row.get("优先级"):
            payload["priority"] = str(row["优先级"]).strip()
        if row.get("完成度") is not None and str(row.get("完成度")).strip() != "":
            payload["completion"] = _to_int(row.get("完成度"))
        if row.get("开始日期"):
            payload["start_date"] = _to_date(row.get("开始日期"))
        if row.get("截止日期"):
            payload["due_date"] = _to_date(row.get("截止日期"))
        return TaskCreate(**payload)

    @staticmethod
    def import_tasks(db: Session, project_id: int, data: bytes) -> ImportResult:
        """从 xlsx 导入任务到指定项目"""
        rows = parse_xlsx(data, expected_headers=REQUIRED_TASK_COLUMNS)
        result = ImportResult()
        for idx, row in enumerate(rows, start=2):  # 从第 2 行（表头之后）开始计数
            try:
                task_create = ImportService._row_to_task_create(row)
                TaskService.create(db, project_id, task_create)
                result.created += 1
            except (ValidationError, ValueError, TypeError) as e:
                result.errors.append({"row": idx, "error": str(e)})
        return result
