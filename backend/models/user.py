from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
import enum
from backend.models.base import BaseModel

class UserRole(str, enum.Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    PROJECT_MANAGER = "project_manager"
    MEMBER = "member"
    OBSERVER = "observer"

class UserStatus(str, enum.Enum):
    """用户准入状态枚举"""
    PENDING = "pending"      # 待审批：能登录但被访问闸挡住
    ACTIVE = "active"        # 已启用：正常访问
    DISABLED = "disabled"    # 已禁用：被踢出

class User(BaseModel):
    """用户模型"""
    __tablename__ = "users"

    feishu_user_id = Column(String(100), unique=True, nullable=False, index=True, comment="飞书用户ID")
    name = Column(String(100), nullable=False, comment="姓名")
    name_en = Column(String(100), comment="英文姓名")
    position = Column(String(100), comment="职位")
    avatar_url = Column(String(500), comment="头像URL")
    department = Column(String(100), comment="部门")
    role = Column(SQLEnum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.MEMBER, nullable=False, comment="角色")
    # 准入状态：存量用户 server_default=active（不锁现有同事）；新登录用户由 auth_service 置 pending
    status = Column(
        SQLEnum(UserStatus, values_callable=lambda x: [e.value for e in x]),
        default=UserStatus.ACTIVE, server_default="active", nullable=False, index=True,
        comment="准入状态 pending待审/active启用/disabled禁用",
    )
    last_login_at = Column(DateTime, comment="最后登录时间")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, role={self.role})>"
