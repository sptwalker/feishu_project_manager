from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user, get_current_admin
from backend.models.user import User
from backend.models.project import ProjectStatus
from backend.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from backend.services.project_service import ProjectService, ProjectVersionConflict
from backend.services.operation_log_service import OperationLogService
from backend.services.project_diff import build_field_change_desc
from backend.schemas.operation_log import OperationLogResponse
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
        project_id=project.id,
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

    # 在更新前对比基本字段，生成字段级中文变更描述（用旧值）
    payload = project_data.model_dump(exclude_unset=True)
    field_desc = build_field_change_desc(project, payload, old_name)

    try:
        project = ProjectService.update(db, project_id, project_data)
    except (ProjectVersionConflict, StaleDataError):
        # 乐观锁冲突：应用层版本比对失败，或并发提交时 SQL 级 CAS 命中 0 行
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="项目已被他人修改，请刷新后重试"
        )
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

    # 记录操作日志（带 project_id，供项目历史查询）
    pname = project.name or old_name
    if "progress_log" in payload:
        # 进展变化：按类型分类记录；未分类到具体动作但进展确有变化时兜底记“更新了进展”
        action, st = OperationLogService.classify_progress_change(old_log, project.progress_log or [])
        if action == "feedback":
            OperationLogService.log(db, user=current_user, action="feedback", target=pname,
                                    description=f'在项目"{pname}"里反馈了{st}事项', project_id=project.id)
        elif action == "update_progress":
            OperationLogService.log(db, user=current_user, action="update_progress", target=pname,
                                    description=f'在项目"{pname}"里更新了项目进展', project_id=project.id)
        elif action == "comment":
            OperationLogService.log(db, user=current_user, action="comment", target=pname,
                                    description=f'在项目"{pname}"里进行了评论', project_id=project.id)
        elif action == "delete_progress":
            OperationLogService.log(db, user=current_user, action="delete_progress", target=pname,
                                    description=f'在项目"{pname}"里删除了项目进展', project_id=project.id)
        elif (old_log or []) != (project.progress_log or []):
            # 进展内容/状态被修改但不属于增/删/批注 → 兜底记“更新了进展”
            OperationLogService.log(db, user=current_user, action="update_progress", target=pname,
                                    description=f'在项目"{pname}"里更新了项目进展', project_id=project.id)
        # 若同一次提交还改了基本字段，再补记一条字段级变更
        if field_desc:
            OperationLogService.log(db, user=current_user, action="edit_project", target=pname,
                                    description=field_desc, project_id=project.id)
    elif field_desc:
        # 仅基本字段变化：记录精确的字段级变更描述
        OperationLogService.log(db, user=current_user, action="edit_project", target=pname,
                                description=field_desc, project_id=project.id)
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
        project_id=project_id,
    )


@router.get("/{project_id}/history", response_model=List[OperationLogResponse])
def get_project_history(
    project_id: int,
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取某项目的历史修改记录（按发生时间倒序）。登录用户可读。"""
    if not ProjectService.get_by_id(db, project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return OperationLogService.query(db, project_id=project_id, limit=limit)
