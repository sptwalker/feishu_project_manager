from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List


class SalesCodeResponse(BaseModel):
    """销售码记录"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    prefix: str = Field("", description="前缀")
    created_at: datetime = Field(..., description="生成时间")
    generated_by: str = Field("", description="生成人")
    issued_to: str = Field("", description="发放对象")
    redeemed: bool = Field(False, description="是否核销")
    redeemed_at: Optional[datetime] = Field(None, description="核销时间")
    redeemed_by: Optional[str] = Field(None, description="核销人")


class GenerateRequest(BaseModel):
    """批量生成销售码（需二级密码）"""
    count: int = Field(..., ge=1, le=1000, description="生成数量")
    prefix: str = Field(..., min_length=1, max_length=8, description="前缀（从前缀库选择）")
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


# ---------- 前缀库 ----------

class PrefixResponse(BaseModel):
    """前缀库记录（含已用量/剩余量）"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    prefix: str
    remark: str = Field("", description="备注")
    max_count: Optional[int] = Field(None, description="数量上限（空=无限制）")
    disabled: bool = Field(False, description="是否禁用")
    created_by: str = Field("", description="添加者")
    created_at: datetime = Field(..., description="添加日期")
    used: int = Field(0, description="已生成数量")
    remaining: Optional[int] = Field(None, description="剩余可生成（无限制则为空）")


class PrefixCreate(BaseModel):
    """新增前缀"""
    prefix: str = Field(..., min_length=1, max_length=8, description="前缀（大写字母数字，≤8位）")
    remark: str = Field("", max_length=200, description="备注")
    max_count: Optional[int] = Field(None, ge=1, description="数量上限（不填=无限制）")


class PrefixUpdate(BaseModel):
    """更新前缀（目前用于启用/禁用）"""
    disabled: bool = Field(..., description="是否禁用")

