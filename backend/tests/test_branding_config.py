"""品牌配置 DB 存取：DB 优先 / env 回退 / 部分更新合并"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.core.config import get_settings
from backend.services.settings_service import SettingsService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_branding_falls_back_to_env(db_session):
    s = get_settings()
    cfg = SettingsService.get_branding_config(db_session)
    # 未配置 → 回退 .env 默认
    assert cfg["brand_sidebar"] == s.BRAND_SIDEBAR
    assert cfg["org_scope"] == s.BRAND_ORG_SCOPE
    assert cfg["dept_unit"] == s.BRAND_DEPT_UNIT


def test_branding_db_overrides_env(db_session):
    SettingsService.set_branding_config(db_session, {
        "org_scope": "营销销售部", "dept_unit": "团队", "accent": "#e8833a",
    })
    cfg = SettingsService.get_branding_config(db_session)
    assert cfg["org_scope"] == "营销销售部"
    assert cfg["dept_unit"] == "团队"
    assert cfg["accent"] == "#e8833a"
    # 未设置的字段仍回退 env
    assert cfg["page_title"] == get_settings().BRAND_PAGE_TITLE


def test_branding_partial_update_merges(db_session):
    SettingsService.set_branding_config(db_session, {"org_scope": "营销销售部"})
    SettingsService.set_branding_config(db_session, {"dept_unit": "团队"})  # 不应清掉 org_scope
    cfg = SettingsService.get_branding_config(db_session)
    assert cfg["org_scope"] == "营销销售部"
    assert cfg["dept_unit"] == "团队"


def test_branding_empty_clears_to_env(db_session):
    s = get_settings()
    SettingsService.set_branding_config(db_session, {"org_scope": "营销销售部"})
    SettingsService.set_branding_config(db_session, {"org_scope": ""})  # 清空 → 回退 env
    cfg = SettingsService.get_branding_config(db_session)
    assert cfg["org_scope"] == s.BRAND_ORG_SCOPE


def test_branding_none_field_skipped(db_session):
    SettingsService.set_branding_config(db_session, {"org_scope": "营销销售部"})
    # None 字段不参与写入（仅更新提供的）
    SettingsService.set_branding_config(db_session, {"org_scope": None, "dept_unit": "团队"})
    cfg = SettingsService.get_branding_config(db_session)
    assert cfg["org_scope"] == "营销销售部"
    assert cfg["dept_unit"] == "团队"


def test_branding_logo_data_uri_roundtrip(db_session):
    data_uri = "data:image/png;base64,iVBORw0KGgoAAAANS"
    SettingsService.set_branding_config(db_session, {"logo_url": data_uri})
    cfg = SettingsService.get_branding_config(db_session)
    assert cfg["logo_url"] == data_uri


def test_sales_code_enabled_env_fallback_then_db_override(db_session):
    s = get_settings()
    # 未设置 → 回退 .env（默认 False）
    assert SettingsService.get_sales_code_enabled(db_session) == s.SALES_CODE_ENABLED
    # DB 开启覆盖 env
    SettingsService.set_sales_code_enabled(db_session, True)
    assert SettingsService.get_sales_code_enabled(db_session) is True
    # DB 关闭覆盖 env
    SettingsService.set_sales_code_enabled(db_session, False)
    assert SettingsService.get_sales_code_enabled(db_session) is False
