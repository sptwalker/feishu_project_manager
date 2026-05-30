import pytest
from datetime import date
from pydantic import ValidationError
from backend.schemas.task import TaskCreate, TaskUpdate
from backend.models.task import TaskStatus, TaskPriority


def test_task_create_minimal_valid():
    """最小合法入参可创建 TaskCreate"""
    task = TaskCreate(name="任务A", owner_id=1)
    assert task.name == "任务A"
    assert task.owner_id == 1
    assert task.status == TaskStatus.PENDING
    assert task.priority == TaskPriority.MEDIUM
    assert task.completion == 0
    assert task.parent_task_id is None


def test_task_create_full_valid():
    """完整入参可创建 TaskCreate"""
    task = TaskCreate(
        name="任务B",
        description="描述",
        owner_id=2,
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        completion=50,
        due_date=date(2026, 6, 1),
        start_date=date(2026, 5, 30),
        end_date=date(2026, 6, 1),
        parent_task_id=10,
    )
    assert task.completion == 50
    assert task.parent_task_id == 10


def test_task_name_required():
    """name 缺失应校验失败"""
    with pytest.raises(ValidationError):
        TaskCreate(owner_id=1)


def test_task_name_empty_invalid():
    """name 为空字符串应校验失败"""
    with pytest.raises(ValidationError):
        TaskCreate(name="", owner_id=1)


def test_task_owner_id_must_be_positive():
    """owner_id 必须为正数"""
    with pytest.raises(ValidationError):
        TaskCreate(name="任务", owner_id=0)


def test_task_completion_out_of_range():
    """completion 超出 0-100 范围应校验失败"""
    with pytest.raises(ValidationError):
        TaskCreate(name="任务", owner_id=1, completion=101)
    with pytest.raises(ValidationError):
        TaskCreate(name="任务", owner_id=1, completion=-1)


def test_task_parent_id_must_be_positive():
    """parent_task_id 若提供必须为正数"""
    with pytest.raises(ValidationError):
        TaskCreate(name="任务", owner_id=1, parent_task_id=0)


def test_task_update_all_optional():
    """TaskUpdate 所有字段可选，空入参合法"""
    update = TaskUpdate()
    assert update.model_dump(exclude_unset=True) == {}


def test_task_update_partial():
    """TaskUpdate 部分字段更新"""
    update = TaskUpdate(completion=80, status=TaskStatus.COMPLETED)
    data = update.model_dump(exclude_unset=True)
    assert data == {"completion": 80, "status": TaskStatus.COMPLETED}
