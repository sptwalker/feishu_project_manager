"""内部销售码 API（全部仅管理员）

- 生成：校验二级密码后批量生成入库
- 核销：逐条 / 批量（批量返回失败项及原因）
- 查询：按销售码 / 生成时间区间
- 二级密码：状态 / 修改（在「系统设置 › 其他设置」调用）
"""
from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.core.dependencies import get_current_admin
from backend.models.user import User
from backend.schemas.sales_code import (
    SalesCodeResponse, GenerateRequest, RedeemRequest, RedeemResult,
    BatchRedeemRequest, BatchRedeemResponse,
    GenPasswordStatus, GenPasswordUpdate,
    PrefixResponse, PrefixCreate, PrefixUpdate,
)
from backend.models.sales_code import SalesCodePrefix
from backend.services.sales_code_service import SalesCodeService

router = APIRouter()


def _prefix_out(db: Session, row: SalesCodePrefix) -> PrefixResponse:
    """把前缀 ORM 行序列化为响应（补算已用量/剩余量）。"""
    used = SalesCodeService.count_by_prefix(db, row.prefix)
    remaining = None if row.max_count is None else max(row.max_count - used, 0)
    return PrefixResponse(
        id=row.id, prefix=row.prefix, remark=row.remark, max_count=row.max_count,
        disabled=row.disabled, created_by=row.created_by, created_at=row.created_at,
        used=used, remaining=remaining,
    )


@router.post("/sales-codes/generate", response_model=list[SalesCodeResponse])
def generate_sales_codes(
    payload: GenerateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """批量生成销售码（管理员）：先校验二级密码，通过后按前缀生成入库，返回生成的码列表。"""
    if not SalesCodeService.verify_gen_password(db, payload.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="二级密码错误")
    try:
        rows = SalesCodeService.generate_batch(
            db, payload.count, payload.issued_to, current_admin, payload.prefix)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return rows


@router.post("/sales-codes/redeem", response_model=RedeemResult)
def redeem_sales_code(
    payload: RedeemRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """逐条核销（管理员）：查询成功即核销，否则返回失败原因。"""
    ok, reason, rec = SalesCodeService.redeem_one(db, payload.code, current_admin)
    return RedeemResult(ok=ok, reason=reason, record=rec)


@router.post("/sales-codes/redeem-batch", response_model=BatchRedeemResponse)
def redeem_sales_codes_batch(
    payload: BatchRedeemRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """批量核销（管理员）：核销所有可核销的码，失败项返回原因。"""
    result = SalesCodeService.redeem_batch(db, payload.codes, current_admin)
    return BatchRedeemResponse(**result)


@router.get("/sales-codes", response_model=list[SalesCodeResponse])
def query_sales_codes(
    code: Optional[str] = Query(None, description="销售码（模糊匹配）"),
    prefix: Optional[str] = Query(None, description="前缀（精确匹配）"),
    start: Optional[date] = Query(None, description="生成时间起（含当日）"),
    end: Optional[date] = Query(None, description="生成时间止（含当日）"),
    redeemed: Optional[bool] = Query(None, description="是否已核销"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """查询销售码（管理员）：按销售码 / 前缀 / 生成时间区间 / 核销状态过滤。"""
    start_dt = datetime.combine(start, time.min) if start else None
    end_dt = datetime.combine(end, time.max) if end else None
    return SalesCodeService.query(
        db, code=code, prefix=prefix, start=start_dt, end=end_dt, redeemed=redeemed)


# ---------- 前缀库 ----------

@router.get("/sales-codes/prefixes", response_model=list[PrefixResponse])
def list_prefixes(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """列出前缀库（管理员）：含每个前缀的已用量/剩余量。"""
    return SalesCodeService.list_prefixes(db)


@router.post("/sales-codes/prefixes", response_model=PrefixResponse)
def create_prefix(
    payload: PrefixCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """新增前缀（管理员）：≤8 位大写字母数字，可设备注与数量上限。"""
    try:
        row = SalesCodeService.create_prefix(
            db, payload.prefix, payload.remark, payload.max_count, current_admin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _prefix_out(db, row)


@router.put("/sales-codes/prefixes/{prefix_id}", response_model=PrefixResponse)
def update_prefix(
    prefix_id: int,
    payload: PrefixUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """启用/禁用前缀（管理员）。禁用后不可再用于生成，已生成的码不受影响。"""
    try:
        row = SalesCodeService.set_prefix_disabled(db, prefix_id, payload.disabled)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _prefix_out(db, row)


@router.get("/sales-codes/gen-password/status", response_model=GenPasswordStatus)
def get_gen_password_status(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """生成二级密码状态（管理员）：是否仍为初始密码。不回传密码本身。"""
    return GenPasswordStatus(is_default=SalesCodeService.is_gen_password_default(db))


@router.put("/sales-codes/gen-password", response_model=GenPasswordStatus)
def set_gen_password(
    payload: GenPasswordUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """修改生成二级密码（管理员）。改后立即生效。"""
    try:
        SalesCodeService.set_gen_password(db, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return GenPasswordStatus(is_default=SalesCodeService.is_gen_password_default(db))
