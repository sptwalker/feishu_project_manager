import pytest
from datetime import date
from pydantic import ValidationError
from backend.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from backend.models.project import ProjectStatus, ProjectUrgency

def test_project_create_valid():
    """测试有效的项目创建数据"""
    data = {
        "name": "测试项目",
        "record_date": "2026-05-30",
        "content": "项目描述",
        "status": "planned",
        "urgency": "medium",
        "department": "技术部",
        "owner_id": 1,
        "completion": 0,
        "estimated_end_date": "2026-12-31"
    }
    project = ProjectCreate(**data)
    assert project.name == "测试项目"
    assert project.completion == 0

def test_project_create_invalid_completion():
    """测试无效的完成度"""
    data = {
        "name": "测试项目",
        "record_date": "2026-05-30",
        "owner_id": 1,
        "completion": 150
    }
    with pytest.raises(ValidationError):
        ProjectCreate(**data)
