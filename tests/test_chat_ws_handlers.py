"""F-202 WebSocket chat handler tests"""
import json

import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock

from api.websocket.manager import Connection, ConnectionManager



def _sent_payload(mock_ws):
    """manager.send 现在走 send_text(json.dumps(...), default=str), 解析最后一条 payload"""
    assert mock_ws.send_text.await_count >= 1, "expected at least one send_text call"
    return json.loads(mock_ws.send_text.await_args[0][0])


@pytest.fixture(autouse=True)
def reset_manager():
    ConnectionManager.reset_instance()
    yield


async def _register_connection(manager, connection_id="chat-test-1", user_id=None, username=None):
    mock_ws = MagicMock()
    mock_ws.send_text = AsyncMock(return_value=True)
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
        call_args = _sent_payload(mock_ws)
        assert call_args["type"] == "error"

    @pytest.mark.asyncio
    async def test_handle_chat_message_missing_fields(self):
        from api.websocket.handlers.chat import handle_chat_message
        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(manager, user_id=uuid.uuid4())
        await handle_chat_message(conn, {"type": "chat_message"})
        call_args = _sent_payload(mock_ws)
        assert call_args["type"] == "error"

    @pytest.mark.asyncio
    async def test_handle_chat_typing_broadcasts(self):
        from api.websocket.handlers.chat import handle_chat_typing
        manager = ConnectionManager()
        user1_id = uuid.uuid4()
        conn1, mock_ws1 = await _register_connection(manager, "c1", user_id=user1_id, username="alice")
        conn2, mock_ws2 = await _register_connection(manager, "c2", user_id=uuid.uuid4(), username="bob")
        await manager.subscribe_room(conn1, 1)
        await manager.subscribe_room(conn2, 1)
        await handle_chat_typing(conn1, {"type": "chat_typing", "room_id": 1, "is_typing": True})
        call_args = _sent_payload(mock_ws2)
        assert call_args["type"] == "chat_typing"
        assert call_args["user_id"] == str(user1_id)
        assert call_args["username"] == "alice"
        assert call_args["is_typing"] is True

    @pytest.mark.asyncio
    async def test_handle_chat_typing_requires_auth(self):
        from api.websocket.handlers.chat import handle_chat_typing
        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(manager)
        await handle_chat_typing(conn, {"type": "chat_typing", "room_id": 1, "is_typing": True})
        call_args = _sent_payload(mock_ws)
        assert call_args["type"] == "error"

    @pytest.mark.asyncio
    async def test_handle_chat_reaction_requires_auth(self):
        from api.websocket.handlers.chat import handle_chat_reaction
        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(manager)
        await handle_chat_reaction(conn, {"type": "chat_reaction", "room_id": 1, "message_id": 1, "emoji": "👍", "add": True})
        call_args = _sent_payload(mock_ws)
        assert call_args["type"] == "error"

    @pytest.mark.asyncio
    async def test_handle_chat_reaction_missing_fields(self):
        from api.websocket.handlers.chat import handle_chat_reaction
        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(manager, user_id=uuid.uuid4())
        await handle_chat_reaction(conn, {"type": "chat_reaction", "room_id": 1})
        call_args = _sent_payload(mock_ws)
        assert call_args["type"] == "error"
