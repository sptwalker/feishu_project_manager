from pydantic import BaseModel, Field, ConfigDict, HttpUrl, field_validator
from typing import Optional, List
from datetime import datetime
from backend.models.user import UserRole, UserStatus, DISCUSS_PERM_KEYS

class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    name_en: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)

class UserCreate(UserBase):
    feishu_user_id: str = Field(..., min_length=1, max_length=100)
    avatar_url: Optional[HttpUrl] = Field(None)

class UserInDB(UserBase):
    id: int
    feishu_user_id: str
    avatar_url: Optional[HttpUrl]
    role: UserRole
    status: UserStatus
    discuss_perms: List[str] = Field(default_factory=list, description="留言区权限键列表")
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("discuss_perms", mode="before")
    @classmethod
    def _split_perms(cls, v):
        """模型存的是 CSV 字符串；对外拆成 list。已是 list 则原样返回。"""
        if isinstance(v, str):
            return [p for p in v.split(",") if p]
        return v or []

class UserResponse(UserInDB):
    pass

class UserRoleUpdate(BaseModel):
    role: UserRole

class UserStatusUpdate(BaseModel):
    """管理员审批：设置用户准入状态"""
    status: UserStatus

class UserUpdate(BaseModel):
    """管理员编辑用户：所有字段可选"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    name_en: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    role: Optional[UserRole] = Field(None)
    # 留言区权限：仅接受白名单键（未知键静默丢弃），service 层落成 CSV
    discuss_perms: Optional[List[str]] = Field(None)

    @field_validator("discuss_perms")
    @classmethod
    def _filter_perms(cls, v):
        if v is None:
            return v
        return [k for k in dict.fromkeys(v) if k in DISCUSS_PERM_KEYS]
