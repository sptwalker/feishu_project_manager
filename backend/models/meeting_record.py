from sqlalchemy import Column, Integer, String, Date, DateTime, JSON
from backend.models.base import BaseModel


class MeetingRecord(BaseModel):
    """周会记录归档表

    每次周例会一条（session 唯一）。开启周会时创建（status=active），
    关闭/结束时把当次各项目进展快照写入 content_snapshot 并置为 archived。
    会议日期、记录人在此持久化（项目进展记录本身不含这些信息）。
    """
    __tablename__ = "meeting_records"

    session = Column(Integer, unique=True, nullable=False, index=True, comment="周会次数（唯一）")
    meeting_date = Column(Date, nullable=False, comment="会议日期")
    recorder = Column(String(100), comment="记录人姓名")
    status = Column(String(20), default="active", nullable=False, comment="active=进行中 / archived=已结束")
    # 各项目进展快照：[{dept, dept_short, dept_color, project, owner, status, content, time, urgency}]
    content_snapshot = Column(JSON, default=list, comment="结束时落库的各项目进展快照")
    doc_url = Column(String(500), comment="飞书文档链接（发送后回填）")
    created_by = Column(Integer, comment="操作人用户ID（审计用，可空）")
    started_at = Column(DateTime, nullable=True, comment="汇报会议开始时刻（首次进入汇报模式时写入）")
    ended_at = Column(DateTime, nullable=True, comment="汇报会议结束时刻（归档时写入）")
    # ---- 服务端统一计时 + 主控机制（仅 active 行有效，归档时清空）----
    # 计时锚点（只存状态转移点，客户端用 now-锚点 本地推算显示）：
    # {status, total_base, total_started_at, current_presenter_key, segment_started_at, person_base{}, paused_reason}
    timer_state = Column(JSON, nullable=True, comment="服务端计时锚点（主控控制，客户端本地推算）")
    controller_client_id = Column(String(64), nullable=True, comment="当前主控浏览器 client_id；null=无主控")
    controller_heartbeat_at = Column(DateTime, nullable=True, comment="主控最后心跳时刻")
    controller_version = Column(Integer, default=0, nullable=False, server_default="0", comment="主控认领/接管 CAS 版本")

    def __repr__(self) -> str:
        return f"<MeetingRecord(session={self.session}, date={self.meeting_date}, status={self.status})>"
