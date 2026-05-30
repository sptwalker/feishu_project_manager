import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.models.user import User, UserRole
from backend.models.project import Project
# 确保所有模型都注册到 Base.metadata
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.core.security import create_access_token


@pytest.fixture
def db_session():
    """数据库会话 fixture"""
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


def _make_client(db_session, current_user):
    """构造覆盖了 db 和 current_user 的 TestClient"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_user():
        return current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    return TestClient(app)


def _cleanup():
    app.dependency_overrides.clear()


def test_member_cannot_delete_others_project(db_session):
    """测试普通成员不能删除他人项目"""
    # 创建项目所有者
    owner = User(feishu_user_id="owner_123", name="所有者", role=UserRole.MEMBER)
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    # 创建项目
    project = Project(name="测试项目", record_date=date(2026, 5, 30), owner_id=owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    # 创建另一个用户
    other_user = User(feishu_user_id="other_456", name="其他用户", role=UserRole.MEMBER)
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    token = create_access_token({"sub": str(other_user.id)})

    client = _make_client(db_session, other_user)
    try:
        response = client.delete(
            f"/api/v1/projects/{project.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
    finally:
        _cleanup()


def test_admin_can_delete_any_project(db_session):
    """测试管理员可以删除任何项目"""
    owner = User(feishu_user_id="owner_789", name="所有者", role=UserRole.MEMBER)
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    project = Project(name="测试项目2", record_date=date(2026, 5, 30), owner_id=owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    admin = User(feishu_user_id="admin_001", name="管理员", role=UserRole.ADMIN)
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    token = create_access_token({"sub": str(admin.id)})

    client = _make_client(db_session, admin)
    try:
        response = client.delete(
            f"/api/v1/projects/{project.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204
    finally:
        _cleanup()


def test_owner_can_delete_own_project(db_session):
    """测试项目所有者可以删除自己的项目"""
    owner = User(feishu_user_id="owner_self", name="所有者", role=UserRole.MEMBER)
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    project = Project(name="自己的项目", record_date=date(2026, 5, 30), owner_id=owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    token = create_access_token({"sub": str(owner.id)})

    client = _make_client(db_session, owner)
    try:
        response = client.delete(
            f"/api/v1/projects/{project.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204
    finally:
        _cleanup()


def test_member_cannot_update_others_project(db_session):
    """测试普通成员不能更新他人项目"""
    owner = User(feishu_user_id="owner_upd", name="所有者", role=UserRole.MEMBER)
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    project = Project(name="他人项目", record_date=date(2026, 5, 30), owner_id=owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    other_user = User(feishu_user_id="other_upd", name="其他用户", role=UserRole.MEMBER)
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    token = create_access_token({"sub": str(other_user.id)})

    client = _make_client(db_session, other_user)
    try:
        response = client.put(
            f"/api/v1/projects/{project.id}",
            json={"name": "尝试更新"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
    finally:
        _cleanup()


def test_owner_can_update_own_project(db_session):
    """测试项目所有者可以更新自己的项目"""
    owner = User(feishu_user_id="owner_self_upd", name="所有者", role=UserRole.MEMBER)
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    project = Project(name="原名称", record_date=date(2026, 5, 30), owner_id=owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    token = create_access_token({"sub": str(owner.id)})

    client = _make_client(db_session, owner)
    try:
        response = client.put(
            f"/api/v1/projects/{project.id}",
            json={"name": "新名称"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "新名称"
    finally:
        _cleanup()


def test_update_nonexistent_project_returns_404(db_session):
    """非所有者对不存在的项目执行 PUT 应返回 404 而不是 403"""
    other_user = User(feishu_user_id="other_404_upd", name="其他用户", role=UserRole.MEMBER)
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    token = create_access_token({"sub": str(other_user.id)})

    client = _make_client(db_session, other_user)
    try:
        response = client.put(
            "/api/v1/projects/999999",
            json={"name": "尝试更新"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
    finally:
        _cleanup()


def test_delete_nonexistent_project_returns_404(db_session):
    """非所有者对不存在的项目执行 DELETE 应返回 404 而不是 403"""
    other_user = User(feishu_user_id="other_404_del", name="其他用户", role=UserRole.MEMBER)
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    token = create_access_token({"sub": str(other_user.id)})

    client = _make_client(db_session, other_user)
    try:
        response = client.delete(
            "/api/v1/projects/999999",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
    finally:
        _cleanup()


def test_project_manager_cannot_delete_others_project(db_session):
    """PROJECT_MANAGER 角色（非所有者）不能删除他人项目，应返回 403"""
    owner = User(feishu_user_id="owner_pm_test", name="所有者", role=UserRole.MEMBER)
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    project = Project(name="他人项目PM", record_date=date(2026, 5, 30), owner_id=owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    pm_user = User(feishu_user_id="pm_user_001", name="项目经理", role=UserRole.PROJECT_MANAGER)
    db_session.add(pm_user)
    db_session.commit()
    db_session.refresh(pm_user)

    token = create_access_token({"sub": str(pm_user.id)})

    client = _make_client(db_session, pm_user)
    try:
        response = client.delete(
            f"/api/v1/projects/{project.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
    finally:
        _cleanup()
