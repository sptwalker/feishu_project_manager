from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class OperationLogResponse(BaseModel):
    """系统操作日志条目（响应）"""
    id: int
    user_name: str = Field("", description="操作人姓名")
    project_id: Optional[int] = Field(None, description="关联项目ID")
    action: str = Field("", description="动作类型")
    target: Optional[str] = Field(None, description="操作对象（如项目名）")
    description: str = Field("", description="操作描述（不含人名）")
    occurred_at: datetime = Field(..., description="发生时间")

    model_config = ConfigDict(from_attributes=True)
