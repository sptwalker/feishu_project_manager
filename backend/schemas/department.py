from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class DepartmentBase(BaseModel):
    """部门基础schema"""
    name: str = Field(..., min_length=1, max_length=100, description="部门名称")
    short_name: Optional[str] = Field(None, max_length=50, description="部门简称")
    leader: Optional[str] = Field(None, max_length=100, description="负责人")
    responsibility: Optional[str] = Field(None, max_length=500, description="部门职责")
    color: Optional[str] = Field(None, max_length=20, description="显示颜色")


class DepartmentCreate(DepartmentBase):
    """创建部门"""
    pass


class DepartmentUpdate(BaseModel):
    """更新部门"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="部门名称")
    short_name: Optional[str] = Field(None, max_length=50, description="部门简称")
    leader: Optional[str] = Field(None, max_length=100, description="负责人")
    responsibility: Optional[str] = Field(None, max_length=500, description="部门职责")
    color: Optional[str] = Field(None, max_length=20, description="显示颜色")


class DepartmentInDB(DepartmentBase):
    """数据库中的部门"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DepartmentResponse(DepartmentInDB):
    """部门响应"""
    pass
