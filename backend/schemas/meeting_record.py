from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List


class MeetingItem(BaseModel):
    """周会纪要单条（某项目在该次周会的最新进展快照）"""
    dept: Optional[str] = None
    dept_short: Optional[str] = None
    dept_color: Optional[str] = None
    project: str
    owner: Optional[str] = None
    status: str = ""
    content: str = ""
    time: str = ""
    urgency: str = "medium"


class MeetingRecordResponse(BaseModel):
    """某次周会详情"""
    session: int
    meeting_date: Optional[str] = None
    recorder: Optional[str] = None
    status: str = "archived"
    doc_url: Optional[str] = None
    items: List[MeetingItem] = Field(default_factory=list)


class MeetingSessionsResponse(BaseModel):
    """可翻阅的周会次数列表（翻页边界）"""
    sessions: List[int] = Field(default_factory=list)
    current: int


class MeetingOpenRequest(BaseModel):
    """开启周会"""
    session: int = Field(..., ge=1, description="本次周会次数")
    recorder: Optional[str] = Field(None, max_length=100, description="记录人")
    meeting_date: date = Field(..., description="会议日期")
    end_previous: bool = Field(False, description="是否先结束上一次未归档的周会")


class MeetingSendResponse(BaseModel):
    """发送会议记录结果"""
    ok: bool
    doc_url: Optional[str] = None
    message: str = ""
