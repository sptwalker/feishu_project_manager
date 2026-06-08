"""品牌配置接口测试

- 公开可访问（无需登录）
- 默认值字段完整
- BRAND_* env 覆盖后接口反映新值，theme 只含非空项
"""
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import get_settings


def test_branding_public_and_complete():
    """/branding 公开可访问（无 token 200），字段完整，默认无 theme 覆盖。"""
    with TestClient(app) as client:
        r = client.get("/api/v1/branding")
    assert r.status_code == 200
    data = r.json()
    for k in ("brand_sidebar", "brand_login", "brand_mark", "page_title",
              "login_headline", "login_sub", "logo_url", "favicon_url", "theme"):
        assert k in data
    assert data["page_title"] == "飞书项目管理系统"
    # 默认未配置主题色 → theme 为空（前端沿用 tokens.css）
    assert data["theme"] == {}


def test_branding_reflects_env_overrides(monkeypatch):
    """配置 BRAND_* 后接口反映新值；theme 仅含非空项。"""
    s = get_settings()
    monkeypatch.setattr(s, "BRAND_PAGE_TITLE", "营销项目管理")
    monkeypatch.setattr(s, "BRAND_LOGO_URL", "/branding/logo.png")
    monkeypatch.setattr(s, "BRAND_ACCENT", "#e8833a")
    monkeypatch.setattr(s, "BRAND_SIDEBAR_BG", "#2a1d14")
    # 其余主题项留空 → 不应进入 theme
    with TestClient(app) as client:
        r = client.get("/api/v1/branding")
    data = r.json()
    assert data["page_title"] == "营销项目管理"
    assert data["logo_url"] == "/branding/logo.png"
    assert data["theme"]["--c-accent"] == "#e8833a"
    assert data["theme"]["--c-sidebar"] == "#2a1d14"
    assert "--c-accent-hover" not in data["theme"]   # 留空项不进 theme
