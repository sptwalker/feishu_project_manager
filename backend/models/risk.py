from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from backend.models.base import BaseModel

class RiskStatus(str, enum.Enum):
    OPEN = "open"
    MONITORING = "monitoring"
    RESOLVED = "resolved"

class Risk(BaseModel):
    __tablename__ = "risks"

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(SQLEnum(RiskStatus), default=RiskStatus.OPEN)
    owner_id = Column(Integer, ForeignKey("users.id"))

    project = relationship("Project", back_populates="risks")
