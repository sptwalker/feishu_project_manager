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
