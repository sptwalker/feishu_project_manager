"""飞书多维表格（Bitable）同步服务

将本地项目/任务数据同步到飞书多维表格。同步通过 record_id 做 upsert：
- 提供 record_id：更新对应记录
- 不提供：新建记录并返回 record_id

字段映射保持简单的字符串/数值，便于在多维表格中直接展示。
需要在配置中提供 FEISHU_BITABLE_APP_TOKEN 与对应表 ID。
"""
import logging
from typing import Optional, Dict, Any
from backend.core.config import get_settings
from backend.core.feishu import feishu_client

logger = logging.getLogger(__name__)


class BitableConfigError(Exception):
    """多维表格配置缺失"""
    pass


class BitableService:
    """多维表格同步服务"""

    @staticmethod
    def _project_table() -> tuple[str, str]:
        s = get_settings()
        if not s.FEISHU_BITABLE_APP_TOKEN or not s.FEISHU_BITABLE_PROJECT_TABLE_ID:
            raise BitableConfigError("Bitable project table is not configured")
        return s.FEISHU_BITABLE_APP_TOKEN, s.FEISHU_BITABLE_PROJECT_TABLE_ID

    @staticmethod
    def _task_table() -> tuple[str, str]:
        s = get_settings()
        if not s.FEISHU_BITABLE_APP_TOKEN or not s.FEISHU_BITABLE_TASK_TABLE_ID:
            raise BitableConfigError("Bitable task table is not configured")
        return s.FEISHU_BITABLE_APP_TOKEN, s.FEISHU_BITABLE_TASK_TABLE_ID

    @staticmethod
    def project_to_fields(project) -> Dict[str, Any]:
        """Project ORM -> 多维表格字段"""
        return {
            "项目ID": project.id,
            "项目名称": project.name or "",
            "状态": project.status.value if project.status else "",
            "紧急程度": project.urgency.value if project.urgency else "",
            "完成度": project.completion or 0,
            "部门": project.department or "",
        }

    @staticmethod
    def task_to_fields(task) -> Dict[str, Any]:
        """Task ORM -> 多维表格字段"""
        return {
            "任务ID": task.id,
            "任务名称": task.name or "",
            "项目ID": task.project_id,
            "状态": task.status.value if task.status else "",
            "优先级": task.priority.value if task.priority else "",
            "完成度": task.completion or 0,
        }

    @staticmethod
    async def _upsert(app_token: str, table_id: str, fields: Dict[str, Any],
                      record_id: Optional[str]) -> str:
        if record_id:
            await feishu_client.bitable_update_record(app_token, table_id, record_id, fields)
            return record_id
        data = await feishu_client.bitable_create_record(app_token, table_id, fields)
        return (data.get("record", {}) or {}).get("record_id", "")

    @staticmethod
    async def sync_project(project, record_id: Optional[str] = None) -> str:
        """同步单个项目，返回 record_id"""
        app_token, table_id = BitableService._project_table()
        fields = BitableService.project_to_fields(project)
        return await BitableService._upsert(app_token, table_id, fields, record_id)

    @staticmethod
    async def sync_task(task, record_id: Optional[str] = None) -> str:
        """同步单个任务，返回 record_id"""
        app_token, table_id = BitableService._task_table()
        fields = BitableService.task_to_fields(task)
        return await BitableService._upsert(app_token, table_id, fields, record_id)
