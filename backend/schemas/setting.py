from pydantic import BaseModel, Field
from typing import Optional


class LastMeeting(BaseModel):
    """上一次周例会信息"""
    date: str = Field(..., description="上次周会记录时间")
    count: int = Field(..., description="上次周会次数")


class MeetingStateResponse(BaseModel):
    """周例会状态（GET /settings/meeting）"""
    active: bool = Field(..., description="是否处于周例会记录状态")
    base_monday: str = Field(..., description="基准周一日期")
    base_count: int = Field(..., description="基准次数")
    this_week_monday: str = Field(..., description="本周周一日期")
    this_week_count: int = Field(..., description="本周周会次数")
    this_week_recorded: bool = Field(..., description="本周是否已有周会记录")
    last_meeting: Optional[LastMeeting] = Field(None, description="上一次周例会")
    calibration_count: int = Field(..., description="可校准的目标次数")
    calibration_monday: str = Field(..., description="校准对应的周一日期")
    # 事件驱动周期（新规则：上次会议日期 + new_cycle_days 天进入新周期）
    can_open_new_cycle: bool = Field(False, description="当前是否可开启新周期")
    next_count: int = Field(0, description="下次开启的周会次数")
    days_since_last: Optional[int] = Field(None, description="距上次会议日期的天数")
    new_cycle_days: int = Field(3, description="进入新周期所需的间隔天数")


class MeetingActiveUpdate(BaseModel):
    """开关周例会状态"""
    active: bool


class MeetingCountUpdate(BaseModel):
    """校准周会次数（以 calibration_monday 为基准重设）"""
    count: int = Field(..., ge=1)


class FollowupStallDaysResponse(BaseModel):
    """项目进展停滞催办天数"""
    days: int = Field(..., description="停滞催办天数阈值")


class FollowupStallDaysUpdate(BaseModel):
    """更新停滞催办天数阈值"""
    days: int = Field(..., ge=1, le=365)


class CoreGroupChatIdResponse(BaseModel):
    """周会纪要核心群 chat_id（空字符串=未配置）"""
    chat_id: str = Field("", description="核心群 chat_id")


class CoreGroupChatIdUpdate(BaseModel):
    """更新核心群 chat_id（允许空字符串=清空/不发送）"""
    chat_id: str = Field("", max_length=200)


class AutoOpenMeetingResponse(BaseModel):
    """周四自动开周会开关状态"""
    enabled: bool = Field(False, description="是否启用周四自动开周会")


class AutoOpenMeetingUpdate(BaseModel):
    """切换周四自动开周会开关"""
    enabled: bool = Field(..., description="是否启用周四自动开周会")


class AutoReminderResponse(BaseModel):
    """周会自动催更开关状态"""
    enabled: bool = Field(False, description="是否启用周会自动催更（每周五/周日）")


class AutoReminderUpdate(BaseModel):
    """切换周会自动催更开关"""
    enabled: bool = Field(..., description="是否启用周会自动催更")


class MeetingReportOrderResponse(BaseModel):
    """周会汇报顺序（部门级 + 个人级）"""
    departments: list[str] = Field(default_factory=list, description="部门汇报顺序")
    members: dict[str, list[str]] = Field(default_factory=dict, description="各部门内个人顺序")


class MeetingReportOrderUpdate(BaseModel):
    """更新周会汇报顺序"""
    departments: list[str] = Field(default_factory=list)
    members: dict[str, list[str]] = Field(default_factory=dict)


class MeetingTimerResponse(BaseModel):
    """周会计时设置"""
    total_minutes: int = Field(120, ge=1, le=600, description="总时长提醒阈值（分钟）")
    person_threshold_minutes: int = Field(5, ge=1, le=120, description="单人提醒阈值（分钟）")


class MeetingTimerUpdate(BaseModel):
    """更新周会计时设置"""
    total_minutes: int = Field(..., ge=1, le=600)
    person_threshold_minutes: int = Field(..., ge=1, le=120)


class FollowupAutoResponse(BaseModel):
    """自动定时催办配置"""
    enabled: bool = Field(False, description="是否启用自动定时催办")
    mode: str = Field("weekly", description="weekly | fixed_days | follow_meeting")
    weekday: int = Field(4, ge=0, le=6, description="星期(0=周一..6=周日)，weekly 用")
    time: str = Field("14:00", description="HH:mm，weekly/fixed_days 用")
    interval_days: int = Field(7, ge=3, le=15, description="固定间隔天数，fixed_days 用")
    follow: list[str] = Field(default_factory=list, description="follow_meeting：one=周五① two=周日②")
    last_run_date: str = Field("", description="上次执行日期(YYYY-MM-DD)")


class FollowupAutoUpdate(BaseModel):
    """更新自动定时催办配置"""
    enabled: bool = Field(False)
    mode: str = Field("weekly")
    weekday: int = Field(4, ge=0, le=6)
    time: str = Field("14:00")
    interval_days: int = Field(7, ge=3, le=15)
    follow: list[str] = Field(default_factory=list)


class FeishuAppResponse(BaseModel):
    """本实例飞书机器人应用配置（不回传密钥）"""
    app_id: str = Field("", description="飞书 App ID")
    secret_set: bool = Field(False, description="是否已配置 App Secret")


class FeishuAppUpdate(BaseModel):
    """更新飞书机器人应用凭证"""
    app_id: str = Field("", description="飞书 App ID（空则回退 .env）")
    app_secret: Optional[str] = Field(None, description="App Secret；留空则保持现有密钥")
