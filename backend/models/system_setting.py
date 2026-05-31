from sqlalchemy import Column, String, Text
from backend.models.base import BaseModel


class SystemSetting(BaseModel):
    """系统全局配置（key-value），供周例会状态、AI/主题等全局设置复用"""
    __tablename__ = "system_settings"

    key = Column(String(100), unique=True, nullable=False, index=True, comment="配置键")
    value = Column(Text, nullable=True, comment="配置值（字符串/JSON）")

    def __repr__(self) -> str:
        return f"<SystemSetting(key={self.key}, value={self.value})>"
