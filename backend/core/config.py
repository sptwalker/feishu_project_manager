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
    DATABASE_URL: str = "sqlite:///./backend/data/feishu_pm.db"
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

    # 定时任务调度（安全闸：默认关闭，开启后才会启动后台调度线程）
    SCHEDULER_ENABLED: bool = False
    # 各定时任务的触发时间（cron，本地时区 TIMEZONE）
    REMINDER_HOUR: int = 9            # 逾期/临期/里程碑提醒：每天 09:00
    FOLLOWUP_HOUR: int = 10          # 进度跟催：每天 10:00
    PROJECT_FOLLOWUP_HOUR: int = 9   # 项目进展催办：每天 09:30
    PROJECT_FOLLOWUP_MINUTE: int = 30
    WEEKLY_REPORT_DAY: str = "mon"   # 周报：周一
    WEEKLY_REPORT_HOUR: int = 9      # 周报：09:00
    # 提醒阈值
    REMINDER_DUE_SOON_DAYS: int = 3  # 临期：N 天内到期
    FOLLOWUP_STALE_DAYS: int = 3     # 进度跟催：进行中且 N 天未更新
    # 周报接收人（飞书用户ID，为空则不发送）
    FEISHU_REPORT_RECEIVER_ID: str = ""
    # 项目进展催办的目标飞书群（chat_id，为空则不发送）
    FEISHU_PROJECT_GROUP_CHAT_ID: str = ""
    # 周会纪要分享的核心组群（chat_id，为空则不发送）
    FEISHU_CORE_GROUP_CHAT_ID: str = ""
    # 飞书文档链接前缀（租户域名，如 https://xxx.feishu.cn；用于拼 docx 链接）
    FEISHU_DOC_URL_PREFIX: str = "https://feishu.cn"

    # 初始管理员：这些飞书 open_id 的用户登录时自动确保为管理员
    # 用途：外网全新部署后，无需手动改库即可让指定人员成为管理员去配置系统
    # 注意：open_id 仅对同一个飞书自建应用（同 FEISHU_APP_ID）恒定，换应用需更新此项
    # 默认：刘丹
    INITIAL_ADMIN_FEISHU_IDS: list[str] = ["ou_bf1b517ee3c1a8d508e1c0947aa6f5a9"]

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
