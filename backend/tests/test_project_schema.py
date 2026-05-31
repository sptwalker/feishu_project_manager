import pytest
from datetime import date
from pydantic import ValidationError
from backend.schemas.project import ProjectCreate, ProjectUpdate
from backend.models.project import ProjectStatus, ProjectUrgency


def test_project_create_valid():
    """合法入参可创建 ProjectCreate"""
    project = ProjectCreate(
        name="测试项目",
        record_date=date(2026, 5, 30),
        owner_name="负责人",
    )
    assert project.name == "测试项目"
    assert project.owner_name == "负责人"
    assert project.status == ProjectStatus.PLANNED


def test_project_owner_name_optional():
    """owner_name 可选：不提供也能创建（与用户账号解耦）"""
    project = ProjectCreate(name="测试", record_date=date(2026, 5, 30))
    assert project.owner_name is None


def test_project_name_required():
    """缺少 name 应校验失败"""
    with pytest.raises(ValidationError):
        ProjectCreate(record_date=date(2026, 5, 30), owner_name="负责人")


def test_project_record_date_required():
    """缺少 record_date 应校验失败"""
    with pytest.raises(ValidationError):
        ProjectCreate(name="测试", owner_name="负责人")


def test_project_completion_range():
    """completion 超出范围应校验失败"""
    with pytest.raises(ValidationError):
        ProjectCreate(name="测试", record_date=date(2026, 5, 30), completion=101)
    with pytest.raises(ValidationError):
        ProjectCreate(name="测试", record_date=date(2026, 5, 30), completion=-1)


def test_project_update_all_optional():
    """ProjectUpdate 所有字段可选，空入参合法"""
    update = ProjectUpdate()
    assert update.model_dump(exclude_unset=True) == {}


def test_project_update_partial():
    """ProjectUpdate 部分字段更新"""
    update = ProjectUpdate(status=ProjectStatus.IN_PROGRESS, owner_name="新负责人")
    data = update.model_dump(exclude_unset=True)
    assert data == {"status": ProjectStatus.IN_PROGRESS, "owner_name": "新负责人"}
