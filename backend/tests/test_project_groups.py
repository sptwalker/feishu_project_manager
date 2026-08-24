"""项目组（Project Groups）层级测试

- 建组（is_group=true）→ 建子项目（parent_id=组.id）→ GET 返回带 is_group/parent_id
- 删组 → 子项目随之消失（ORM 级联），子项目下的 task/risk 也被删
- 独立项目默认 is_group=false, parent_id=null
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.user import User, UserRole
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.models.task import Task, TaskStatus, TaskPriority
from backend.models.risk import Risk
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
    u = User(feishu_user_id="grp_admin", name="组管理员", role=UserRole.ADMIN)
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
    r = client.post("/api/v1/projects/", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_group_and_child_roundtrip(db_session, admin_user):
    client = _client(db_session, admin_user)
    group = _create(client, "市场项目组", is_group=True)
    assert group["is_group"] is True
    assert group["parent_id"] is None

    child = _create(client, "子项目A", parent_id=group["id"])
    assert child["is_group"] is False
    assert child["parent_id"] == group["id"]

    # 列表返回带层级字段
    r = client.get("/api/v1/projects/", params={"limit": 500})
    app.dependency_overrides.clear()
    assert r.status_code == 200
    by_id = {p["id"]: p for p in r.json()}
    assert by_id[group["id"]]["is_group"] is True
    assert by_id[child["id"]]["parent_id"] == group["id"]


def test_delete_group_cascades(db_session, admin_user):
    client = _client(db_session, admin_user)
    group = _create(client, "待删组", is_group=True)
    child = _create(client, "待删子项目", parent_id=group["id"])
    # 子项目下挂 task + risk，验证级联会连带删除
    db_session.add(Task(project_id=child["id"], name="子任务",
                        status=TaskStatus.PENDING, priority=TaskPriority.MEDIUM))
    db_session.add(Risk(project_id=child["id"], title="子风险"))
    db_session.commit()

    r = client.delete(f"/api/v1/projects/{group['id']}")
    app.dependency_overrides.clear()
    assert r.status_code == 204, r.text

    # 组、子项目、子项目的 task/risk 全部消失
    assert db_session.query(_P).filter_by(id=group["id"]).first() is None
    assert db_session.query(_P).filter_by(id=child["id"]).first() is None
    assert db_session.query(Task).filter_by(project_id=child["id"]).count() == 0
    assert db_session.query(Risk).filter_by(project_id=child["id"]).count() == 0


def test_standalone_defaults(db_session, admin_user):
    client = _client(db_session, admin_user)
    p = _create(client, "独立项目")
    app.dependency_overrides.clear()
    assert p["is_group"] is False
    assert p["parent_id"] is None
