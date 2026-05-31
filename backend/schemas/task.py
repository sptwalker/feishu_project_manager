from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from typing import Optional
from backend.models.task import TaskStatus, TaskPriority

class TaskBase(BaseModel):
    """任务基础 Schema"""
    name: str = Field(..., min_length=1, max_length=200, description="任务名称")
    description: Optional[str] = Field(None, description="描述")
    owner_name: Optional[str] = Field(None, max_length=100, description="负责人姓名")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="当前状态")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="优先级")
    completion: int = Field(default=0, ge=0, le=100, description="完成度")
    due_date: Optional[date] = Field(None, description="截止日期")
    start_date: Optional[date] = Field(None, description="开始时间")
    end_date: Optional[date] = Field(None, description="完成时间")
    parent_task_id: Optional[int] = Field(None, gt=0, description="父任务ID")

class TaskCreate(TaskBase):
    """创建任务 Schema"""
    pass

class TaskUpdate(BaseModel):
    """更新任务 Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    owner_name: Optional[str] = Field(None, max_length=100)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    completion: Optional[int] = Field(None, ge=0, le=100)
    due_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    parent_task_id: Optional[int] = Field(None, gt=0)

class TaskResponse(TaskBase):
    """任务响应 Schema"""
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
