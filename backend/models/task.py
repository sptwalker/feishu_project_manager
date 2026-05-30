from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, Enum as SQLEnum, CheckConstraint
from sqlalchemy.orm import relationship
import enum
from models.base import BaseModel

class TaskStatus(str, enum.Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

class TaskPriority(str, enum.Enum):
    """任务优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Task(BaseModel):
    """任务模型"""
    __tablename__ = "tasks"

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True, comment="所属项目")
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), index=True, comment="父任务ID")
    name = Column(String(200), nullable=False, comment="任务名称")
    description = Column(Text, comment="描述")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="负责人ID")
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, comment="当前状态")
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False, comment="优先级")
    completion = Column(Integer, default=0, comment="完成度(0-100)")
    due_date = Column(Date, comment="截止日期")
    start_date = Column(Date, comment="开始时间")
    end_date = Column(Date, comment="完成时间")

    __table_args__ = (
        CheckConstraint('completion >= 0 AND completion <= 100', name='check_task_completion'),
    )

    # 关系
    project = relationship("Project", back_populates="tasks")
    owner = relationship("User", back_populates="owned_tasks", foreign_keys=[owner_id])
    parent_task = relationship("Task", remote_side=[id], backref="subtasks")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name={self.name}, status={self.status})>"
