from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from backend.models.base import Base


class Department(Base):
    """部门模型"""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True, comment="部门名称")
    short_name = Column(String(50), nullable=True, comment="部门简称")
    leader = Column(String(100), nullable=True, comment="负责人")
    responsibility = Column(String(500), nullable=True, comment="部门职责")
    color = Column(String(20), nullable=True, comment="显示颜色")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
