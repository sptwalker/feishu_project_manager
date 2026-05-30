import asyncio
import pytest
from unittest.mock import AsyncMock
from backend.core.config import get_settings
from backend.core.feishu import FeishuAPIError
from backend.services.notification_service import NotificationService
from backend.services import notification_service as ns


@pytest.fixture
def enable_notify():
    s = get_settings()
    old = s.FEISHU_NOTIFY_ENABLED
    s.FEISHU_NOTIFY_ENABLED = True
    yield
    s.FEISHU_NOTIFY_ENABLED = old


def test_disabled_is_noop(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(ns.feishu_client, "send_card", mock)
    sent = asyncio.run(
        NotificationService.notify_task_status_change("u1", "T", "a", "b")
    )
    assert sent is False
    mock.assert_not_called()


def test_enabled_sends_card(monkeypatch, enable_notify):
    mock = AsyncMock(return_value={"message_id": "m"})
    monkeypatch.setattr(ns.feishu_client, "send_card", mock)
    sent = asyncio.run(
        NotificationService.notify_task_status_change("u1", "T", "a", "b", "张三", "P")
    )
    assert sent is True
    mock.assert_awaited_once()


def test_no_receive_id_is_noop(monkeypatch, enable_notify):
    mock = AsyncMock()
    monkeypatch.setattr(ns.feishu_client, "send_card", mock)
    sent = asyncio.run(
        NotificationService.notify_risk_change(None, "R", "a", "b")
    )
    assert sent is False
    mock.assert_not_called()


def test_send_failure_is_handled(monkeypatch, enable_notify):
    mock = AsyncMock(side_effect=FeishuAPIError("boom"))
    monkeypatch.setattr(ns.feishu_client, "send_card", mock)
    sent = asyncio.run(
        NotificationService.notify_task_status_change("u1", "T", "a", "b")
    )
    assert sent is False


def test_risk_notification_sends(monkeypatch, enable_notify):
    mock = AsyncMock(return_value={"message_id": "m"})
    monkeypatch.setattr(ns.feishu_client, "send_card", mock)
    sent = asyncio.run(
        NotificationService.notify_risk_change("u1", "R", "open", "resolved")
    )
    assert sent is True
    mock.assert_awaited_once()
