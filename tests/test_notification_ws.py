# tests/test_notification_ws.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from api.websocket.manager import Connection, ConnectionManager
from api.websocket.handlers.notification import (
    handle_ping, handle_subscribe, handle_unsubscribe,
    notify_commit_new, notify_user,
)


@pytest.mark.asyncio
async def test_handle_ping():
    conn = AsyncMock(spec=Connection)
    conn.metadata = {}
    message = {"type": "ping", "timestamp": "2024-01-01T00:00:00Z"}

    await handle_ping(conn, message)

    conn.send.assert_called_once()
    sent = conn.send.call_args[0][0]
    assert sent["type"] == "pong"
    assert sent["timestamp"] == "2024-01-01T00:00:00Z"
    assert "server_time" in sent


@pytest.mark.asyncio
async def test_handle_subscribe_repository():
    conn = AsyncMock(spec=Connection)
    conn.username = "testuser"
    manager_mock = MagicMock(spec=ConnectionManager)

    with patch("api.websocket.handlers.notification.manager", manager_mock):
        message = {"type": "subscribe", "channel": "repository", "repository_id": 42}
        await handle_subscribe(conn, message)

    manager_mock.subscribe_repository.assert_called_once_with(conn, 42)
    conn.send.assert_called_once()
    sent = conn.send.call_args[0][0]
    assert sent["type"] == "subscribed"
    assert sent["channel"] == "repository"


@pytest.mark.asyncio
async def test_handle_subscribe_repository_missing_id():
    conn = AsyncMock(spec=Connection)
    message = {"type": "subscribe", "channel": "repository"}
    await handle_subscribe(conn, message)

    conn.send.assert_called_once()
    sent = conn.send.call_args[0][0]
    assert sent["type"] == "error"
    assert "repository_id" in sent["error"]


@pytest.mark.asyncio
async def test_handle_subscribe_user_notifications():
    conn = AsyncMock(spec=Connection)
    message = {"type": "subscribe", "channel": "user_notifications"}
    await handle_subscribe(conn, message)

    conn.send.assert_called_once()
    sent = conn.send.call_args[0][0]
    assert sent["type"] == "subscribed"
    assert sent["channel"] == "user_notifications"


@pytest.mark.asyncio
async def test_handle_subscribe_unknown_channel():
    conn = AsyncMock(spec=Connection)
    message = {"type": "subscribe", "channel": "unknown_channel"}
    await handle_subscribe(conn, message)

    conn.send.assert_called_once()
    sent = conn.send.call_args[0][0]
    assert sent["type"] == "error"


@pytest.mark.asyncio
async def test_handle_unsubscribe_repository():
    conn = AsyncMock(spec=Connection)
    manager_mock = MagicMock(spec=ConnectionManager)

    with patch("api.websocket.handlers.notification.manager", manager_mock):
        message = {"type": "unsubscribe", "channel": "repository", "repository_id": 42}
        await handle_unsubscribe(conn, message)

    manager_mock.unsubscribe_repository.assert_called_once_with(conn, 42)
    conn.send.assert_called_once()
    sent = conn.send.call_args[0][0]
    assert sent["type"] == "unsubscribed"


@pytest.mark.asyncio
async def test_notify_commit_new():
    manager_mock = MagicMock(spec=ConnectionManager)
    manager_mock.send_to_repository = AsyncMock(return_value=3)

    with patch("api.websocket.handlers.notification.manager", manager_mock):
        count = await notify_commit_new(
            repository_id=1,
            commit_data={"sha": "abc123", "message": "test"},
            exclude_user_id=5,
        )

    assert count == 3
    manager_mock.send_to_repository.assert_called_once()
    call_args = manager_mock.send_to_repository.call_args
    assert call_args[0][0] == 1
    assert call_args[0][1]["type"] == "notification"
    assert call_args[0][1]["action"] == "commit_new"
    assert call_args[0][2] == 5


@pytest.mark.asyncio
async def test_notify_user():
    manager_mock = MagicMock(spec=ConnectionManager)
    manager_mock.send_to_user = AsyncMock(return_value=1)

    with patch("api.websocket.handlers.notification.manager", manager_mock):
        count = await notify_user(
            user_id=10,
            notification_type="mention",
            data={"message": "You were mentioned"},
        )

    assert count == 1
    manager_mock.send_to_user.assert_called_once()
    call_args = manager_mock.send_to_user.call_args
    assert call_args[0][0] == 10
    assert call_args[0][1]["type"] == "user_notification"
