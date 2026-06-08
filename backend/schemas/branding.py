from pydantic import BaseModel, Field
from typing import Dict


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
    logo_url: str = Field("", description="侧边栏 logo 图地址（空则前端用内置默认）")
    favicon_url: str = Field("", description="favicon 地址（空则用默认）")
    theme: Dict[str, str] = Field(default_factory=dict, description="CSS 变量覆盖（仅含非空项）")
