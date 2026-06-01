from sqlalchemy import Column, Integer, String, Text, Date, Boolean, Enum as SQLEnum, CheckConstraint, JSON
from sqlalchemy.orm import relationship
import enum
from backend.models.base import BaseModel

class ProjectStatus(str, enum.Enum):
    """项目状态枚举"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ProjectUrgency(str, enum.Enum):
    """紧急程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Project(BaseModel):
    """项目模型"""
    __tablename__ = "projects"

    name = Column(String(200), nullable=False, comment="项目名称")
    record_date = Column(Date, nullable=False, comment="记录日期")
    content = Column(Text, comment="内容描述")
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PLANNED, nullable=False, comment="当前状态")
    urgency = Column(SQLEnum(ProjectUrgency), default=ProjectUrgency.MEDIUM, nullable=False, comment="紧急程度")
    department = Column(String(100), comment="负责部门")
    owner_name = Column(String(100), comment="负责人姓名（与用户账号解耦）")
    related_name = Column(String(200), comment="相关人")
    completion = Column(Integer, default=0, comment="完成度(0-100)")
    is_long_term = Column(Boolean, default=False, nullable=False, comment="长期项目（不显示完成度）")
    estimated_end_date = Column(Date, comment="预计完成时间")
    actual_end_date = Column(Date, comment="实际完成时间")
    # 项目进展记录：[{time, content, status}] 列表
    progress_log = Column(JSON, default=list, comment="项目进展记录")

    __table_args__ = (
        CheckConstraint('completion >= 0 AND completion <= 100', name='check_project_completion'),
    )

    # 关系（项目不再关联负责人用户账号，仅保留下属任务/风险）
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    risks = relationship("Risk", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, status={self.status})>"
