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
from backend.models.risk import RiskStatus
from backend.schemas.risk import RiskCreate, RiskUpdate
from backend.services.risk_service import RiskService


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
    user = User(feishu_user_id="risk_owner", name="风险负责人", role=UserRole.MEMBER)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def project(db_session, owner):
    proj = Project(name="风险测试项目", record_date=date(2026, 5, 30), owner_id=owner.id)
    db_session.add(proj)
    db_session.commit()
    db_session.refresh(proj)
    return proj


def test_create_risk(db_session, project, owner):
    """创建风险"""
    risk = RiskService.create(
        db_session, project.id, RiskCreate(title="风险1", owner_id=owner.id)
    )
    assert risk.id is not None
    assert risk.project_id == project.id
    assert risk.status == RiskStatus.OPEN


def test_create_risk_without_owner(db_session, project):
    """无负责人也可创建风险"""
    risk = RiskService.create(db_session, project.id, RiskCreate(title="无主风险"))
    assert risk.id is not None
    assert risk.owner_id is None


def test_get_by_id(db_session, project):
    """根据ID获取风险"""
    created = RiskService.create(db_session, project.id, RiskCreate(title="风险2"))
    fetched = RiskService.get_by_id(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id


def test_get_by_id_not_found(db_session):
    """获取不存在的风险返回 None"""
    assert RiskService.get_by_id(db_session, 99999) is None


def test_get_list_scoped_to_project(db_session, project, owner):
    """列表仅返回所属项目的风险"""
    other = Project(name="其他项目", record_date=date(2026, 5, 30), owner_id=owner.id)
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    RiskService.create(db_session, project.id, RiskCreate(title="A"))
    RiskService.create(db_session, other.id, RiskCreate(title="B"))

    risks = RiskService.get_list(db_session, project_id=project.id)
    assert len(risks) == 1
    assert risks[0].title == "A"


def test_get_list_filter_by_status(db_session, project):
    """按状态过滤风险列表"""
    RiskService.create(db_session, project.id, RiskCreate(title="开启", status=RiskStatus.OPEN))
    RiskService.create(db_session, project.id, RiskCreate(title="已解决", status=RiskStatus.RESOLVED))

    risks = RiskService.get_list(db_session, project_id=project.id, status=RiskStatus.RESOLVED)
    assert len(risks) == 1
    assert risks[0].title == "已解决"


def test_get_list_negative_pagination_raises(db_session, project):
    """skip/limit 为负数抛出 ValueError"""
    with pytest.raises(ValueError):
        RiskService.get_list(db_session, project_id=project.id, limit=-1)


def test_update_risk(db_session, project):
    """更新风险"""
    risk = RiskService.create(db_session, project.id, RiskCreate(title="原标题"))
    updated = RiskService.update(db_session, risk.id, RiskUpdate(title="新标题", status=RiskStatus.MONITORING))
    assert updated.title == "新标题"
    assert updated.status == RiskStatus.MONITORING


def test_update_risk_not_found(db_session):
    """更新不存在的风险返回 None"""
    assert RiskService.update(db_session, 99999, RiskUpdate(title="x")) is None


def test_delete_risk(db_session, project):
    """删除风险"""
    risk = RiskService.create(db_session, project.id, RiskCreate(title="待删"))
    assert RiskService.delete(db_session, risk.id) is True
    assert RiskService.get_by_id(db_session, risk.id) is None


def test_delete_risk_not_found(db_session):
    """删除不存在的风险返回 False"""
    assert RiskService.delete(db_session, 99999) is False
