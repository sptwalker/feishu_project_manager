from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from models.base import BaseModel

class UserRole(str, enum.Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    PROJECT_MANAGER = "project_manager"
    MEMBER = "member"
    OBSERVER = "observer"

class User(BaseModel):
    """用户模型"""
    __tablename__ = "users"

    feishu_user_id = Column(String(100), unique=True, nullable=False, index=True, comment="飞书用户ID")
    name = Column(String(100), nullable=False, comment="姓名")
    avatar_url = Column(String(500), comment="头像URL")
    department = Column(String(100), comment="部门")
    role = Column(SQLEnum(UserRole), default=UserRole.MEMBER, nullable=False, comment="角色")
    last_login_at = Column(DateTime, comment="最后登录时间")

    # 关系
    owned_projects = relationship("Project", back_populates="owner", foreign_keys="Project.owner_id")
    owned_tasks = relationship("Task", back_populates="owner", foreign_keys="Task.owner_id")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, role={self.role})>"
