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

    def __repr__(self) -> str:
        return f"<MeetingRecord(session={self.session}, date={self.meeting_date}, status={self.status})>"
