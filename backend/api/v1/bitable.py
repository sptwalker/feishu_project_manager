"""多维表格同步 API

提供手动触发同步的端点。仅管理员或项目所有者可触发。
未配置多维表格时返回 503。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.models.user import User
from backend.services.project_service import ProjectService
from backend.services.task_service import TaskService
from backend.services.bitable_service import BitableService, BitableConfigError
from backend.core.feishu import FeishuAPIError
from backend.core.permissions import PermissionChecker

router = APIRouter()


@router.post("/bitable/projects/{project_id}/sync")
async def sync_project_to_bitable(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将项目同步到飞书多维表格"""
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    PermissionChecker.require_project_permission(current_user, project, "modify")

    try:
        record_id = await BitableService.sync_project(project)
    except BitableConfigError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except FeishuAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    return {"record_id": record_id, "synced": True}


@router.post("/bitable/tasks/{task_id}/sync")
async def sync_task_to_bitable(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将任务同步到飞书多维表格"""
    task = TaskService.get_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    project = ProjectService.get_by_id(db, task.project_id)
    PermissionChecker.require_task_permission(current_user, task, project, "modify")

    try:
        record_id = await BitableService.sync_task(task)
    except BitableConfigError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except FeishuAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    return {"record_id": record_id, "synced": True}
