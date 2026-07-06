from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List


class SalesCodeResponse(BaseModel):
    """销售码记录"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    created_at: datetime = Field(..., description="生成时间")
    generated_by: str = Field("", description="生成人")
    issued_to: str = Field("", description="发放对象")
    redeemed: bool = Field(False, description="是否核销")
    redeemed_at: Optional[datetime] = Field(None, description="核销时间")
    redeemed_by: Optional[str] = Field(None, description="核销人")


class GenerateRequest(BaseModel):
    """批量生成销售码（需二级密码）"""
    count: int = Field(..., ge=1, le=1000, description="生成数量")
    issued_to: str = Field(..., min_length=1, max_length=200, description="发放对象")
    password: str = Field(..., description="生成二级密码")


class RedeemRequest(BaseModel):
    """逐条核销"""
    code: str = Field(..., min_length=1, max_length=64, description="销售码")


class RedeemResult(BaseModel):
    """逐条核销结果"""
    ok: bool
    reason: str = ""
    record: Optional[SalesCodeResponse] = None


class BatchRedeemRequest(BaseModel):
    """批量核销"""
    codes: List[str] = Field(..., description="销售码列表")


class RedeemFailure(BaseModel):
    """批量核销中的失败项"""
    code: str
    reason: str


class BatchRedeemResponse(BaseModel):
    """批量核销结果：核销成功的记录 + 失败项及原因"""
    redeemed: List[SalesCodeResponse] = Field(default_factory=list)
    failed: List[RedeemFailure] = Field(default_factory=list)


class GenPasswordStatus(BaseModel):
    """生成二级密码状态（不回传密码本身）"""
    is_default: bool = Field(True, description="是否仍为初始密码 888888")


class GenPasswordUpdate(BaseModel):
    """修改生成二级密码"""
    password: str = Field(..., min_length=4, max_length=64, description="新的二级密码")
