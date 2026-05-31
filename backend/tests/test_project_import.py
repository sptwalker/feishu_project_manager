import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.models import User as _U, Project as _P, Task as _T, Event as _E, Risk as _R  # noqa: F401
from backend.db.base import Base
from backend.models.user import User
from backend.models.project import Project, ProjectStatus, ProjectUrgency
from backend.services.import_service import ImportService
from backend.utils.excel import build_xlsx, ExcelParseError

# 周会跟进清单格式表头
HEADERS = ["部门", "完成情况", "待办事项", "说明", "负责人", "相关人", "目前状况",
           "优先级", "进度", "记录日期", "截止日期", "待讨论", "智能总结", "文本13", "文本14", "重要度"]


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


def _row(department="技术", status="执行中", name="光枪SDK接入", desc="说明",
         owner="Ericsong", related="", progress_note="", priority="P3", progress="0.5",
         record="2026/5/23", due="2026/5/30", importance=""):
    return [department, status, name, desc, owner, related, progress_note,
            priority, progress, record, due, "□", "", "", "", importance]


def test_import_projects_basic(db_session):
    data = build_xlsx(HEADERS, [
        _row(name="项目A", owner="Ericsong", status="执行中", priority="P1", progress="0.5"),
        _row(name="项目B", owner="simon", status="已完成", priority="P2", progress="1"),
        _row(name="项目C", owner="Noice", status="暂停中", priority="P3", progress="0.1"),
    ])
    result = ImportService.import_projects(db_session, data)
    assert result.created == 3
    assert result.errors == []

    projects = db_session.query(Project).order_by(Project.id).all()
    by_name = {p.name: p for p in projects}
    assert {p.name for p in projects} == {"项目A", "项目B", "项目C"}
    assert by_name["项目A"].status == ProjectStatus.IN_PROGRESS
    assert by_name["项目B"].status == ProjectStatus.COMPLETED
    assert by_name["项目C"].status == ProjectStatus.PAUSED
    assert by_name["项目A"].urgency == ProjectUrgency.HIGH      # P1
    assert by_name["项目B"].urgency == ProjectUrgency.MEDIUM    # P2
    assert by_name["项目A"].completion == 50                   # 0.5 -> 50
    assert by_name["项目B"].completion == 100                  # 1 -> 100
    assert by_name["项目A"].department == "技术"
    assert by_name["项目A"].owner_name == "Ericsong"          # 负责人按姓名直接存储
    assert by_name["项目A"].estimated_end_date == date(2026, 5, 30)
    assert by_name["项目A"].record_date == date(2026, 5, 23)


def test_import_does_not_create_users(db_session):
    """导入只把负责人存为姓名，绝不创建用户账号（与用户解耦）"""
    data = build_xlsx(HEADERS, [
        _row(name="P1", owner="申华"),
        _row(name="P2", owner="申华"),
        _row(name="P3", owner="Jack"),
    ])
    result = ImportService.import_projects(db_session, data)
    assert result.created == 3
    # 不应创建任何用户
    assert db_session.query(User).count() == 0
    names = {p.owner_name for p in db_session.query(Project).all()}
    assert names == {"申华", "Jack"}


def test_import_skips_empty_name_rows(db_session):
    data = build_xlsx(HEADERS, [
        _row(name="有效项目", owner="A"),
        _row(name="", owner="B"),         # 空名 -> 跳过，不计入
        ["", "", "", "", "", "", "", "", "", "", "", "□", "", "", "", ""],  # 完全空行
    ])
    result = ImportService.import_projects(db_session, data)
    assert result.created == 1
    assert result.errors == []


def test_import_row_missing_owner_is_error(db_session):
    data = build_xlsx(HEADERS, [
        _row(name="有负责人", owner="A"),
        _row(name="无负责人", owner=""),   # 负责人为空 -> 计入错误
    ])
    result = ImportService.import_projects(db_session, data)
    assert result.created == 1
    assert len(result.errors) == 1
    assert result.errors[0]["row"] == 3


def test_import_progress_as_percentage(db_session):
    data = build_xlsx(HEADERS, [_row(name="P", owner="A", progress="80")])
    result = ImportService.import_projects(db_session, data)
    assert result.created == 1
    p = db_session.query(Project).first()
    assert p.completion == 80


def test_import_merges_description_and_progress_note(db_session):
    data = build_xlsx(HEADERS, [
        _row(name="P", owner="A", desc="基础说明", progress_note="本周完成评审"),
    ])
    ImportService.import_projects(db_session, data)
    p = db_session.query(Project).first()
    assert "基础说明" in p.content
    assert "本周完成评审" in p.content


def test_import_missing_required_column_raises(db_session):
    # 缺少「负责人」列
    data = build_xlsx(["部门", "待办事项"], [["技术", "项目X"]])
    with pytest.raises(ExcelParseError):
        ImportService.import_projects(db_session, data)
