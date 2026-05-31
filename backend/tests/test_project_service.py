import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from backend.services.project_service import ProjectService
from backend.schemas.project import ProjectCreate, ProjectUpdate
from backend.models.project import Project, ProjectStatus
from backend.models.user import User, UserRole
from backend.db.base import Base

@pytest.fixture
def db_session():
    """数据库会话 fixture"""
    # 使用内存数据库进行测试
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(db_session):
    """创建测试用户"""
    user = User(
        feishu_user_id="test_user_123",
        name="测试用户",
        role=UserRole.MEMBER
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def test_create_project(db_session, test_user):
    """测试创建项目"""
    project_data = ProjectCreate(
        name="新项目",
        record_date=date.today(),
        content="项目描述",
        owner_name="负责人"
    )
    project = ProjectService.create(db_session, project_data)
    assert project.id is not None
    assert project.name == "新项目"
    assert project.owner_name == "负责人"

def test_get_project_by_id(db_session, test_user):
    """测试根据ID获取项目"""
    project_data = ProjectCreate(
        name="测试项目",
        record_date=date.today(),
        owner_name="负责人"
    )
    created = ProjectService.create(db_session, project_data)
    fetched = ProjectService.get_by_id(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id

def test_get_project_by_id_not_found(db_session):
    """测试获取不存在的项目"""
    fetched = ProjectService.get_by_id(db_session, 99999)
    assert fetched is None

def test_get_project_list(db_session, test_user):
    """测试获取项目列表"""
    # 创建多个项目
    for i in range(5):
        project_data = ProjectCreate(
            name=f"项目{i}",
            record_date=date.today(),
            owner_name="负责人"
        )
        ProjectService.create(db_session, project_data)

    projects = ProjectService.get_list(db_session, skip=0, limit=10)
    assert len(projects) == 5

def test_get_project_list_with_filters(db_session, test_user):
    """测试带过滤条件的项目列表"""
    # 创建不同状态的项目
    project1 = ProjectCreate(
        name="计划中项目",
        record_date=date.today(),
        owner_name="负责人",
        status=ProjectStatus.PLANNED,
        department="技术部"
    )
    ProjectService.create(db_session, project1)

    project2 = ProjectCreate(
        name="进行中项目",
        record_date=date.today(),
        owner_name="负责人",
        status=ProjectStatus.IN_PROGRESS,
        department="产品部"
    )
    ProjectService.create(db_session, project2)

    # 按状态过滤
    planned_projects = ProjectService.get_list(db_session, status=ProjectStatus.PLANNED)
    assert len(planned_projects) == 1
    assert planned_projects[0].name == "计划中项目"

    # 按部门过滤
    tech_projects = ProjectService.get_list(db_session, department="技术部")
    assert len(tech_projects) == 1
    assert tech_projects[0].department == "技术部"

def test_update_project(db_session, test_user):
    """测试更新项目"""
    project_data = ProjectCreate(
        name="原始项目",
        record_date=date.today(),
        owner_name="负责人",
        completion=0
    )
    created = ProjectService.create(db_session, project_data)

    # 更新项目
    update_data = ProjectUpdate(
        name="更新后的项目",
        completion=50,
        status=ProjectStatus.IN_PROGRESS
    )
    updated = ProjectService.update(db_session, created.id, update_data)

    assert updated is not None
    assert updated.name == "更新后的项目"
    assert updated.completion == 50
    assert updated.status == ProjectStatus.IN_PROGRESS

def test_update_project_not_found(db_session):
    """测试更新不存在的项目"""
    update_data = ProjectUpdate(name="不存在的项目")
    updated = ProjectService.update(db_session, 99999, update_data)
    assert updated is None

def test_delete_project(db_session, test_user):
    """测试删除项目"""
    project_data = ProjectCreate(
        name="待删除项目",
        record_date=date.today(),
        owner_name="负责人"
    )
    created = ProjectService.create(db_session, project_data)

    # 删除项目
    result = ProjectService.delete(db_session, created.id)
    assert result is True

    # 验证已删除
    fetched = ProjectService.get_by_id(db_session, created.id)
    assert fetched is None

def test_delete_project_not_found(db_session):
    """测试删除不存在的项目"""
    result = ProjectService.delete(db_session, 99999)
    assert result is False

def test_get_project_list_negative_skip(db_session):
    """测试负数 skip 参数"""
    with pytest.raises(ValueError, match="skip and limit must be non-negative"):
        ProjectService.get_list(db_session, skip=-1, limit=10)

def test_get_project_list_negative_limit(db_session):
    """测试负数 limit 参数"""
    with pytest.raises(ValueError, match="skip and limit must be non-negative"):
        ProjectService.get_list(db_session, skip=0, limit=-5)
