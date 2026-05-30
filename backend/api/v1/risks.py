from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.models.user import User
from backend.models.risk import RiskStatus
from backend.schemas.risk import RiskCreate, RiskUpdate, RiskResponse
from backend.services.risk_service import RiskService
from backend.services.project_service import ProjectService
from backend.services.notification_service import NotificationService
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


def _get_risk_or_404(db: Session, risk_id: int):
    """获取风险，不存在则抛出 404"""
    risk = RiskService.get_by_id(db, risk_id)
    if not risk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk not found"
        )
    return risk


@router.post(
    "/projects/{project_id}/risks",
    response_model=RiskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_risk(
    project_id: int,
    risk_data: RiskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """在项目下创建风险"""
    _get_project_or_404(db, project_id)
    try:
        risk = RiskService.create(db, project_id, risk_data)
        return risk
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reference (e.g., owner_id does not exist)"
        )


@router.get(
    "/projects/{project_id}/risks",
    response_model=List[RiskResponse],
)
def get_risks(
    project_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[RiskStatus] = Query(None, alias="status"),
    owner_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取项目下的风险列表"""
    _get_project_or_404(db, project_id)
    return RiskService.get_list(
        db, project_id=project_id, skip=skip, limit=limit,
        status=status_filter, owner_id=owner_id,
    )


@router.get("/risks/{risk_id}", response_model=RiskResponse)
def get_risk(
    risk_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个风险"""
    return _get_risk_or_404(db, risk_id)


@router.put("/risks/{risk_id}", response_model=RiskResponse)
def update_risk(
    risk_id: int,
    risk_data: RiskUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新风险"""
    risk = _get_risk_or_404(db, risk_id)
    project = ProjectService.get_by_id(db, risk.project_id)

    # 权限检查
    PermissionChecker.require_risk_permission(current_user, risk, project, "modify")

    old_status = risk.status.value if risk.status else None

    try:
        risk = RiskService.update(db, risk_id, risk_data)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reference (e.g., owner_id does not exist)"
        )
    if not risk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk not found"
        )

    # 状态变更时，向风险负责人推送飞书通知（尽力而为，受开关控制）
    new_status = risk.status.value if risk.status else None
    if new_status and old_status and new_status != old_status:
        owner = db.query(User).filter(User.id == risk.owner_id).first() if risk.owner_id else None
        receive_id = owner.feishu_user_id if owner else None
        background_tasks.add_task(
            NotificationService.notify_risk_change,
            receive_id,
            risk.title,
            old_status,
            new_status,
            current_user.name,
            project.name if project else "",
        )

    return risk


@router.delete("/risks/{risk_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_risk(
    risk_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除风险"""
    risk = _get_risk_or_404(db, risk_id)
    project = ProjectService.get_by_id(db, risk.project_id)

    # 权限检查
    PermissionChecker.require_risk_permission(current_user, risk, project, "delete")

    RiskService.delete(db, risk_id)
