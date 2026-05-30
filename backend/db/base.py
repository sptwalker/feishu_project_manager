from sqlalchemy.orm import DeclarativeBase
from typing import Any

class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass

# 导出 Base 供其他模块使用
__all__ = ["Base"]
