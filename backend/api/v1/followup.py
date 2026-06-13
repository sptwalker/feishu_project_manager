"""项目催办 API（管理员）

- 列出需催办的负责人及其停滞/待处理项目（确认表数据源）
- 按负责人私聊催办（手动触发）
真实外发受 FEISHU_NOTIFY_ENABLED 控制。
"""
from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.core.dependencies import get_current_admin
from backend.models.user import User
from backend.services.project_followup_service import ProjectFollowupService

router = APIRouter()


class NotifyOwnerRequest(BaseModel):
    owner_name: str = Field(..., description="负责人姓名")


@router.get("/followup/at-risk-owners")
def list_at_risk_owners(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """需催办的负责人列表（仅管理员）。feishu_id 不外泄，仅返回 resolvable 布尔。"""
    groups = ProjectFollowupService.group_at_risk_by_owner(db)
    return [
        {
            "owner": g["owner"],
            "resolvable": g["resolvable"],
            "stalled": g["stalled"],
            "pending": g["pending"],
            "stalled_count": g["stalled_count"],
            "pending_count": g["pending_count"],
        }
        for g in groups
    ]


@router.post("/followup/notify-owner")
async def notify_owner(
    payload: NotifyOwnerRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """向单个负责人私聊催办（手动，仅管理员）。返回 {sent, reason?}。"""
    return await ProjectFollowupService.send_owner_followup(
        db, payload.owner_name, auto=False, operator=current_admin)
