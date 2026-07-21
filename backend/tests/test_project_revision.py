"""项目集合变更签名 /projects/revision 测试

会议汇报页据此低成本轮询检测「他端改了项目」，变化才重拉列表。
覆盖：空库签名；建/改/删项目后签名变化；同数据重复查询签名稳定。
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


@pytest.fixture
def test_user(db_session):
    user = User(feishu_user_id="rev_test_user", name="签名测试用户", role=UserRole.ADMIN)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(db_session, test_user):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _rev(client) -> str:
    r = client.get("/api/v1/projects/revision")
    assert r.status_code == 200
    return r.json()["revision"]


def _create(client, name="签名项目"):
    r = client.post("/api/v1/projects/", json={
        "name": name, "record_date": "2026-06-07", "owner_name": "负责人",
    })
    assert r.status_code == 201
    return r.json()


def test_revision_empty_and_stable(client):
    """空库有确定签名；无改动时重复查询签名不变"""
    r1 = _rev(client)
    assert r1 == "0:0"
    assert _rev(client) == r1


def test_revision_changes_on_create(client):
    before = _rev(client)
    _create(client)
    assert _rev(client) != before          # 新增 → count+1、sum+1


def test_revision_changes_on_update(client):
    p = _create(client)
    before = _rev(client)
    r = client.put(f"/api/v1/projects/{p['id']}", json={"completion": 42, "version": 1})
    assert r.status_code == 200
    assert _rev(client) != before          # 编辑 → version+1 → sum 变


def test_revision_changes_on_delete(client):
    p = _create(client)
    before = _rev(client)
    r = client.delete(f"/api/v1/projects/{p['id']}")
    assert r.status_code == 204
    assert _rev(client) != before          # 删除 → count 变


def test_revision_not_shadowed_by_dynamic_route(client):
    """/revision 不被 /{project_id} 吞掉（否则会因 int 解析 422 或误当 id）"""
    r = client.get("/api/v1/projects/revision")
    assert r.status_code == 200
    assert ":" in r.json()["revision"]
