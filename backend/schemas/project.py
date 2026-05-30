from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from typing import Optional
from backend.models.project import ProjectStatus, ProjectUrgency

class ProjectBase(BaseModel):
    """项目基础 Schema"""
    name: str = Field(..., min_length=1, max_length=200, description="项目名称")
    record_date: date = Field(..., description="记录日期")
    content: Optional[str] = Field(None, description="内容描述")
    status: ProjectStatus = Field(default=ProjectStatus.PLANNED, description="当前状态")
    urgency: ProjectUrgency = Field(default=ProjectUrgency.MEDIUM, description="紧急程度")
    department: Optional[str] = Field(None, max_length=100, description="负责部门")
    owner_id: int = Field(..., gt=0, description="负责人ID")
    completion: int = Field(default=0, ge=0, le=100, description="完成度")
    estimated_end_date: Optional[date] = Field(None, description="预计完成时间")

class ProjectCreate(ProjectBase):
    """创建项目 Schema"""
    pass

class ProjectUpdate(BaseModel):
    """更新项目 Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    status: Optional[ProjectStatus] = None
    urgency: Optional[ProjectUrgency] = None
    department: Optional[str] = Field(None, max_length=100)
    owner_id: Optional[int] = Field(None, gt=0)
    completion: Optional[int] = Field(None, ge=0, le=100)
    estimated_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None

class ProjectResponse(ProjectBase):
    """项目响应 Schema"""
    id: int
    actual_end_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
