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

# 留言区细粒度授权键（唯一真源）：与系统角色解耦，逐用户勾选。评星复用 reply。
DISCUSS_PERM_KEYS = ("reply", "hide", "delete", "block", "announce")

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
    # 留言区权限（CSV，键取自 DISCUSS_PERM_KEYS）：与系统角色脱钩，逐项授权。空串=无任何留言区权限。
    discuss_perms = Column(String(200), default="", server_default="", nullable=False, comment="留言区权限CSV")

    def has_discuss_perm(self, key: str) -> bool:
        """是否持有某留言区权限键。"""
        return key in (self.discuss_perms or "").split(",")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, role={self.role})>"
