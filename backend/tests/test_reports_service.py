import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.models.user import User, UserRole
from backend.models.project import Project, ProjectStatus
from backend.models.task import Task, TaskStatus
from backend.models.risk import Risk, RiskStatus
from backend.services.statistics_service import StatisticsService
from backend.services.export_service import ExportService
from backend.services.import_service import ImportService
from backend.utils.excel import build_xlsx, parse_xlsx


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
    u = User(feishu_user_id="stat_owner", name="负责人", role=UserRole.ADMIN)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def project(db_session, owner):
    p = Project(name="统计项目", record_date=date(2026, 5, 30), owner_id=owner.id,
                status=ProjectStatus.IN_PROGRESS, completion=40)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


TODAY = date(2026, 6, 1)


def test_dashboard(db_session, owner, project):
    db_session.add_all([
        Task(project_id=project.id, name="t1", owner_id=owner.id, status=TaskStatus.PENDING),
        Task(project_id=project.id, name="t2", owner_id=owner.id, status=TaskStatus.COMPLETED),
        Task(project_id=project.id, name="逾期", owner_id=owner.id, status=TaskStatus.IN_PROGRESS,
             due_date=date(2026, 5, 1)),
        Risk(project_id=project.id, title="r1", status=RiskStatus.OPEN),
    ])
    db_session.commit()

    d = StatisticsService.dashboard(db_session, TODAY)
    assert d["projects"]["total"] == 1
    assert d["projects"]["by_status"]["in_progress"] == 1
    assert d["projects"]["avg_completion"] == 40.0
    assert d["tasks"]["total"] == 3
    assert d["tasks"]["by_status"]["completed"] == 1
    assert d["tasks"]["overdue"] == 1
    assert d["risks"]["by_status"]["open"] == 1


def test_project_progress(db_session, owner, project):
    db_session.add_all([
        Task(project_id=project.id, name="t1", owner_id=owner.id, status=TaskStatus.COMPLETED),
        Task(project_id=project.id, name="t2", owner_id=owner.id, status=TaskStatus.PENDING),
    ])
    db_session.commit()

    p = StatisticsService.project_progress(db_session, project.id)
    assert p["task_total"] == 2
    assert p["task_completed"] == 1
    assert p["task_completion_rate"] == 50.0


def test_project_progress_not_found(db_session):
    assert StatisticsService.project_progress(db_session, 99999) is None


def test_export_projects(db_session, owner, project):
    data = ExportService.export_projects(db_session)
    parsed = parse_xlsx(data)
    assert len(parsed) == 1
    assert parsed[0]["项目名称"] == "统计项目"


def test_export_tasks(db_session, owner, project):
    db_session.add(Task(project_id=project.id, name="导出任务", owner_id=owner.id))
    db_session.commit()
    data = ExportService.export_tasks(db_session, project.id)
    parsed = parse_xlsx(data)
    assert len(parsed) == 1
    assert parsed[0]["任务名称"] == "导出任务"


def test_import_tasks_success(db_session, owner, project):
    data = build_xlsx(
        ["任务名称", "负责人ID", "状态", "完成度"],
        [["导入1", owner.id, "pending", 0], ["导入2", owner.id, "in_progress", 30]],
    )
    result = ImportService.import_tasks(db_session, project.id, data)
    assert result.created == 2
    assert result.errors == []
    tasks = db_session.query(Task).filter(Task.project_id == project.id).all()
    assert {t.name for t in tasks} == {"导入1", "导入2"}


def test_import_tasks_partial_errors(db_session, owner, project):
    # 第二行 owner_id 缺失 -> 校验失败，但第一行成功
    data = build_xlsx(
        ["任务名称", "负责人ID"],
        [["有效", owner.id], ["无负责人", None]],
    )
    result = ImportService.import_tasks(db_session, project.id, data)
    assert result.created == 1
    assert len(result.errors) == 1
    assert result.errors[0]["row"] == 3


def test_import_tasks_with_dates(db_session, owner, project):
    data = build_xlsx(
        ["任务名称", "负责人ID", "截止日期"],
        [["带日期", owner.id, "2026-07-01"]],
    )
    result = ImportService.import_tasks(db_session, project.id, data)
    assert result.created == 1
    t = db_session.query(Task).filter(Task.name == "带日期").first()
    assert t.due_date == date(2026, 7, 1)
