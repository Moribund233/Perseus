"""F-202 WebSocket chat handler tests"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from api.websocket.manager import Connection, ConnectionManager


@pytest.fixture(autouse=True)
def reset_manager():
    ConnectionManager.reset_instance()
    yield


async def _register_connection(manager, connection_id="chat-test-1", user_id=None, username=None):
    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock(return_value=True)
    mock_ws.accept = AsyncMock(return_value=None)
    conn = await manager.connect(mock_ws)
    if user_id is not None:
        await manager.bind_user(conn, user_id, username or f"user_{user_id}")
    return conn, mock_ws


class TestChatHandlers:

    @pytest.mark.asyncio
    async def test_handle_chat_message_requires_auth(self):
        from api.websocket.handlers.chat import handle_chat_message
        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(manager)
        await handle_chat_message(conn, {"type": "chat_message", "room_id": 1, "content": "hello"})
        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "error"

    @pytest.mark.asyncio
    async def test_handle_chat_message_missing_fields(self):
        from api.websocket.handlers.chat import handle_chat_message
        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(manager, user_id=1)
        await handle_chat_message(conn, {"type": "chat_message"})
        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "error"

    @pytest.mark.asyncio
    async def test_handle_chat_typing_broadcasts(self):
        from api.websocket.handlers.chat import handle_chat_typing
        manager = ConnectionManager()
        conn1, mock_ws1 = await _register_connection(manager, "c1", user_id=1, username="alice")
        conn2, mock_ws2 = await _register_connection(manager, "c2", user_id=2, username="bob")
        await manager.subscribe_room(conn1, 1)
        await manager.subscribe_room(conn2, 1)
        await handle_chat_typing(conn1, {"type": "chat_typing", "room_id": 1, "is_typing": True})
        mock_ws2.send_json.assert_called_once()
        call_args = mock_ws2.send_json.call_args[0][0]
        assert call_args["type"] == "chat_typing"
        assert call_args["user_id"] == 1
        assert call_args["username"] == "alice"
        assert call_args["is_typing"] is True

    @pytest.mark.asyncio
    async def test_handle_chat_typing_requires_auth(self):
        from api.websocket.handlers.chat import handle_chat_typing
        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(manager)
        await handle_chat_typing(conn, {"type": "chat_typing", "room_id": 1, "is_typing": True})
        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "error"
