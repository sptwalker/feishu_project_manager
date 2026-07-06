"""品牌/表现差异化配置（公开接口，无需登录——登录页也要显示 logo/标题）

每个实例的品牌配置：DB（系统设置，UI 可改）优先，空则回退各自 .env 的 BRAND_*。
前端启动时拉取并应用（logo / 标题文字 / 主题配色 / 自定义信息文字），实现同代码多实例 white-label。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services.settings_service import SettingsService
from backend.schemas.branding import BrandingResponse

router = APIRouter()


@router.get("/branding", response_model=BrandingResponse)
def get_branding(db: Session = Depends(get_db)) -> BrandingResponse:
    """返回本实例的品牌配置（公开）。逐字段 DB 优先、空回退 .env；主题色仅返回非空项。"""
    c = SettingsService.get_branding_config(db)
    theme: dict[str, str] = {}
    if c.get("accent"):
        theme["--c-accent"] = c["accent"]
    if c.get("accent_hover"):
        theme["--c-accent-hover"] = c["accent_hover"]
    if c.get("accent_soft"):
        theme["--c-accent-soft"] = c["accent_soft"]
    if c.get("sidebar_bg"):
        theme["--c-sidebar"] = c["sidebar_bg"]
    if c.get("sidebar_hover"):
        theme["--c-sidebar-hover"] = c["sidebar_hover"]
    return BrandingResponse(
        brand_sidebar=c["brand_sidebar"],
        brand_login=c["brand_login"],
        brand_mark=c["brand_mark"],
        page_title=c["page_title"],
        login_headline=c["login_headline"],
        login_sub=c["login_sub"],
        org_scope=c["org_scope"],
        dept_unit=c["dept_unit"],
        logo_url=c["logo_url"],
        favicon_url=c["favicon_url"],
        theme=theme,
        sales_code_enabled=SettingsService.get_sales_code_enabled(db),
    )
