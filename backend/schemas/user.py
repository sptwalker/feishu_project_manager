from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from typing import Optional
from datetime import datetime
from backend.models.user import UserRole

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
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserResponse(UserInDB):
    pass

class UserRoleUpdate(BaseModel):
    role: UserRole

class UserUpdate(BaseModel):
    """管理员编辑用户：所有字段可选"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    name_en: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    role: Optional[UserRole] = Field(None)
