from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "Feishu Project Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/feishu_pm.db"
    DATABASE_ECHO: bool = False  # SQL 日志

    @property
    def async_database_url(self) -> str:
        """获取异步数据库 URL"""
        if self.DATABASE_URL.startswith("sqlite"):
            return self.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
        elif self.DATABASE_URL.startswith("postgresql"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL

    # JWT 配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 飞书应用配置
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/feishu/callback"
    FEISHU_VERIFICATION_TOKEN: str = ""
    FEISHU_ENCRYPT_KEY: str = ""

    # 飞书消息通知（安全闸：默认关闭，开启后才会真实外发消息）
    FEISHU_NOTIFY_ENABLED: bool = False

    # 飞书多维表格（Bitable）同步
    FEISHU_BITABLE_APP_TOKEN: str = ""
    FEISHU_BITABLE_PROJECT_TABLE_ID: str = ""
    FEISHU_BITABLE_TASK_TABLE_ID: str = ""

    # 前端配置
    FRONTEND_URL: str = "http://localhost:3000"

    # 系统配置
    TIMEZONE: str = "Asia/Shanghai"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost"]

    class Config:
        env_file = Path(__file__).parent.parent / ".env"
        case_sensitive = True

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """验证JWT密钥强度"""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        if "your-secret-key" in v.lower() or "change-in-production" in v.lower():
            raise ValueError("SECRET_KEY must be changed from default value in production")
        return v


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
