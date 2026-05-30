from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from models.base import BaseModel

class RiskStatus(str, enum.Enum):
    OPEN = "open"
    MONITORING = "monitoring"
    RESOLVED = "resolved"

class Risk(BaseModel):
    __tablename__ = "risks"

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True, comment="项目ID")
    title = Column(String(200), nullable=False, comment="风险标题")
    description = Column(Text, comment="风险描述")
    status = Column(SQLEnum(RiskStatus), default=RiskStatus.OPEN, nullable=False, index=True, comment="风险状态")
    owner_id = Column(Integer, ForeignKey("users.id"), comment="负责人ID")

    project = relationship("Project", back_populates="risks")

    def __repr__(self):
        return f"<Risk(id={self.id}, title={self.title}, status={self.status})>"
