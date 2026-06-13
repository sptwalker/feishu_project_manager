"""飞书应用凭证 DB 配置：解析优先级 + 设置存取"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.core.feishu import FeishuClient
from backend.core.config import get_settings
from backend.services.settings_service import (
    SettingsService, FEISHU_APP_ID_KEY, FEISHU_APP_SECRET_KEY,
)


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


# ---------- SettingsService: DB 优先 + env 回退 ----------

def test_app_id_falls_back_to_env(db_session):
    s = get_settings()
    assert SettingsService.get_feishu_app_id(db_session) == s.FEISHU_APP_ID  # 未配置 → env


def test_app_id_db_overrides_env(db_session):
    SettingsService.set_feishu_app(db_session, "cli_db_id", "db_secret")
    assert SettingsService.get_feishu_app_id(db_session) == "cli_db_id"
    assert SettingsService.is_feishu_secret_set(db_session) is True


def test_secret_kept_when_update_without_secret(db_session):
    SettingsService.set_feishu_app(db_session, "cli_a", "secret_a")
    # 仅改 app_id、不传 secret → 密钥保持
    SettingsService.set_feishu_app(db_session, "cli_b", None)
    assert SettingsService.get_feishu_app_id(db_session) == "cli_b"
    assert SettingsService.get_setting(db_session, FEISHU_APP_SECRET_KEY) == "secret_a"


def test_empty_app_id_falls_back_to_env(db_session):
    s = get_settings()
    SettingsService.set_feishu_app(db_session, "", None)  # 清空 → 回退 env
    assert SettingsService.get_feishu_app_id(db_session) == s.FEISHU_APP_ID


# ---------- FeishuClient._creds 解析优先级 ----------

def test_creds_override_wins(monkeypatch):
    c = FeishuClient()
    c.app_id = "ov_id"          # 显式赋值（测试/手动）优先
    c.app_secret = "ov_secret"
    # 即使 DB 有值也应被 override 覆盖
    monkeypatch.setattr(FeishuClient, "_db_credentials", staticmethod(lambda: ("db_id", "db_sec")))
    assert c._creds() == ("ov_id", "ov_secret")
    assert c.app_id == "ov_id"


def test_creds_db_over_env(monkeypatch):
    c = FeishuClient()
    monkeypatch.setattr(FeishuClient, "_db_credentials", staticmethod(lambda: ("db_id", "db_sec")))
    assert c._creds() == ("db_id", "db_sec")


def test_creds_env_fallback(monkeypatch):
    c = FeishuClient()
    monkeypatch.setattr(FeishuClient, "_db_credentials", staticmethod(lambda: ("", "")))
    s = get_settings()
    assert c._creds() == (s.FEISHU_APP_ID, s.FEISHU_APP_SECRET)
