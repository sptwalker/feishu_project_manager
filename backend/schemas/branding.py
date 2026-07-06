from pydantic import BaseModel, Field
from typing import Dict, Optional


class BrandingResponse(BaseModel):
    """品牌/表现差异化配置（公开接口，登录页也要用）。

    每个实例从自己的 .env 读取 BRAND_* 配置，前端启动时拉取并应用。
    文字字段为可信 HTML（仅来自后端配置，不接受用户输入）。
    """
    brand_sidebar: str = Field(..., description="侧边栏品牌名（HTML）")
    brand_login: str = Field(..., description="登录页品牌名（HTML）")
    brand_mark: str = Field(..., description="登录页方块标记字符")
    page_title: str = Field(..., description="浏览器标签标题")
    login_headline: str = Field(..., description="登录页主标语（HTML）")
    login_sub: str = Field(..., description="登录页副标语")
    org_scope: str = Field("全公司", description="首页副标题范围词（如 全公司 / 营销销售部）")
    dept_unit: str = Field("部门", description="首页副标题部门单位词（如 部门 / 团队）")
    logo_url: str = Field("", description="侧边栏 logo 图地址（空则前端用内置默认）")
    favicon_url: str = Field("", description="favicon 地址（空则用默认）")
    theme: Dict[str, str] = Field(default_factory=dict, description="CSS 变量覆盖（仅含非空项）")
    sales_code_enabled: bool = Field(False, description="是否启用内部销售码管理（部署级；控制菜单可见）")


class BrandingFull(BaseModel):
    """品牌完整配置（管理员读/写，颜色为扁平字段）。"""
    brand_sidebar: str = ""
    brand_login: str = ""
    brand_mark: str = ""
    page_title: str = ""
    login_headline: str = ""
    login_sub: str = ""
    org_scope: str = ""
    dept_unit: str = ""
    logo_url: str = ""
    favicon_url: str = ""
    accent: str = ""
    accent_hover: str = ""
    accent_soft: str = ""
    sidebar_bg: str = ""
    sidebar_hover: str = ""


class BrandingUpdate(BaseModel):
    """品牌更新（仅传入的字段会被写入；None 跳过、空串=清空回退 .env）。"""
    brand_sidebar: Optional[str] = None
    brand_login: Optional[str] = None
    brand_mark: Optional[str] = None
    page_title: Optional[str] = None
    login_headline: Optional[str] = None
    login_sub: Optional[str] = None
    org_scope: Optional[str] = None
    dept_unit: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    accent: Optional[str] = None
    accent_hover: Optional[str] = None
    accent_soft: Optional[str] = None
    sidebar_bg: Optional[str] = None
    sidebar_hover: Optional[str] = None
