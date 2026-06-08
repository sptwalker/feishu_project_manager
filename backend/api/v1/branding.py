"""品牌/表现差异化配置（公开接口，无需登录——登录页也要显示 logo/标题）

每个实例从自己的 .env 读取 BRAND_* 配置；前端启动时拉取并应用
（logo / 标题文字 / 主题配色 / 自定义信息文字），实现同代码多实例 white-label。
"""
from fastapi import APIRouter

from backend.core.config import get_settings
from backend.schemas.branding import BrandingResponse

router = APIRouter()


@router.get("/branding", response_model=BrandingResponse)
def get_branding() -> BrandingResponse:
    """返回本实例的品牌配置（公开）。主题色仅返回非空项，前端只覆盖这些 CSS 变量。"""
    s = get_settings()
    # 主题色：只收集配置了的项，前端按此覆盖 :root；未配置的沿用 tokens.css 默认
    theme: dict[str, str] = {}
    if s.BRAND_ACCENT:
        theme["--c-accent"] = s.BRAND_ACCENT
    if s.BRAND_ACCENT_HOVER:
        theme["--c-accent-hover"] = s.BRAND_ACCENT_HOVER
    if s.BRAND_ACCENT_SOFT:
        theme["--c-accent-soft"] = s.BRAND_ACCENT_SOFT
    if s.BRAND_SIDEBAR_BG:
        theme["--c-sidebar"] = s.BRAND_SIDEBAR_BG
    if s.BRAND_SIDEBAR_HOVER:
        theme["--c-sidebar-hover"] = s.BRAND_SIDEBAR_HOVER
    return BrandingResponse(
        brand_sidebar=s.BRAND_SIDEBAR,
        brand_login=s.BRAND_LOGIN,
        brand_mark=s.BRAND_MARK,
        page_title=s.BRAND_PAGE_TITLE,
        login_headline=s.BRAND_LOGIN_HEADLINE,
        login_sub=s.BRAND_LOGIN_SUB,
        logo_url=s.BRAND_LOGO_URL,
        favicon_url=s.BRAND_FAVICON_URL,
        theme=theme,
    )
