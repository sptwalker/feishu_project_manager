"""CEO重点关注（ceo_focus / 置顶）测试

- 管理员可钉 3 个（create），第 4 个 create 与 update 均 400
- 非管理员 PUT ceo_focus=true 返回 403
- 非管理员保存已钉项目「其它字段」（ceo_focus 不变）→ 200，且钉状态不被清除
- 关掉一个再钉另一个 OK（额度释放）
- GET 列表中 ceo_focus=true 排在前
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.user import User, UserRole
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def admin_user(db_session):
    u = User(feishu_user_id="ceo_admin", name="管理员", role=UserRole.ADMIN)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def member_user(db_session):
    # 项目经理可改项目但非管理员：用于验证 ceo_focus 权限拦截
    u = User(feishu_user_id="ceo_pm", name="项目经理", role=UserRole.PROJECT_MANAGER)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _client(db_session, user):
    def override_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _create(client, name, **extra):
    payload = {"name": name, "urgency": "medium", **extra}
    return client.post("/api/v1/projects/", json=payload)


def test_admin_pin_up_to_three_then_reject(db_session, admin_user):
    client = _client(db_session, admin_user)
    for i in range(3):
        r = _create(client, f"钉{i}", ceo_focus=True)
        assert r.status_code == 201, r.text
        assert r.json()["ceo_focus"] is True
    # 第 4 个 create 超限 → 400
    r4 = _create(client, "钉4", ceo_focus=True)
    assert r4.status_code == 400, r4.text
    # 建一个未钉的，再 update 钉它 → 也 400
    plain = _create(client, "普通", ceo_focus=False).json()
    r = client.put(f"/api/v1/projects/{plain['id']}", json={"ceo_focus": True, "version": plain["version"]})
    app.dependency_overrides.clear()
    assert r.status_code == 400, r.text


def test_non_admin_cannot_set_focus(db_session, admin_user, member_user):
    # admin 建一个普通项目
    admin_client = _client(db_session, admin_user)
    p = _create(admin_client, "待钉", ceo_focus=False).json()
    # 项目经理尝试钉 → 403
    pm_client = _client(db_session, member_user)
    r = pm_client.put(f"/api/v1/projects/{p['id']}", json={"ceo_focus": True, "version": p["version"]})
    app.dependency_overrides.clear()
    assert r.status_code == 403, r.text


def test_non_admin_can_edit_pinned_other_fields(db_session, admin_user, member_user):
    # admin 钉住一个项目
    admin_client = _client(db_session, admin_user)
    p = _create(admin_client, "已钉", ceo_focus=True).json()
    assert p["ceo_focus"] is True
    # 项目经理改「其它字段」（不带 ceo_focus）→ 200，且钉状态保留
    pm_client = _client(db_session, member_user)
    r = pm_client.put(f"/api/v1/projects/{p['id']}", json={"content": "更新说明", "version": p["version"]})
    app.dependency_overrides.clear()
    assert r.status_code == 200, r.text
    assert r.json()["ceo_focus"] is True
    assert r.json()["content"] == "更新说明"


def test_release_quota_by_unpin(db_session, admin_user):
    client = _client(db_session, admin_user)
    pins = [_create(client, f"钉{i}", ceo_focus=True).json() for i in range(3)]
    plain = _create(client, "候补", ceo_focus=False).json()
    # 满 3 个时钉候补 → 400
    r = client.put(f"/api/v1/projects/{plain['id']}", json={"ceo_focus": True, "version": plain["version"]})
    assert r.status_code == 400
    # 取消一个 → 额度释放
    r = client.put(f"/api/v1/projects/{pins[0]['id']}", json={"ceo_focus": False, "version": pins[0]["version"]})
    assert r.status_code == 200, r.text
    # 再钉候补 → OK
    r = client.put(f"/api/v1/projects/{plain['id']}", json={"ceo_focus": True, "version": plain["version"]})
    app.dependency_overrides.clear()
    assert r.status_code == 200, r.text


def test_list_pins_first(db_session, admin_user):
    client = _client(db_session, admin_user)
    _create(client, "普通A", ceo_focus=False)
    _create(client, "普通B", ceo_focus=False)
    pinned = _create(client, "被钉", ceo_focus=True).json()
    r = client.get("/api/v1/projects/", params={"limit": 500})
    app.dependency_overrides.clear()
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert ids[0] == pinned["id"]  # 置顶排最前
