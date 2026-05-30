import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
# 确保所有模型都注册到 Base.metadata
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.models.user import User, UserRole
from backend.models.project import Project
from backend.models.task import TaskStatus, TaskPriority
from backend.schemas.task import TaskCreate, TaskUpdate
from backend.services.task_service import TaskService


@pytest.fixture
def db_session():
    """内存数据库会话 fixture"""
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
def owner(db_session):
    user = User(feishu_user_id="task_owner", name="任务负责人", role=UserRole.MEMBER)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def project(db_session, owner):
    proj = Project(name="任务测试项目", record_date=date(2026, 5, 30), owner_id=owner.id)
    db_session.add(proj)
    db_session.commit()
    db_session.refresh(proj)
    return proj


def test_create_task(db_session, project, owner):
    """创建任务"""
    task = TaskService.create(
        db_session, project.id,
        TaskCreate(name="任务1", owner_id=owner.id)
    )
    assert task.id is not None
    assert task.project_id == project.id
    assert task.status == TaskStatus.PENDING


def test_get_by_id(db_session, project, owner):
    """根据ID获取任务"""
    created = TaskService.create(
        db_session, project.id, TaskCreate(name="任务2", owner_id=owner.id)
    )
    fetched = TaskService.get_by_id(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id


def test_get_by_id_not_found(db_session):
    """获取不存在的任务返回 None"""
    assert TaskService.get_by_id(db_session, 99999) is None


def test_get_list_scoped_to_project(db_session, project, owner):
    """列表仅返回所属项目的任务"""
    other_project = Project(name="其他项目", record_date=date(2026, 5, 30), owner_id=owner.id)
    db_session.add(other_project)
    db_session.commit()
    db_session.refresh(other_project)

    TaskService.create(db_session, project.id, TaskCreate(name="A", owner_id=owner.id))
    TaskService.create(db_session, other_project.id, TaskCreate(name="B", owner_id=owner.id))

    tasks = TaskService.get_list(db_session, project_id=project.id)
    assert len(tasks) == 1
    assert tasks[0].name == "A"


def test_get_list_filter_by_status(db_session, project, owner):
    """按状态过滤任务列表"""
    TaskService.create(db_session, project.id, TaskCreate(name="进行中", owner_id=owner.id, status=TaskStatus.IN_PROGRESS))
    TaskService.create(db_session, project.id, TaskCreate(name="已完成", owner_id=owner.id, status=TaskStatus.COMPLETED))

    tasks = TaskService.get_list(db_session, project_id=project.id, status=TaskStatus.COMPLETED)
    assert len(tasks) == 1
    assert tasks[0].name == "已完成"


def test_get_list_filter_by_priority(db_session, project, owner):
    """按优先级过滤"""
    TaskService.create(db_session, project.id, TaskCreate(name="高", owner_id=owner.id, priority=TaskPriority.HIGH))
    TaskService.create(db_session, project.id, TaskCreate(name="低", owner_id=owner.id, priority=TaskPriority.LOW))

    tasks = TaskService.get_list(db_session, project_id=project.id, priority=TaskPriority.HIGH)
    assert len(tasks) == 1
    assert tasks[0].name == "高"


def test_get_list_negative_pagination_raises(db_session, project):
    """skip/limit 为负数抛出 ValueError"""
    with pytest.raises(ValueError):
        TaskService.get_list(db_session, project_id=project.id, skip=-1)


def test_subtasks(db_session, project, owner):
    """子任务创建与查询"""
    parent = TaskService.create(db_session, project.id, TaskCreate(name="父任务", owner_id=owner.id))
    TaskService.create(db_session, project.id, TaskCreate(name="子1", owner_id=owner.id, parent_task_id=parent.id))
    TaskService.create(db_session, project.id, TaskCreate(name="子2", owner_id=owner.id, parent_task_id=parent.id))

    subtasks = TaskService.get_subtasks(db_session, parent.id)
    assert len(subtasks) == 2
    assert {t.name for t in subtasks} == {"子1", "子2"}


def test_update_task(db_session, project, owner):
    """更新任务"""
    task = TaskService.create(db_session, project.id, TaskCreate(name="原名", owner_id=owner.id))
    updated = TaskService.update(db_session, task.id, TaskUpdate(name="新名", completion=60))
    assert updated.name == "新名"
    assert updated.completion == 60


def test_update_task_not_found(db_session):
    """更新不存在的任务返回 None"""
    assert TaskService.update(db_session, 99999, TaskUpdate(name="x")) is None


def test_delete_task(db_session, project, owner):
    """删除任务"""
    task = TaskService.create(db_session, project.id, TaskCreate(name="待删", owner_id=owner.id))
    assert TaskService.delete(db_session, task.id) is True
    assert TaskService.get_by_id(db_session, task.id) is None


def test_delete_task_not_found(db_session):
    """删除不存在的任务返回 False"""
    assert TaskService.delete(db_session, 99999) is False
