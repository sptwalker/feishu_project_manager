import asyncio
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from backend.core.config import get_settings
from backend.models.project import ProjectStatus, ProjectUrgency
from backend.models.task import TaskStatus, TaskPriority
from backend.services.bitable_service import BitableService, BitableConfigError
from backend.services import bitable_service as bs


@pytest.fixture
def configure():
    s = get_settings()
    old = (
        s.FEISHU_BITABLE_APP_TOKEN,
        s.FEISHU_BITABLE_PROJECT_TABLE_ID,
        s.FEISHU_BITABLE_TASK_TABLE_ID,
    )
    s.FEISHU_BITABLE_APP_TOKEN = "app-token"
    s.FEISHU_BITABLE_PROJECT_TABLE_ID = "ptbl"
    s.FEISHU_BITABLE_TASK_TABLE_ID = "ttbl"
    yield
    (
        s.FEISHU_BITABLE_APP_TOKEN,
        s.FEISHU_BITABLE_PROJECT_TABLE_ID,
        s.FEISHU_BITABLE_TASK_TABLE_ID,
    ) = old


def _project():
    return SimpleNamespace(
        id=1, name="P", status=ProjectStatus.IN_PROGRESS,
        urgency=ProjectUrgency.HIGH, completion=50, department="研发",
    )


def _task():
    return SimpleNamespace(
        id=2, name="T", project_id=1, status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH, completion=30,
    )


def test_project_to_fields():
    f = BitableService.project_to_fields(_project())
    assert f["项目名称"] == "P"
    assert f["状态"] == "in_progress"
    assert f["完成度"] == 50
    assert f["紧急程度"] == "high"


def test_task_to_fields():
    f = BitableService.task_to_fields(_task())
    assert f["任务名称"] == "T"
    assert f["状态"] == "in_progress"
    assert f["优先级"] == "high"
    assert f["项目ID"] == 1


def test_sync_project_creates_when_no_record_id(monkeypatch, configure):
    create = AsyncMock(return_value={"record": {"record_id": "rec9"}})
    update = AsyncMock()
    monkeypatch.setattr(bs.feishu_client, "bitable_create_record", create)
    monkeypatch.setattr(bs.feishu_client, "bitable_update_record", update)

    rid = asyncio.run(BitableService.sync_project(_project()))
    assert rid == "rec9"
    create.assert_awaited_once()
    update.assert_not_called()


def test_sync_project_updates_when_record_id(monkeypatch, configure):
    create = AsyncMock()
    update = AsyncMock(return_value={})
    monkeypatch.setattr(bs.feishu_client, "bitable_create_record", create)
    monkeypatch.setattr(bs.feishu_client, "bitable_update_record", update)

    rid = asyncio.run(BitableService.sync_project(_project(), record_id="recX"))
    assert rid == "recX"
    update.assert_awaited_once()
    create.assert_not_called()


def test_sync_task_creates(monkeypatch, configure):
    create = AsyncMock(return_value={"record": {"record_id": "rt1"}})
    monkeypatch.setattr(bs.feishu_client, "bitable_create_record", create)
    rid = asyncio.run(BitableService.sync_task(_task()))
    assert rid == "rt1"


def test_config_error_when_unset():
    s = get_settings()
    old = s.FEISHU_BITABLE_APP_TOKEN
    s.FEISHU_BITABLE_APP_TOKEN = ""
    try:
        with pytest.raises(BitableConfigError):
            asyncio.run(BitableService.sync_project(_project()))
    finally:
        s.FEISHU_BITABLE_APP_TOKEN = old
