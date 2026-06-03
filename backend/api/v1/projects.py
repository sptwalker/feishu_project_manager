from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user, get_current_admin
from backend.models.user import User
from backend.models.project import ProjectStatus
from backend.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from backend.services.project_service import ProjectService
from backend.services.operation_log_service import OperationLogService
from backend.core.permissions import PermissionChecker

router = APIRouter()

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建项目"""
    PermissionChecker.require_project_permission(current_user, action="modify")
    try:
        project = ProjectService.create(db, project_data)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project data"
        )
    OperationLogService.log(
        db, user=current_user, action="create_project",
        target=project.name, description=f'新增了项目记录"{project.name}"',
    )
    return project

@router.get("/", response_model=List[ProjectResponse])
def get_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    status_filter: Optional[ProjectStatus] = Query(None, alias="status"),
    owner_name: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取项目列表"""
    projects = ProjectService.get_list(
        db, skip=skip, limit=limit,
        status=status_filter, owner_name=owner_name, department=department
    )
    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个项目"""
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新项目"""
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # 权限检查
    PermissionChecker.require_project_permission(current_user, project, "modify")

    # 快照旧进展，用于更新后判定操作类型（进展更新/评论/反馈）
    import copy
    old_log = copy.deepcopy(project.progress_log or [])
    old_name = project.name

    try:
        project = ProjectService.update(db, project_id, project_data)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project data"
        )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # 记录操作日志：优先按进展变化分类，否则视为普通信息修改
    pname = project.name or old_name
    payload = project_data.model_dump(exclude_unset=True)
    if "progress_log" in payload:
        action, st = OperationLogService.classify_progress_change(old_log, project.progress_log or [])
        if action == "feedback":
            OperationLogService.log(db, user=current_user, action="feedback", target=pname,
                                    description=f'在项目"{pname}"里反馈了{st}事项')
        elif action == "update_progress":
            OperationLogService.log(db, user=current_user, action="update_progress", target=pname,
                                    description=f'在项目"{pname}"里更新了项目进展')
        elif action == "comment":
            OperationLogService.log(db, user=current_user, action="comment", target=pname,
                                    description=f'在项目"{pname}"里进行了评论')
        elif action == "delete_progress":
            OperationLogService.log(db, user=current_user, action="delete_progress", target=pname,
                                    description=f'在项目"{pname}"里删除了项目进展')
        elif len(payload) > 1:
            # 进展无变化但同时改了其它字段
            OperationLogService.log(db, user=current_user, action="edit_project", target=pname,
                                    description=f'修改了项目"{pname}"的信息')
    elif payload:
        OperationLogService.log(db, user=current_user, action="edit_project", target=pname,
                                description=f'修改了项目"{pname}"的信息')
    return project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """删除项目（仅管理员）"""
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # 权限检查
    PermissionChecker.require_project_permission(current_user, project, "delete")

    pname = project.name
    ProjectService.delete(db, project_id)
    OperationLogService.log(
        db, user=current_user, action="delete_project",
        target=pname, description=f'删除了项目"{pname}"',
    )
