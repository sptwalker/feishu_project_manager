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


# ---------- 服务端计时 + 主控 ----------

class TimerStateResponse(BaseModel):
    """计时状态（锚点 + server_now + 主控信息 + 我的角色）。active=False 时仅含基础字段。"""
    active: bool
    server_now: str
    my_role: str = "none"                      # controller | assistant | none
    session: Optional[int] = None
    status: Optional[str] = None               # idle | running | paused
    total_base: Optional[int] = None
    total_started_at: Optional[str] = None
    current_presenter_key: Optional[str] = None
    segment_started_at: Optional[str] = None
    person_base: Optional[dict] = None
    paused_reason: Optional[str] = None
    controller_present: Optional[bool] = None
    controller_online: Optional[bool] = None
    controller_version: Optional[int] = None
    offline_seconds: Optional[int] = None
    release_seconds: Optional[int] = None


class TimerClientRequest(BaseModel):
    """带 client_id 的通用请求（claim / heartbeat）"""
    client_id: str = Field(..., max_length=64)


class TimerControlRequest(BaseModel):
    """主控计时控制：resume / pause / select_presenter"""
    client_id: str = Field(..., max_length=64)
    action: str = Field(..., description="resume | pause | select_presenter")
    presenter_key: Optional[str] = Field(None, description="select_presenter 时的『部门|个人』")


class TimerTakeoverRequest(BaseModel):
    """协助端接管（主控释放后）"""
    client_id: str = Field(..., max_length=64)
    expected_version: Optional[int] = Field(None, description="CAS：期望的 controller_version")
