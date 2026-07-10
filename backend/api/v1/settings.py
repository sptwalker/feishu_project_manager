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
    SalesCodeEnabledResponse, SalesCodeEnabledUpdate,
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
    """校准周会次数（仅管理员）：纠正最近一次周会的次数"""
    try:
        SettingsService.set_count(db, payload.count)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
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


@router.get("/settings/sales-code-enabled", response_model=SalesCodeEnabledResponse)
def get_sales_code_enabled(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取内部销售码平台开关状态（所有登录用户可读；侧栏据此决定菜单可见）"""
    return SalesCodeEnabledResponse(enabled=SettingsService.get_sales_code_enabled(db))


@router.put("/settings/sales-code-enabled", response_model=SalesCodeEnabledResponse)
def set_sales_code_enabled(
    payload: SalesCodeEnabledUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """切换内部销售码平台开关（仅管理员；改后前端刷新即生效，无需重启/登录服务器）"""
    SettingsService.set_sales_code_enabled(db, payload.enabled)
    return SalesCodeEnabledResponse(enabled=SettingsService.get_sales_code_enabled(db))


# ---------- 外部留言讨论区：开关 + SMTP ----------

@router.get("/settings/discuss-enabled", response_model=SalesCodeEnabledResponse)
def get_discuss_enabled(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取留言讨论区开关（登录用户可读；侧栏据此决定菜单可见）"""
    return SalesCodeEnabledResponse(enabled=SettingsService.get_discuss_enabled(db))


@router.put("/settings/discuss-enabled", response_model=SalesCodeEnabledResponse)
def set_discuss_enabled(
    payload: SalesCodeEnabledUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """切换留言讨论区开关（仅管理员；关闭后公开页显示已关闭、公开接口 404）"""
    SettingsService.set_discuss_enabled(db, payload.enabled)
    return SalesCodeEnabledResponse(enabled=SettingsService.get_discuss_enabled(db))


@router.get("/settings/smtp")
def get_smtp(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """SMTP 邮件配置（仅管理员；密码不回显，仅返回是否已配置）"""
    cfg = SettingsService.get_smtp_config(db)
    return {
        "host": cfg["host"], "port": cfg["port"], "ssl": cfg["ssl"],
        "username": cfg["username"], "sender": cfg["sender"],
        "password_set": bool(cfg["password"]),
    }


@router.put("/settings/smtp")
def set_smtp(
    payload: dict,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """保存 SMTP 配置（仅管理员；password 留空=保持现有密码）"""
    cfg = SettingsService.set_smtp_config(db, payload or {})
    return {
        "host": cfg["host"], "port": cfg["port"], "ssl": cfg["ssl"],
        "username": cfg["username"], "sender": cfg["sender"],
        "password_set": bool(cfg["password"]),
    }


@router.post("/settings/smtp/test")
def test_smtp(
    payload: dict,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """发送测试邮件到指定地址，验证 SMTP 配置有效（仅管理员）"""
    from backend.discuss.service import DiscussService
    to = str((payload or {}).get("to") or "").strip()
    if "@" not in to:
        return {"ok": False, "message": "请填写有效的收件邮箱"}
    ok = DiscussService.send_email(
        SettingsService.get_smtp_config(db), to,
        "SMTP 测试邮件", "这是一封来自留言讨论区的 SMTP 配置测试邮件。收到即配置成功。",
    )
    return {"ok": ok, "message": "已发送，请查收" if ok else "发送失败，请检查配置"}


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
