"""系统设置 API（周例会状态 / 次数校准 / 项目催办阈值）"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.core.dependencies import get_current_user, get_current_admin
from backend.models.user import User
from backend.schemas.setting import (
    MeetingStateResponse, MeetingActiveUpdate, MeetingCountUpdate,
    FollowupStallDaysResponse, FollowupStallDaysUpdate,
    CoreGroupChatIdResponse, CoreGroupChatIdUpdate,
    AutoOpenMeetingResponse, AutoOpenMeetingUpdate,
    AutoReminderResponse, AutoReminderUpdate,
    MeetingReportOrderResponse, MeetingReportOrderUpdate,
    MeetingTimerResponse, MeetingTimerUpdate,
    FollowupAutoResponse, FollowupAutoUpdate,
    FeishuAppResponse, FeishuAppUpdate,
)
from backend.services.settings_service import SettingsService, FEISHU_CORE_GROUP_CHAT_ID_KEY
from backend.schemas.branding import BrandingFull, BrandingUpdate
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


@router.get("/settings/core-group-chat-id", response_model=CoreGroupChatIdResponse)
def get_core_group_chat_id(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取周会纪要核心群 chat_id（所有登录用户可读）"""
    return CoreGroupChatIdResponse(chat_id=SettingsService.get_core_group_chat_id(db) or "")


@router.put("/settings/core-group-chat-id", response_model=CoreGroupChatIdResponse)
def set_core_group_chat_id(
    payload: CoreGroupChatIdUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """设置周会纪要核心群 chat_id（仅管理员；空字符串=清空，留空则不发送）"""
    SettingsService.set_setting(db, FEISHU_CORE_GROUP_CHAT_ID_KEY, payload.chat_id.strip())
    return CoreGroupChatIdResponse(chat_id=SettingsService.get_core_group_chat_id(db) or "")


@router.get("/settings/auto-open-meeting", response_model=AutoOpenMeetingResponse)
def get_auto_open_meeting(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取周四自动开周会开关状态（所有登录用户可读）"""
    return AutoOpenMeetingResponse(enabled=SettingsService.get_auto_open_meeting_enabled(db))


@router.put("/settings/auto-open-meeting", response_model=AutoOpenMeetingResponse)
def set_auto_open_meeting(
    payload: AutoOpenMeetingUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """切换周四自动开周会开关（仅管理员；改后立即生效无需重启）"""
    SettingsService.set_auto_open_meeting_enabled(db, payload.enabled)
    return AutoOpenMeetingResponse(enabled=SettingsService.get_auto_open_meeting_enabled(db))


@router.get("/settings/auto-reminder", response_model=AutoReminderResponse)
def get_auto_reminder(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取周会自动催更开关状态（所有登录用户可读）"""
    return AutoReminderResponse(enabled=SettingsService.get_auto_reminder_enabled(db))


@router.put("/settings/auto-reminder", response_model=AutoReminderResponse)
def set_auto_reminder(
    payload: AutoReminderUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """切换周会自动催更开关（仅管理员；改后立即生效无需重启）"""
    SettingsService.set_auto_reminder_enabled(db, payload.enabled)
    return AutoReminderResponse(enabled=SettingsService.get_auto_reminder_enabled(db))


@router.get("/settings/meeting-report-order", response_model=MeetingReportOrderResponse)
def get_meeting_report_order(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取周会汇报顺序（所有登录用户可读，用于正确排序）"""
    return MeetingReportOrderResponse(**SettingsService.get_meeting_report_order(db))


@router.put("/settings/meeting-report-order", response_model=MeetingReportOrderResponse)
def set_meeting_report_order(
    payload: MeetingReportOrderUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """保存周会汇报顺序（仅管理员；拖拽结束即保存）"""
    SettingsService.set_meeting_report_order(db, payload.departments, payload.members)
    return MeetingReportOrderResponse(**SettingsService.get_meeting_report_order(db))


@router.get("/settings/meeting-timer", response_model=MeetingTimerResponse)
def get_meeting_timer(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取周会计时设置（所有登录用户可读）"""
    return MeetingTimerResponse(
        total_minutes=SettingsService.get_meeting_total_minutes(db),
        person_threshold_minutes=SettingsService.get_meeting_person_threshold_minutes(db),
    )


@router.put("/settings/meeting-timer", response_model=MeetingTimerResponse)
def set_meeting_timer(
    payload: MeetingTimerUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """更新周会计时设置（仅管理员）"""
    SettingsService.set_meeting_total_minutes(db, payload.total_minutes)
    SettingsService.set_meeting_person_threshold_minutes(db, payload.person_threshold_minutes)
    return MeetingTimerResponse(
        total_minutes=SettingsService.get_meeting_total_minutes(db),
        person_threshold_minutes=SettingsService.get_meeting_person_threshold_minutes(db),
    )


@router.get("/settings/followup-auto", response_model=FollowupAutoResponse)
def get_followup_auto(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取自动定时催办配置（所有登录用户可读）"""
    return FollowupAutoResponse(**SettingsService.get_followup_auto(db))


@router.put("/settings/followup-auto", response_model=FollowupAutoResponse)
def set_followup_auto(
    payload: FollowupAutoUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """保存自动定时催办配置（仅管理员；改后立即生效无需重启）"""
    merged = SettingsService.set_followup_auto(db, payload.model_dump())
    return FollowupAutoResponse(**merged)


@router.get("/settings/feishu-app", response_model=FeishuAppResponse)
def get_feishu_app(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """获取本实例飞书应用配置（仅管理员；只返回 App ID 与「是否已配密钥」，不回传密钥）"""
    return FeishuAppResponse(
        app_id=SettingsService.get_feishu_app_id(db),
        secret_set=SettingsService.is_feishu_secret_set(db),
    )


@router.put("/settings/feishu-app", response_model=FeishuAppResponse)
def set_feishu_app(
    payload: FeishuAppUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """保存本实例飞书应用凭证（仅管理员；App Secret 留空则保持原值。改后立即生效无需重启）"""
    SettingsService.set_feishu_app(db, payload.app_id, payload.app_secret)
    return FeishuAppResponse(
        app_id=SettingsService.get_feishu_app_id(db),
        secret_set=SettingsService.is_feishu_secret_set(db),
    )


@router.get("/settings/branding", response_model=BrandingFull)
def get_branding_full(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """获取本实例品牌完整配置（仅管理员，用于设置页表单回显；DB 优先、空回退 .env）"""
    return BrandingFull(**SettingsService.get_branding_config(db))


@router.put("/settings/branding", response_model=BrandingFull)
def set_branding_full(
    payload: BrandingUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """保存本实例品牌配置（仅管理员；改后刷新即生效，无需登录服务器/重启）。
    logo_url 支持 data URI（上传图片转 base64）；为防 DB 膨胀限制其长度。"""
    if payload.logo_url and payload.logo_url.startswith("data:") and len(payload.logo_url) > 700_000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="logo 图片过大（请压缩到约 500KB 以内）")
    merged = SettingsService.set_branding_config(db, payload.model_dump())
    return BrandingFull(**merged)
