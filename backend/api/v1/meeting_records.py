"""周会记录归档 API

- 翻阅历史周会（登录可读）：sessions 列表、某次详情
- 开启/关闭周会（管理员）：归档落库 + 切换周会模式
- 发送会议记录到飞书（管理员）：生成飞书文档并分享到核心群
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.core.dependencies import get_current_user, get_current_admin
from backend.models.user import User
from backend.schemas.meeting_record import (
    MeetingRecordResponse, MeetingSessionsResponse, MeetingOpenRequest, MeetingSendResponse,
)
from backend.schemas.setting import MeetingStateResponse
from backend.services.meeting_record_service import MeetingRecordService
from backend.services.settings_service import SettingsService

router = APIRouter()


@router.get("/meeting-records/sessions", response_model=MeetingSessionsResponse)
def list_meeting_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """可翻阅的周会次数列表（翻页边界）"""
    return MeetingRecordService.list_sessions(db)


@router.get("/meeting-records/{session}", response_model=MeetingRecordResponse)
def get_meeting_record(
    session: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """某次周会详情（归档快照优先，否则动态扫描）"""
    return MeetingRecordService.get_session_detail(db, session)


@router.post("/meeting-records/open", response_model=MeetingRecordResponse)
def open_meeting(
    payload: MeetingOpenRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """开启周会（管理员）：确认计次/记录人/会议日期后开启，自动结束上一次未归档的周会"""
    return MeetingRecordService.open_meeting(
        db, payload.session, payload.recorder, payload.meeting_date, created_by=current_admin.id,
    )


@router.post("/meeting-records/close", response_model=MeetingStateResponse)
def close_meeting(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """关闭周会（管理员）：归档当前进行中的周会并关闭周会模式"""
    MeetingRecordService.close_meeting(db)
    return SettingsService.get_meeting_state(db)


@router.post("/meeting-records/{session}/send", response_model=MeetingSendResponse)
async def send_meeting_record(
    session: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """发送会议记录（管理员）：生成飞书文档并分享到核心组群"""
    return await MeetingRecordService.send_meeting(db, session)
