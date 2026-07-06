from sqlalchemy import Column, Integer, String, Boolean, DateTime
from backend.models.base import BaseModel


class SalesCode(BaseModel):
    """内部销售码

    管理员批量生成的随机销售码，逐条/批量核销。created_at 即"生成时间"。
    generated_by / redeemed_by 为姓名快照（仿 operation_log，改名/删号后记录仍可读）。
    """
    __tablename__ = "sales_codes"

    code = Column(String(32), unique=True, nullable=False, index=True, comment="销售码（随机，唯一）")
    generated_by = Column(String(100), nullable=False, default="", comment="生成人姓名快照")
    generated_by_id = Column(Integer, comment="生成人用户ID（审计，可空）")
    issued_to = Column(String(200), nullable=False, default="", comment="发放对象")
    redeemed = Column(Boolean, default=False, nullable=False, index=True, comment="是否已核销")
    redeemed_at = Column(DateTime, nullable=True, comment="核销时间")
    redeemed_by = Column(String(100), nullable=True, comment="核销人姓名快照")

    def __repr__(self) -> str:
        return f"<SalesCode(code={self.code}, redeemed={self.redeemed})>"
