import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
# 确保所有模型注册到 Base.metadata
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.models.user import User, UserRole
from backend.models.project import Project, ProjectStatus
from backend.models.task import Task, TaskStatus
from backend.services.reminder_service import ReminderService


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
def owner(db_session):
    u = User(feishu_user_id="rem_owner", name="负责人", role=UserRole.MEMBER)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def project(db_session, owner):
    p = Project(name="提醒项目", record_date=date(2026, 5, 30), owner_id=owner.id)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _task(db_session, project, owner, **kw):
    t = Task(project_id=project.id, name=kw.pop("name", "T"), owner_id=owner.id, **kw)
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


TODAY = date(2026, 6, 1)


def test_find_overdue_tasks(db_session, project, owner):
    _task(db_session, project, owner, name="逾期", due_date=date(2026, 5, 20), status=TaskStatus.IN_PROGRESS)
    _task(db_session, project, owner, name="未来", due_date=date(2026, 6, 10), status=TaskStatus.IN_PROGRESS)
    _task(db_session, project, owner, name="已完成逾期", due_date=date(2026, 5, 20), status=TaskStatus.COMPLETED)
    _task(db_session, project, owner, name="无截止", status=TaskStatus.PENDING)

    overdue = ReminderService.find_overdue_tasks(db_session, TODAY)
    names = {t.name for t in overdue}
    assert names == {"逾期"}


def test_find_due_soon_tasks(db_session, project, owner):
    _task(db_session, project, owner, name="今天", due_date=TODAY, status=TaskStatus.PENDING)
    _task(db_session, project, owner, name="3天内", due_date=TODAY + timedelta(days=2), status=TaskStatus.PENDING)
    _task(db_session, project, owner, name="太远", due_date=TODAY + timedelta(days=10), status=TaskStatus.PENDING)
    _task(db_session, project, owner, name="已逾期", due_date=TODAY - timedelta(days=1), status=TaskStatus.PENDING)

    soon = ReminderService.find_due_soon_tasks(db_session, TODAY, days=3)
    names = {t.name for t in soon}
    assert names == {"今天", "3天内"}


def test_find_stale_in_progress_tasks(db_session, project, owner):
    now = datetime(2026, 6, 1, 12, 0, 0)
    stale = _task(db_session, project, owner, name="陈旧", status=TaskStatus.IN_PROGRESS)
    fresh = _task(db_session, project, owner, name="新鲜", status=TaskStatus.IN_PROGRESS)
    # 手动覆盖 updated_at
    stale.updated_at = now - timedelta(days=5)
    fresh.updated_at = now - timedelta(hours=1)
    db_session.commit()

    result = ReminderService.find_stale_in_progress_tasks(db_session, now, days=3)
    names = {t.name for t in result}
    assert "陈旧" in names
    assert "新鲜" not in names


def test_find_overdue_projects(db_session, owner):
    p1 = Project(name="逾期项目", record_date=date(2026, 5, 1), owner_id=owner.id,
                 estimated_end_date=date(2026, 5, 20), status=ProjectStatus.IN_PROGRESS)
    p2 = Project(name="完成项目", record_date=date(2026, 5, 1), owner_id=owner.id,
                 estimated_end_date=date(2026, 5, 20), status=ProjectStatus.COMPLETED)
    p3 = Project(name="未来项目", record_date=date(2026, 5, 1), owner_id=owner.id,
                 estimated_end_date=date(2026, 6, 30), status=ProjectStatus.IN_PROGRESS)
    db_session.add_all([p1, p2, p3])
    db_session.commit()

    overdue = ReminderService.find_overdue_projects(db_session, TODAY)
    names = {p.name for p in overdue}
    assert names == {"逾期项目"}
