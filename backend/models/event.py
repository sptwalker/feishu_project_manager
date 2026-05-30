from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON
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

    event_type = Column(SQLEnum(EventType), nullable=False)
    entity_type = Column(SQLEnum(EntityType), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    occurred_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    change_details = Column(JSON)
    description = Column(Text)

    triggered_by_user = relationship("User", foreign_keys=[triggered_by])
