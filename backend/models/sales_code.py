from sqlalchemy import Column, Integer, String, Boolean, DateTime
from backend.models.base import BaseModel


class SalesCode(BaseModel):
    """内部销售码

    管理员批量生成的随机销售码，逐条/批量核销。created_at 即"生成时间"。
    码形如 "PREFIX-XXXXXXXX"：prefix 来自前缀库（≤8 位大写），后段为 8 位随机大写字母数字。
    generated_by / redeemed_by 为姓名快照（仿 operation_log，改名/删号后记录仍可读）。
    """
    __tablename__ = "sales_codes"

    code = Column(String(32), unique=True, nullable=False, index=True, comment="销售码（前缀-随机，唯一）")
    prefix = Column(String(8), nullable=False, default="", index=True, comment="前缀（用于按前缀查询/限额统计）")
    generated_by = Column(String(100), nullable=False, default="", comment="生成人姓名快照")
    generated_by_id = Column(Integer, comment="生成人用户ID（审计，可空）")
    issued_to = Column(String(200), nullable=False, default="", comment="发放对象")
    redeemed = Column(Boolean, default=False, nullable=False, index=True, comment="是否已核销")
    redeemed_at = Column(DateTime, nullable=True, comment="核销时间")
    redeemed_by = Column(String(100), nullable=True, comment="核销人姓名快照")

    def __repr__(self) -> str:
        return f"<SalesCode(code={self.code}, redeemed={self.redeemed})>"


class SalesCodePrefix(BaseModel):
    """销售码前缀库

    管理员自定义的前缀（≤8 位大写字母数字），生成销售码时选用。
    max_count 为该前缀允许生成的销售码上限（None=无限制）；disabled 后不可再用于生成。
    """
    __tablename__ = "sales_code_prefixes"

    prefix = Column(String(8), unique=True, nullable=False, index=True, comment="前缀（大写字母数字，≤8位）")
    remark = Column(String(200), nullable=False, default="", comment="备注")
    max_count = Column(Integer, nullable=True, comment="数量上限（空=无限制）")
    disabled = Column(Boolean, default=False, nullable=False, comment="是否禁用")
    created_by = Column(String(100), nullable=False, default="", comment="添加者姓名快照")
    created_by_id = Column(Integer, comment="添加者用户ID（审计，可空）")

    def __repr__(self) -> str:
        return f"<SalesCodePrefix(prefix={self.prefix}, disabled={self.disabled})>"
