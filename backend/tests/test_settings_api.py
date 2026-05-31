from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.user import User, UserRole
from backend.models.project import Project
from backend.models import (  # noqa: F401  确保所有表注册到 Base.metadata
    User as _U, Project as _P, Task as _T, Event as _E, Risk as _R,
    Department as _D, SystemSetting as _S,
)
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.services.settings_service import SettingsService, compute_count, monday_of


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", echo=False,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _make_user(db, feishu_id, role=UserRole.MEMBER):
    u = User(feishu_user_id=feishu_id, name=feishu_id, role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _client(db_session, current_user):
    def override_get_db():
        yield db_session

    def override_get_current_user():
        return current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


def _cleanup():
    app.dependency_overrides.clear()


# ---------- 纯算法 ----------

def test_monday_of():
    assert monday_of(date(2026, 6, 1)) == date(2026, 6, 1)   # 周一
    assert monday_of(date(2026, 6, 7)) == date(2026, 6, 1)   # 周日
    assert monday_of(date(2026, 5, 31)) == date(2026, 5, 25)


def test_compute_count_by_natural_week():
    bm = date(2026, 6, 1)
    assert compute_count(date(2026, 5, 31), bm, 22) == 21   # 上一周
    assert compute_count(date(2026, 6, 1), bm, 22) == 22
    assert compute_count(date(2026, 6, 3), bm, 22) == 22    # 同周不变
    assert compute_count(date(2026, 6, 7), bm, 22) == 22
    assert compute_count(date(2026, 6, 8), bm, 22) == 23    # 跨周 +1
    assert compute_count(date(2026, 6, 15), bm, 22) == 24


# ---------- 状态 / 扫描 ----------

def test_meeting_state_scan_and_calibration(db_session):
    # 上次周会 session=20，本周(21)尚未记录
    p = Project(name="P1", record_date=date(2026, 1, 1), progress_log=[
        {"time": "2026-05-18 10:00", "content": "a", "status": "正常", "meeting_session": 20},
    ])
    db_session.add(p)
    db_session.commit()

    st = SettingsService.get_meeting_state(db_session, today=date(2026, 5, 31))
    assert st["this_week_count"] == 21
    assert st["this_week_recorded"] is False
    assert st["last_meeting"] == {"date": "2026-05-18 10:00", "count": 20}
    assert st["calibration_count"] == 21          # 本周未记录 -> 校准本周
    assert st["calibration_monday"] == "2026-05-25"

    # 追加本周记录 session=21
    p.progress_log = list(p.progress_log) + [
        {"time": "2026-05-31 09:00", "content": "b", "status": "正常", "meeting_session": 21},
    ]
    db_session.commit()
    st2 = SettingsService.get_meeting_state(db_session, today=date(2026, 5, 31))
    assert st2["this_week_recorded"] is True
    assert st2["calibration_count"] == 22         # 本周已记录 -> 校准下周
    assert st2["calibration_monday"] == "2026-06-01"


def test_set_count_resets_base(db_session):
    # 本周未记录时校准本周次数
    SettingsService.set_count(db_session, 30, today=date(2026, 6, 1))
    st = SettingsService.get_meeting_state(db_session, today=date(2026, 6, 1))
    assert st["this_week_count"] == 30
    assert st["base_count"] == 30
    assert st["base_monday"] == "2026-06-01"


# ---------- API 权限 ----------

def test_get_meeting_state_any_user(db_session):
    member = _make_user(db_session, "m1")
    client = _client(db_session, member)
    try:
        r = client.get("/api/v1/settings/meeting")
        assert r.status_code == 200
        assert "active" in r.json()
        assert "this_week_count" in r.json()
    finally:
        _cleanup()


def test_set_active_admin(db_session):
    admin = _make_user(db_session, "admin1", role=UserRole.ADMIN)
    client = _client(db_session, admin)
    try:
        r = client.put("/api/v1/settings/meeting/active", json={"active": True})
        assert r.status_code == 200
        assert r.json()["active"] is True
        r2 = client.put("/api/v1/settings/meeting/active", json={"active": False})
        assert r2.json()["active"] is False
    finally:
        _cleanup()


def test_set_active_non_admin_403(db_session):
    member = _make_user(db_session, "m1")
    client = _client(db_session, member)
    try:
        r = client.put("/api/v1/settings/meeting/active", json={"active": True})
        assert r.status_code == 403
    finally:
        _cleanup()


def test_set_count_non_admin_403(db_session):
    member = _make_user(db_session, "m1")
    client = _client(db_session, member)
    try:
        r = client.put("/api/v1/settings/meeting/count", json={"count": 25})
        assert r.status_code == 403
    finally:
        _cleanup()
