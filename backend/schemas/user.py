from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from models.user import UserRole

class UserBase(BaseModel):
    name: str = Field(..., max_length=100)
    department: Optional[str] = Field(None, max_length=100)

class UserCreate(UserBase):
    feishu_user_id: str = Field(..., max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)

class UserInDB(UserBase):
    id: int
    feishu_user_id: str
    avatar_url: Optional[str]
    role: UserRole
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserResponse(UserInDB):
    pass
