"""F-201 WebSocket room handler tests"""
import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock

from api.websocket.manager import Connection, ConnectionManager


@pytest.fixture(autouse=True)
def reset_manager():
    ConnectionManager.reset_instance()
    yield


async def _register_connection(manager, connection_id="test-1", user_id=None, username=None):
    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock(return_value=True)
    mock_ws.accept = AsyncMock(return_value=None)
    conn = await manager.connect(mock_ws)
    if user_id is not None:
        await manager.bind_user(conn, user_id, username or f"user_{user_id}")
    return conn, mock_ws


class TestManagerRoomIndex:

    @pytest.mark.asyncio
    async def test_subscribe_room_adds_to_index(self):
        manager = ConnectionManager()
        conn, _ = await _register_connection(manager)
        await manager.subscribe_room(conn, 1)
        async with manager._lock:
            assert 1 in manager._room_index
            assert conn.connection_id in manager._room_index[1]

    @pytest.mark.asyncio
    async def test_unsubscribe_room_removes_from_index(self):
        manager = ConnectionManager()
        conn, _ = await _register_connection(manager)
        await manager.subscribe_room(conn, 1)
        await manager.unsubscribe_room(conn, 1)
        async with manager._lock:
            assert 1 not in manager._room_index or conn.connection_id not in manager._room_index[1]

    @pytest.mark.asyncio
    async def test_send_to_room_sends_to_subscribers(self):
        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(manager)
        await manager.subscribe_room(conn, 1)
        count = await manager.send_to_room(1, {"type": "test"})
        assert count == 1
        mock_ws.send_json.assert_called_once_with({"type": "test"})

    @pytest.mark.asyncio
    async def test_send_to_room_multiple_subscribers(self):
        manager = ConnectionManager()
        conn1, mock_ws1 = await _register_connection(manager, "c1")
        conn2, mock_ws2 = await _register_connection(manager, "c2")
        await manager.subscribe_room(conn1, 1)
        await manager.subscribe_room(conn2, 1)
        count = await manager.send_to_room(1, {"type": "test"})
        assert count == 2

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up_room_index(self):
        manager = ConnectionManager()
        conn, _ = await _register_connection(manager)
        await manager.subscribe_room(conn, 1)
        await manager.disconnect(conn)
        async with manager._lock:
            assert 1 not in manager._room_index or conn.connection_id not in manager._room_index[1]


class TestRoomHandlers:

    @pytest.mark.asyncio
    async def test_handle_room_join_subscribes_connection(self):
        from api.websocket.handlers.room import handle_room_join
        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(manager, user_id=uuid.uuid4())
        await handle_room_join(conn, {"type": "room_join", "room_id": 1})
        async with manager._lock:
            assert 1 in manager._room_index
            assert conn.connection_id in manager._room_index[1]

    @pytest.mark.asyncio
    async def test_handle_room_leave_unsubscribes(self):
        from api.websocket.handlers.room import handle_room_leave
        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(manager, user_id=uuid.uuid4())
        await manager.subscribe_room(conn, 1)
        await handle_room_leave(conn, {"type": "room_leave", "room_id": 1})
        async with manager._lock:
            assert 1 not in manager._room_index or conn.connection_id not in manager._room_index[1]

    @pytest.mark.asyncio
    async def test_handle_room_join_requires_auth(self):
        from api.websocket.handlers.room import handle_room_join
        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(manager)
        await handle_room_join(conn, {"type": "room_join", "room_id": 1})
        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert "认证" in call_args.get("error", "")
