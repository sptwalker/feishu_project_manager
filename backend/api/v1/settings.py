"""系统设置 API（周例会状态 / 次数校准 / 项目催办阈值）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.core.dependencies import get_current_user, get_current_admin
from backend.models.user import User
from backend.schemas.setting import (
    MeetingStateResponse, MeetingActiveUpdate, MeetingCountUpdate,
    FollowupStallDaysResponse, FollowupStallDaysUpdate,
)
from backend.services.settings_service import SettingsService
from backend.services.project_followup_service import (
    get_stall_days_threshold, SETTING_FOLLOWUP_STALL_DAYS,
)

router = APIRouter()


@router.get("/settings/meeting", response_model=MeetingStateResponse)
def get_meeting_state(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取周例会状态（所有登录用户可读）"""
    return SettingsService.get_meeting_state(db)


@router.put("/settings/meeting/active", response_model=MeetingStateResponse)
def set_meeting_active(
    payload: MeetingActiveUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """开关周例会记录状态（仅管理员）"""
    SettingsService.set_active(db, payload.active)
    return SettingsService.get_meeting_state(db)


@router.put("/settings/meeting/count", response_model=MeetingStateResponse)
def set_meeting_count(
    payload: MeetingCountUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """校准周会次数（仅管理员）：以校准目标周一为基准重设"""
    SettingsService.set_count(db, payload.count)
    return SettingsService.get_meeting_state(db)


@router.get("/settings/followup-stall-days", response_model=FollowupStallDaysResponse)
def get_followup_stall_days(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目进展停滞催办天数阈值（所有登录用户可读）"""
    return FollowupStallDaysResponse(days=get_stall_days_threshold(db))


@router.put("/settings/followup-stall-days", response_model=FollowupStallDaysResponse)
def set_followup_stall_days(
    payload: FollowupStallDaysUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """设置项目进展停滞催办天数阈值（仅管理员）"""
    SettingsService.set_setting(db, SETTING_FOLLOWUP_STALL_DAYS, str(payload.days))
    return FollowupStallDaysResponse(days=get_stall_days_threshold(db))
