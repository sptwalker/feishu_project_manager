"""端到端验证：任务/风险状态变更通过 BackgroundTasks 触发飞书通知。"""
import pytest
from datetime import date
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.models.user import User, UserRole
from backend.models.project import Project
from backend.models.task import Task, TaskStatus
# 确保所有模型都注册到 Base.metadata
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.api.deps import get_db
from backend.core.dependencies import get_current_user
from backend.core.config import get_settings
from backend.core.feishu import feishu_client


@pytest.fixture
def db_session():
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
    user = User(feishu_user_id="notify_user", name="通知用户", role=UserRole.ADMIN)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def task(db_session, test_user):
    project = Project(name="通知项目", record_date=date(2026, 5, 30), owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    t = Task(project_id=project.id, name="通知任务", owner_id=test_user.id, status=TaskStatus.PENDING)
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


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
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def enable_notify():
    s = get_settings()
    old = s.FEISHU_NOTIFY_ENABLED
    s.FEISHU_NOTIFY_ENABLED = True
    yield
    s.FEISHU_NOTIFY_ENABLED = old


def test_task_status_change_triggers_notification(client, task, enable_notify, monkeypatch):
    """状态变更 → 后台任务发送卡片到负责人"""
    mock = AsyncMock(return_value={"message_id": "m"})
    monkeypatch.setattr(feishu_client, "send_card", mock)

    r = client.put(f"/api/v1/tasks/{task.id}", json={"status": "in_progress"})
    assert r.status_code == 200
    # 后台任务在响应后执行，TestClient 退出时已完成
    mock.assert_awaited_once()
    # 第一个参数是 receive_id（负责人飞书ID）
    args, kwargs = mock.call_args
    assert args[0] == "notify_user"


def test_task_update_without_status_change_no_notification(client, task, enable_notify, monkeypatch):
    """非状态字段更新不应触发通知"""
    mock = AsyncMock(return_value={"message_id": "m"})
    monkeypatch.setattr(feishu_client, "send_card", mock)

    r = client.put(f"/api/v1/tasks/{task.id}", json={"name": "改个名"})
    assert r.status_code == 200
    mock.assert_not_called()
