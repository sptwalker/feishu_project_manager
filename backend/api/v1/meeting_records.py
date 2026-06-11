"""周会记录归档 API

- 翻阅历史周会（登录可读）：sessions 列表、某次详情
- 开启/关闭周会（管理员）：归档落库 + 切换周会模式
- 发送会议记录到飞书（管理员）：生成飞书文档并分享到核心群
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.core.dependencies import get_current_user, get_current_admin
from backend.models.user import User
from backend.schemas.meeting_record import (
    MeetingRecordResponse, MeetingSessionsResponse, MeetingOpenRequest, MeetingSendResponse,
    TimerStateResponse, TimerClientRequest, TimerControlRequest, TimerTakeoverRequest,
)
from backend.schemas.setting import MeetingStateResponse
from backend.services.meeting_record_service import MeetingRecordService
from backend.services.settings_service import SettingsService
from backend.services.notification_service import NotificationService
from backend.services.operation_log_service import OperationLogService
from backend.services.meeting_timer_service import (
    MeetingTimerService, NoActiveMeeting, NotController, ControllerPresent, VersionConflict,
)
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
    """记录周会汇报开始时刻（管理员）。幂等：已开始则不覆盖，且不重复记日志。"""
    # 仅「首次开始」才记一条日志——避免每次进入/刷新汇报页都记，造成日志刷屏
    if MeetingRecordService.start_report(db, session):
        OperationLogService.log(
            db, user=current_admin, action="meeting_report_start",
            description=f"开始第 {session} 次周会汇报",
        )
    return MeetingRecordService.get_session_detail(db, session)


# ---------- 服务端计时 + 主控 ----------

@router.get("/meeting/timer/state", response_model=TimerStateResponse)
def get_timer_state(
    client_id: str = Query("", description="本端浏览器 client_id（用于判定我的角色）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """读计时状态（含惰性掉线/释放判定 + server_now）。登录可读，供主控与协助端轮询。"""
    return MeetingTimerService.get_state(db, client_id or None)


@router.post("/meeting/timer/claim", response_model=TimerStateResponse)
def claim_timer(
    payload: TimerClientRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """认领主控（管理员）：无主控时成为主控，已有他人主控则返回协助态。"""
    try:
        return MeetingTimerService.claim(db, payload.client_id)
    except NoActiveMeeting:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前没有进行中的周会")


@router.post("/meeting/timer/heartbeat", response_model=TimerStateResponse)
def heartbeat_timer(
    payload: TimerClientRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """主控心跳（管理员）：刷新存活；掉线自动暂停后重连则自动继续。"""
    try:
        return MeetingTimerService.heartbeat(db, payload.client_id)
    except NoActiveMeeting:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前没有进行中的周会")


@router.post("/meeting/timer/control", response_model=TimerStateResponse)
def control_timer(
    payload: TimerControlRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """主控计时控制（管理员）：resume/pause/select_presenter。非主控返回 403。"""
    try:
        return MeetingTimerService.control(
            db, payload.client_id, payload.action,
            {"presenter_key": payload.presenter_key},
        )
    except NoActiveMeeting:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前没有进行中的周会")
    except NotController:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="非主控客户端，无权操作计时")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/meeting/timer/takeover", response_model=TimerStateResponse)
def takeover_timer(
    payload: TimerTakeoverRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """接管主控（管理员）：仅当主控已释放（掉线超 3 分钟）时可接管。"""
    try:
        return MeetingTimerService.takeover(db, payload.client_id, payload.expected_version)
    except NoActiveMeeting:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前没有进行中的周会")
    except ControllerPresent:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="主控仍在线，无法接管")
    except VersionConflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已有他人接管，请刷新")
