from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass

# 导出 Base 供其他模块使用
__all__ = ["Base"]
