from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from backend.models.risk import RiskStatus

class RiskBase(BaseModel):
    """风险基础 Schema"""
    title: str = Field(..., min_length=1, max_length=200, description="风险标题")
    description: Optional[str] = Field(None, description="风险描述")
    status: RiskStatus = Field(default=RiskStatus.OPEN, description="风险状态")
    owner_id: Optional[int] = Field(None, gt=0, description="负责人ID")

class RiskCreate(RiskBase):
    """创建风险 Schema"""
    pass

class RiskUpdate(BaseModel):
    """更新风险 Schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[RiskStatus] = None
    owner_id: Optional[int] = Field(None, gt=0)

class RiskResponse(RiskBase):
    """风险响应 Schema"""
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
