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
from backend.services.notification_service import NotificationService
from backend.services.operation_log_service import OperationLogService
from backend.core.config import get_settings

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
async def open_meeting(
    payload: MeetingOpenRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """开启周会（管理员）：确认计次/记录人/会议日期后开启，自动结束上一次未归档的周会。
    若本次开启进入了新周期，向飞书核心群发开启通知（文案C，带管理员名）。"""
    # 开启前先判断是否进入新周期（开启后 active 会变 True，故需在前面取）
    is_new_cycle = SettingsService.get_meeting_state(db)["can_open_new_cycle"]
    detail = MeetingRecordService.open_meeting(
        db, payload.session, payload.recorder, payload.meeting_date, created_by=current_admin.id,
    )
    if is_new_cycle:
        # 进入新周期：通知核心群（best-effort，失败不影响开启）
        chat_id = SettingsService.get_core_group_chat_id(db)
        await NotificationService.notify_meeting_open(
            chat_id, session=payload.session,
            public_url=get_settings().SYSTEM_PUBLIC_URL,
            operator=current_admin.name,
        )
    return detail


@router.post("/meeting-records/close", response_model=MeetingStateResponse)
def close_meeting(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """关闭周会（管理员）：归档当前进行中的周会并关闭周会模式"""
    active = SettingsService.get_active_meeting_record(db)
    session = active.session if active else None
    MeetingRecordService.close_meeting(db)
    if session is not None:
        OperationLogService.log(
            db, user=current_admin, action="meeting_report_end",
            description=f"结束第 {session} 次周会",
        )
    return SettingsService.get_meeting_state(db)


@router.post("/meeting-records/{session}/send", response_model=MeetingSendResponse)
async def send_meeting_record(
    session: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """发送会议记录（管理员）：生成飞书文档并分享到核心组群"""
    return await MeetingRecordService.send_meeting(db, session)


@router.post("/meeting-records/{session}/start-report", response_model=MeetingRecordResponse)
def start_meeting_report(
    session: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """记录周会汇报开始时刻（管理员）。幂等：已开始则不覆盖。"""
    MeetingRecordService.start_report(db, session)
    OperationLogService.log(
        db, user=current_admin, action="meeting_report_start",
        description=f"开始第 {session} 次周会汇报",
    )
    return MeetingRecordService.get_session_detail(db, session)
