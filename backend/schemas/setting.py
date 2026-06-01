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
