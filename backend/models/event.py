from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from backend.models.base import BaseModel

class EventType(str, enum.Enum):
    STATUS_CHANGE = "status_change"
    ASSIGNEE_CHANGE = "assignee_change"
    PROGRESS_UPDATE = "progress_update"
    DATE_ADJUST = "date_adjust"
    RISK_EVENT = "risk_event"
    ASSOCIATION = "association"
    SYSTEM_EVENT = "system_event"

class EntityType(str, enum.Enum):
    PROJECT = "project"
    TASK = "task"
    MEETING = "meeting"

class Event(BaseModel):
    __tablename__ = "events"

    event_type = Column(SQLEnum(EventType), nullable=False, comment="事件类型")
    entity_type = Column(SQLEnum(EntityType), nullable=False, index=True, comment="实体类型")
    entity_id = Column(Integer, nullable=False, index=True, comment="实体ID")
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="触发用户ID")
    occurred_at = Column(DateTime, default=func.now(), nullable=False, index=True, comment="发生时间")
    change_details = Column(JSON, comment="变更详情")
    description = Column(Text, comment="事件描述")

    __table_args__ = (
        Index('ix_events_entity', 'entity_type', 'entity_id'),
    )

    triggered_by_user = relationship("User", foreign_keys=[triggered_by])

    def __repr__(self):
        return f"<Event(id={self.id}, type={self.event_type}, entity={self.entity_type}:{self.entity_id})>"
