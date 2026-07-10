"""留言讨论区独立数据库（discuss.db）

与 PM 主库物理隔离：独立 engine / 独立 Base / 独立文件。
PM 的备份、导入、迁移完全不涉及本库；本库表结构用 create_all 惰性创建
（独立小库、模块自治，不接入主库的 alembic 迁移链）。
"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from backend.core.config import get_settings

# 独立 Base：discuss 表不注册进主库 metadata，主库 create_all/alembic 不感知
DiscussBase = declarative_base()

_engine = None
_SessionLocal = None


def get_discuss_engine():
    """惰性创建 discuss 引擎（首次访问时建库建表）。"""
    global _engine, _SessionLocal
    if _engine is None:
        url = get_settings().DISCUSS_DATABASE_URL
        _engine = create_engine(
            url,
            connect_args={"check_same_thread": False} if "sqlite" in url else {},
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        # 导入模型注册到 DiscussBase 后建表（幂等）
        from backend.discuss import models  # noqa: F401
        DiscussBase.metadata.create_all(bind=_engine)
    return _engine


def get_discuss_db() -> Generator[Session, None, None]:
    """discuss 库会话依赖（FastAPI Depends 用）。"""
    get_discuss_engine()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_discuss_engine_for_tests(engine, session_factory) -> None:
    """测试专用：注入内存引擎，替换全局单例。"""
    global _engine, _SessionLocal
    _engine = engine
    _SessionLocal = session_factory
