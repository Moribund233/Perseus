"""F-206 Online Presence — WebSocket handler tests"""
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


async def _register_connection(manager, user_id=None, username=None):
    mock_ws = MagicMock()
    mock_ws.send_text = AsyncMock(return_value=True)
    mock_ws.accept = AsyncMock(return_value=None)
    conn = await manager.connect(mock_ws)
    if user_id is not None:
        await manager.bind_user(conn, user_id, username or f"user_{user_id}")
    return conn, mock_ws


class TestPresenceHelpers:

    @pytest.mark.asyncio
    async def test_get_room_connections_returns_subscribed_connections(self):
        manager = ConnectionManager()
        user1_id = uuid.uuid4()
        user2_id = uuid.uuid4()
        conn1, _ = await _register_connection(manager, user_id=user1_id, username="alice")
        conn2, _ = await _register_connection(manager, user_id=user2_id, username="bob")
        await manager.subscribe_room(conn1, 1)
        await manager.subscribe_room(conn2, 1)
        result = await manager.get_room_connections(1)
        assert len(result) == 2
        user_ids = {c.user_id for c in result}
        assert user_ids == {user1_id, user2_id}

    @pytest.mark.asyncio
    async def test_get_room_connections_empty_room(self):
        manager = ConnectionManager()
        result = await manager.get_room_connections(999)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_room_online_users_returns_unique_users(self):
        manager = ConnectionManager()
        user1_id = uuid.uuid4()
        user2_id = uuid.uuid4()
        conn1, _ = await _register_connection(manager, user_id=user1_id, username="alice")
        conn2a, _ = await _register_connection(manager, user_id=user2_id, username="bob")
        conn2b, _ = await _register_connection(manager, user_id=user2_id, username="bob")
        await manager.subscribe_room(conn1, 1)
        await manager.subscribe_room(conn2a, 1)
        await manager.subscribe_room(conn2b, 1)
        users = await manager.get_room_online_users(1)
        assert len(users) == 2
        user_ids = {u["user_id"] for u in users}
        assert user_ids == {user1_id, user2_id}

    @pytest.mark.asyncio
    async def test_get_room_online_users_no_duplicates(self):
        manager = ConnectionManager()
        user_id = uuid.uuid4()
        conn, _ = await _register_connection(manager, user_id=user_id, username="alice")
        await manager.subscribe_room(conn, 1)
        users = await manager.get_room_online_users(1)
        alice = [u for u in users if u["user_id"] == user_id][0]
        assert alice["username"] == "alice"


class TestPresenceHandlers:

    @pytest.mark.asyncio
    async def test_room_join_broadcasts_presence_change(self):
        from api.websocket.handlers.room import handle_room_join
        manager = ConnectionManager()
        alice_id = uuid.uuid4()
        conn_alice, mock_alice = await _register_connection(manager, user_id=alice_id, username="alice")
        conn_bob, mock_bob = await _register_connection(manager, user_id=uuid.uuid4(), username="bob")
        await manager.subscribe_room(conn_bob, 1)
        await handle_room_join(conn_alice, {"type": "room_join", "room_id": 1})
        presence_calls = [
            c for c in mock_bob.send_text.call_args_list
            if json.loads(c[0][0]).get("type") == "presence_join"
        ]
        assert len(presence_calls) == 1
        assert json.loads(presence_calls[0][0][0])["user_id"] == str(alice_id)
        assert json.loads(presence_calls[0][0][0])["username"] == "alice"

    @pytest.mark.asyncio
    async def test_room_leave_broadcasts_presence_change(self):
        from api.websocket.handlers.room import handle_room_leave
        manager = ConnectionManager()
        alice_id = uuid.uuid4()
        conn_alice, mock_alice = await _register_connection(manager, user_id=alice_id, username="alice")
        conn_bob, mock_bob = await _register_connection(manager, user_id=uuid.uuid4(), username="bob")
        await manager.subscribe_room(conn_alice, 1)
        await manager.subscribe_room(conn_bob, 1)
        mock_bob.send_text.reset_mock()
        await handle_room_leave(conn_alice, {"type": "room_leave", "room_id": 1})
        presence_calls = [
            c for c in mock_bob.send_text.call_args_list
            if json.loads(c[0][0]).get("type") == "presence_leave"
        ]
        assert len(presence_calls) == 1
        assert json.loads(presence_calls[0][0][0])["user_id"] == str(alice_id)

    @pytest.mark.asyncio
    async def test_presence_list_returns_online_users(self):
        from api.websocket.handlers.room import handle_presence_list
        manager = ConnectionManager()
        conn_alice, mock_alice = await _register_connection(manager, user_id=uuid.uuid4(), username="alice")
        conn_bob, _ = await _register_connection(manager, user_id=uuid.uuid4(), username="bob")
        await manager.subscribe_room(conn_alice, 1)
        await manager.subscribe_room(conn_bob, 1)
        await handle_presence_list(conn_alice, {"type": "presence_list", "room_id": 1})
        sent = _sent_payload(mock_alice)
        assert sent["type"] == "presence_list"
        assert len(sent["users"]) == 2

    @pytest.mark.asyncio
    async def test_presence_list_requires_auth(self):
        from api.websocket.handlers.room import handle_presence_list
        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(manager)
        await handle_presence_list(conn, {"type": "presence_list", "room_id": 1})
        sent = _sent_payload(mock_ws)
        assert sent["type"] == "error"

    @pytest.mark.asyncio
    async def test_disconnect_broadcasts_presence_leave(self):
        manager = ConnectionManager()
        alice_id = uuid.uuid4()
        conn_alice, mock_alice = await _register_connection(manager, user_id=alice_id, username="alice")
        conn_bob, mock_bob = await _register_connection(manager, user_id=uuid.uuid4(), username="bob")
        await manager.subscribe_room(conn_alice, 1)
        await manager.subscribe_room(conn_bob, 1)
        mock_bob.send_text.reset_mock()
        await manager.disconnect(conn_alice)
        presence_calls = [
            c for c in mock_bob.send_text.call_args_list
            if json.loads(c[0][0]).get("type") == "presence_leave"
        ]
        assert len(presence_calls) >= 1
        last_leave = json.loads(presence_calls[-1][0][0])
        assert last_leave["user_id"] == str(alice_id)
