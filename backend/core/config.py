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

    # 图片上传（进展详情配图）。本地默认 backend/data/uploads；
    # Docker 通过 env 设 /data/uploads（在 backend_data 卷内，自动持久化）
    UPLOAD_DIR: str = "backend/data/uploads"
    UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024  # 单图上限 10MB

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
    # 定时任务防漏：错过触发后多久内仍补执行（秒）。默认 4 小时——
    # 容器重启/部署窗口恰好跨过触发时刻时，恢复后仍会补跑一次，避免遗漏。
    SCHEDULER_MISFIRE_GRACE_TIME: int = 14400

    # 周会定时自动开启（独立开关，不依赖 SCHEDULER_ENABLED）
    AUTO_OPEN_MEETING_ENABLED: bool = False   # 每周四自动开周会总开关
    AUTO_MEETING_DAY: str = "thu"             # 自动开启的星期（cron day_of_week）
    AUTO_MEETING_HOUR: int = 14               # 自动开启的小时（14:00）
    AUTO_MEETING_MINUTE: int = 0              # 自动开启的分钟
    AUTO_MEETING_RECORDER: str = "Shineleo"   # 自动开启时的默认记录人
    # 周会自动催更：开启后每周五/周日定时在核心群发进展更新催办（运行时开关存 DB）
    AUTO_REMINDER1_DAY: str = "fri"           # 第一次催更（开启后约 1 天）
    AUTO_REMINDER2_DAY: str = "sun"           # 第二次催更（开启后约 3 天，会议前一天）
    AUTO_REMINDER_HOUR: int = 14              # 催更时间（14:00）
    AUTO_REMINDER_MINUTE: int = 0
    # 周会周期递进：上次会议日期 + N 天即可进入新周期（替代原“跨自然周”规则）
    NEW_CYCLE_DAYS: int = 3
    # 判定“真正召开过”的最短汇报时长（分钟）：已启动汇报(started_at)且持续≥此值才算已召开。
    # 用于排除“自动开启但没真正开会”的空会，避免它被当成“上一次周会”锚定冷却期。
    MEETING_HELD_MIN_MINUTES: int = 60
    # 系统对外访问地址（周会通知文案里引导成员登录更新进展）
    SYSTEM_PUBLIC_URL: str = "https://pms.youdoogo.com/"

    # 提醒阈值
    REMINDER_DUE_SOON_DAYS: int = 3  # 临期：N 天内到期
    FOLLOWUP_STALE_DAYS: int = 3     # 进度跟催：进行中且 N 天未更新
    # 周报接收人（飞书用户ID，为空则不发送）
    FEISHU_REPORT_RECEIVER_ID: str = ""
    # 项目进展催办的目标飞书群（chat_id，为空则不发送）
    FEISHU_PROJECT_GROUP_CHAT_ID: str = ""
    # 周会纪要分享的核心组群（chat_id，为空则不发送）
    # 注：已迁移到「系统设置 › 其他设置」(DB)，send_meeting 不再读此项；保留定义仅作兼容
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

    # ========== 品牌/表现差异化（多实例 white-label：每套系统可不同，空则前端用内置默认）==========
    # 文字（支持可信 HTML：仅来自本配置，不接受用户输入，前端 v-html 渲染）
    BRAND_SIDEBAR: str = '<span class="brand-accent">P</span>roject <span class="brand-accent">M</span>anager'
    BRAND_LOGIN: str = '飞书<span class="accent">PM</span>'   # 登录页品牌名
    BRAND_MARK: str = "飞"                                   # 登录页左上方块标记字符
    BRAND_PAGE_TITLE: str = "飞书项目管理系统"                # 浏览器标签标题
    BRAND_LOGIN_HEADLINE: str = '把中长期项目<br />管理得<span class="accent">轻盈</span>。'  # 登录页主标语
    BRAND_LOGIN_SUB: str = "里程碑 · 任务 · 风险 · 飞书联动 —— 一处掌握全局。"               # 登录页副标语
    # 首页副标题口径：组织范围词 + 部门单位词（多实例差异化，如 sales=营销销售部/团队）
    BRAND_ORG_SCOPE: str = "全公司"                          # 首页副标题"涵盖{X}"的范围词
    BRAND_DEPT_UNIT: str = "部门"                            # 首页副标题"N 个{X}"的单位词
    # 图片（相对路径，由各实例 Nginx /branding/ 提供；空则前端用构建内置默认 logo/favicon）
    BRAND_LOGO_URL: str = ""
    BRAND_FAVICON_URL: str = ""
    # 主题色（覆盖 :root CSS 变量；留空则该项不覆盖，沿用 tokens.css 默认）
    BRAND_ACCENT: str = ""
    BRAND_ACCENT_HOVER: str = ""
    BRAND_ACCENT_SOFT: str = ""
    BRAND_SIDEBAR_BG: str = ""
    BRAND_SIDEBAR_HOVER: str = ""

    # 系统配置
    TIMEZONE: str = "Asia/Shanghai"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost"]

    # 内部销售码管理平台（部署级开关：仅 sales 租户实例开启；经公开 /branding 下发前端控制菜单可见）
    SALES_CODE_ENABLED: bool = False

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
