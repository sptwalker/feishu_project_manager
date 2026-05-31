"""Excel 导入服务

解析 xlsx 中的任务/项目行，校验并批量创建，返回导入结果
（成功数与逐行错误），单行错误不影响其余行。
"""
from datetime import date, datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from pydantic import ValidationError
from backend.utils.excel import parse_xlsx, ExcelParseError
from backend.schemas.task import TaskCreate
from backend.schemas.project import ProjectCreate
from backend.services.task_service import TaskService
from backend.services.project_service import ProjectService

# 导入模板要求的最少列
REQUIRED_TASK_COLUMNS = ["任务名称", "负责人"]
# 项目导入（周会跟进清单格式）要求的最少列
REQUIRED_PROJECT_COLUMNS = ["待办事项", "负责人"]

# 完成情况 -> 项目状态
PROJECT_STATUS_MAP = {
    "执行中": "in_progress",
    "进行中": "in_progress",
    "已完成": "completed",
    "完成": "completed",
    "暂停中": "paused",
    "暂停": "paused",
    "已取消": "cancelled",
    "取消": "cancelled",
    "待启动": "planned",
    "未开始": "planned",
}
# 优先级 P0-P3 -> 紧急程度
PRIORITY_URGENCY_MAP = {
    "P0": "urgent",
    "P1": "high",
    "P2": "medium",
    "P3": "low",
}


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
    s = str(value).strip()[:10].replace("/", "-")
    parts = s.split("-")
    if len(parts) == 3:
        y, m, d = (int(p) for p in parts)
        return date(y, m, d)
    return date.fromisoformat(s)


def _progress_to_completion(value: Any) -> int:
    """进度 0~1（或 0~100）-> 完成度 0-100 整数"""
    if value is None or str(value).strip() == "":
        return 0
    f = float(value)
    if f <= 1.0:
        f *= 100
    return max(0, min(100, round(f)))


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
            "owner_name": str(row.get("负责人")).strip() if row.get("负责人") else None,
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

    @staticmethod
    def _row_to_project_create(db: Session, row: Dict[str, Any]) -> Optional[ProjectCreate]:
        """单行（周会跟进清单格式）-> ProjectCreate。空名行返回 None。"""
        name = str(row.get("待办事项") or "").strip()
        if not name:
            return None

        owner_name = str(row.get("负责人") or "").strip()
        if not owner_name:
            raise ValueError("负责人为空")

        # 说明 + 目前状况（进展备注）合并为 content，避免信息丢失
        content_parts = []
        if str(row.get("说明") or "").strip():
            content_parts.append(str(row["说明"]).strip())
        if str(row.get("目前状况") or "").strip():
            content_parts.append("【进展】" + str(row["目前状况"]).strip())
        content = "\n".join(content_parts) or None

        status = PROJECT_STATUS_MAP.get(str(row.get("完成情况") or "").strip(), "planned")
        urgency = PRIORITY_URGENCY_MAP.get(str(row.get("优先级") or "").strip().upper(), "medium")

        payload: Dict[str, Any] = {
            "name": name,
            "owner_name": owner_name,
            "content": content,
            "status": status,
            "urgency": urgency,
            "completion": _progress_to_completion(row.get("进度")),
            "record_date": _to_date(row.get("记录日期")) or date.today(),
        }
        if str(row.get("部门") or "").strip():
            payload["department"] = str(row["部门"]).strip()[:100]
        end = _to_date(row.get("截止日期"))
        if end:
            payload["estimated_end_date"] = end
        return ProjectCreate(**payload)

    @staticmethod
    def import_projects(db: Session, data: bytes) -> ImportResult:
        """从「周会跟进清单」格式的 xlsx 批量导入项目"""
        rows = parse_xlsx(data, expected_headers=REQUIRED_PROJECT_COLUMNS)
        result = ImportResult()
        for idx, row in enumerate(rows, start=2):
            try:
                project_create = ImportService._row_to_project_create(db, row)
                if project_create is None:
                    continue  # 空行跳过，不计入
                ProjectService.create(db, project_create)
                result.created += 1
            except (ValidationError, ValueError, TypeError) as e:
                result.errors.append({"row": idx, "error": str(e)})
        return result
