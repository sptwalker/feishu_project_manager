from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from backend.db.base import Base

class TimestampMixin:
    """时间戳 Mixin"""
    created_at = Column(DateTime, default=func.now(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), server_default=func.now(), nullable=False)

class BaseModel(Base, TimestampMixin):
    """基础模型类"""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
