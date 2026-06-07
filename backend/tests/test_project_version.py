"""项目乐观锁（version）测试

覆盖：
- 创建项目返回 version=1
- 带正确 version 更新成功且 version 自动 +1
- 带过期 version 更新返回 409，且数据未被覆盖
- 不带 version（过渡期兼容旧客户端）仍可更新且 version 自增
- 双会话并发提交触发 SQL 级 CAS（version_id_col → StaleDataError）
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.user import User, UserRole
from backend.models.project import Project
# 确保所有模型都注册到 Base.metadata
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user


@pytest.fixture
def db_session():
    """内存数据库会话（StaticPool 确保所有线程共享同一连接）"""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
    user = User(feishu_user_id="version_test_user", name="乐观锁测试用户", role=UserRole.ADMIN)
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

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create(client, name="乐观锁项目"):
    r = client.post("/api/v1/projects/", json={
        "name": name, "record_date": "2026-06-07", "owner_name": "负责人",
    })
    assert r.status_code == 201
    return r.json()


def test_create_project_returns_version_1(client):
    """新建项目初始 version=1"""
    data = _create(client)
    assert data["version"] == 1


def test_update_with_correct_version(client):
    """带正确 version 更新：成功且 version 自动 +1"""
    p = _create(client)
    r = client.put(f"/api/v1/projects/{p['id']}", json={"completion": 30, "version": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["completion"] == 30
    assert body["version"] == 2


def test_update_with_stale_version_returns_409(client):
    """带过期 version 更新：409 冲突，且先前的修改未被覆盖"""
    p = _create(client)
    r1 = client.put(f"/api/v1/projects/{p['id']}", json={"completion": 30, "version": 1})
    assert r1.status_code == 200  # version → 2

    # 第二个客户端仍持有打开时的 version=1（过期）
    r2 = client.put(f"/api/v1/projects/{p['id']}", json={"completion": 60, "version": 1})
    assert r2.status_code == 409
    assert "已被他人修改" in r2.json()["detail"]

    # 数据保持第一次的修改，未被过期请求覆盖
    g = client.get(f"/api/v1/projects/{p['id']}")
    assert g.json()["completion"] == 30
    assert g.json()["version"] == 2


def test_update_without_version_is_compatible(client):
    """过渡期兼容：不带 version 跳过应用层比对仍可更新，version 照常自增"""
    p = _create(client)
    r = client.put(f"/api/v1/projects/{p['id']}", json={"completion": 30})
    assert r.status_code == 200
    assert r.json()["version"] == 2


def test_concurrent_commit_triggers_stale_data_error():
    """双会话并发提交：后提交者的 UPDATE ... WHERE version=旧值 命中 0 行 → StaleDataError
    （API 层将其与 ProjectVersionConflict 一并转为 409）"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # 建一条项目
    s0 = SessionLocal()
    proj = Project(name="并发项目", record_date=date(2026, 6, 7))
    s0.add(proj)
    s0.commit()
    pid = proj.id
    s0.close()

    # 两个会话各自加载同一行（各自持有 version=1 的快照）
    s1, s2 = SessionLocal(), SessionLocal()
    p1 = s1.get(Project, pid)
    p2 = s2.get(Project, pid)

    # 会话2 先提交成功（version → 2）
    p2.completion = 50
    s2.commit()

    # 会话1 基于过期 version 提交 → CAS 失败 → StaleDataError
    p1.completion = 80
    with pytest.raises(StaleDataError):
        s1.commit()
    s1.rollback()
    s1.close()
    s2.close()
