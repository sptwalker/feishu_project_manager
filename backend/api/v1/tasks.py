from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.models.user import User
from backend.models.task import TaskStatus, TaskPriority
from backend.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from backend.services.task_service import TaskService
from backend.services.project_service import ProjectService
from backend.core.permissions import PermissionChecker

router = APIRouter()


def _get_project_or_404(db: Session, project_id: int):
    """获取项目，不存在则抛出 404"""
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


def _get_task_or_404(db: Session, task_id: int):
    """获取任务，不存在则抛出 404"""
    task = TaskService.get_by_id(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


def _validate_parent_task(db: Session, project_id: int, parent_task_id: int):
    """校验父任务存在且属于同一项目"""
    parent = TaskService.get_by_id(db, parent_task_id)
    if not parent or parent.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="parent_task_id is invalid or belongs to another project"
        )


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    project_id: int,
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """在项目下创建任务"""
    PermissionChecker.require_task_permission(current_user, action="modify")
    _get_project_or_404(db, project_id)

    if task_data.parent_task_id is not None:
        _validate_parent_task(db, project_id, task_data.parent_task_id)

    try:
        task = TaskService.create(db, project_id, task_data)
        return task
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task data"
        )


@router.get(
    "/projects/{project_id}/tasks",
    response_model=List[TaskResponse],
)
def get_tasks(
    project_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    priority: Optional[TaskPriority] = None,
    owner_name: Optional[str] = None,
    parent_task_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取项目下的任务列表"""
    _get_project_or_404(db, project_id)
    return TaskService.get_list(
        db, project_id=project_id, skip=skip, limit=limit,
        status=status_filter, priority=priority,
        owner_name=owner_name, parent_task_id=parent_task_id,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个任务"""
    return _get_task_or_404(db, task_id)


@router.get("/tasks/{task_id}/subtasks", response_model=List[TaskResponse])
def get_subtasks(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定任务的子任务列表"""
    _get_task_or_404(db, task_id)
    return TaskService.get_subtasks(db, task_id)


@router.post(
    "/tasks/{task_id}/subtasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_subtask(
    task_id: int,
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """在指定任务下创建子任务（继承父任务所属项目）"""
    PermissionChecker.require_task_permission(current_user, action="modify")
    parent = _get_task_or_404(db, task_id)

    # 子任务强制归属父任务及其项目
    task_data.parent_task_id = task_id
    try:
        task = TaskService.create(db, parent.project_id, task_data)
        return task
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task data"
        )


@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新任务"""
    task = _get_task_or_404(db, task_id)

    # 权限检查（基于角色）
    PermissionChecker.require_task_permission(current_user, task, action="modify")

    if task_data.parent_task_id is not None:
        _validate_parent_task(db, task.project_id, task_data.parent_task_id)

    try:
        task = TaskService.update(db, task_id, task_data)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task data"
        )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除任务"""
    task = _get_task_or_404(db, task_id)

    # 权限检查（基于角色）
    PermissionChecker.require_task_permission(current_user, task, action="delete")

    TaskService.delete(db, task_id)
