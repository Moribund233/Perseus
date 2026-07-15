"""Tests for WebSocket connection manager"""
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock
import pytest

from api.websocket.manager import Connection, ConnectionManager


def _make_uuid(n: int) -> uuid.UUID:
    return uuid.UUID(int=n)


class TestConnection:
    """Connection unit tests"""

    def test_is_timeout_within_limit(self):
        """Returns False when within timeout limit"""
        mock_ws = MagicMock()
        conn = Connection(mock_ws, "test-1")
        conn.last_ping = datetime.now()
        assert not conn.is_timeout(timeout_seconds=120)

    def test_is_timeout_exceeds_limit(self):
        """Returns True when exceeds timeout limit"""
        mock_ws = MagicMock()
        conn = Connection(mock_ws, "test-2")
        conn.last_ping = datetime.now() - timedelta(seconds=130)
        assert conn.is_timeout(timeout_seconds=120)

    def test_is_timeout_crosses_day_boundary(self):
        """
        Returns True even when timedelta crosses a day boundary.

        Bug: (now - last_ping).seconds ignores the .days component.
        If last_ping is 1 day + 10s ago, .seconds=10 which is < 120,
        incorrectly reporting not timed out.
        """
        mock_ws = MagicMock()
        conn = Connection(mock_ws, "test-3")
        conn.last_ping = datetime.now() - timedelta(days=1, seconds=10)
        assert conn.is_timeout(timeout_seconds=120)

    def test_is_timeout_zero_seconds(self):
        """Returns False for zero elapsed time"""
        mock_ws = MagicMock()
        conn = Connection(mock_ws, "test-4")
        conn.last_ping = datetime.now()
        assert not conn.is_timeout(timeout_seconds=0)

    def test_is_timeout_negative_elapsed(self):
        """Returns False when last_ping is in the future (clock skew)"""
        mock_ws = MagicMock()
        conn = Connection(mock_ws, "test-5")
        conn.last_ping = datetime.now() + timedelta(seconds=10)
        assert not conn.is_timeout(timeout_seconds=120)

    def test_is_timeout_many_days_ago(self):
        """Returns True when connection is many days old"""
        mock_ws = MagicMock()
        conn = Connection(mock_ws, "test-6")
        conn.last_ping = datetime.now() - timedelta(days=7)
        assert conn.is_timeout(timeout_seconds=120)

    @pytest.mark.asyncio
    async def test_connection_send_marks_dead_on_failure(self):
        """send() sets is_alive=False when sending fails"""
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(side_effect=Exception("send failed"))
        conn = Connection(mock_ws, "test-7")

        result = await conn.send({"type": "ping"})

        assert result is False
        assert conn.is_alive is False

    def test_connection_bind_user_sets_attributes(self):
        """bind_user sets user_id and username"""
        mock_ws = MagicMock()
        conn = Connection(mock_ws, "test-8")
        user_id = uuid.uuid4()

        conn.bind_user(user_id=user_id, username="alice")

        assert conn.user_id == user_id
        assert conn.username == "alice"

    def test_connection_subscribe_unsubscribe_repository(self):
        """subscribe_repository and unsubscribe_repository work correctly"""
        mock_ws = MagicMock()
        conn = Connection(mock_ws, "test-9")
        rid1 = _make_uuid(1)
        rid2 = _make_uuid(2)

        conn.subscribe_repository(rid1)
        conn.subscribe_repository(rid2)
        assert conn.repository_ids == {rid1, rid2}

        conn.unsubscribe_repository(rid1)
        assert conn.repository_ids == {rid2}

        conn.unsubscribe_repository(_make_uuid(999))  # not subscribed
        assert conn.repository_ids == {rid2}

    def test_connection_to_dict_returns_expected_keys(self):
        """to_dict returns serializable representation"""
        mock_ws = MagicMock()
        conn = Connection(mock_ws, "test-10")
        user_id = uuid.uuid4()
        conn.bind_user(user_id=user_id, username="bob")
        conn.subscribe_repository(_make_uuid(100))

        d = conn.to_dict()

        assert d["connection_id"] == "test-10"
        assert d["user_id"] == user_id
        assert d["username"] == "bob"
        assert d["repository_ids"] == [_make_uuid(100)]
        assert d["is_alive"] is True
        assert "connected_at" in d
        assert "last_ping" in d

    def test_connection_update_ping_refreshes_time(self):
        """update_ping updates last_ping to current time"""
        mock_ws = MagicMock()
        conn = Connection(mock_ws, "test-11")
        old_ping = conn.last_ping

        conn.update_ping()

        assert conn.last_ping >= old_ping


class TestConnectionManager:
    """ConnectionManager concurrency and indexing tests"""

    def setup_method(self):
        ConnectionManager.reset_instance()

    def _make_mock_ws(self):
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock(return_value=True)
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_and_disconnect_basic(self):
        """Basic connect/disconnect cycle"""
        mgr = ConnectionManager()

        ws = self._make_mock_ws()
        conn = await mgr.connect(ws)
        async with mgr._lock:
            assert conn.connection_id in mgr._connections

        await mgr.disconnect(conn)
        async with mgr._lock:
            assert conn.connection_id not in mgr._connections

    @pytest.mark.asyncio
    async def test_bind_user_indexing(self):
        """bind_user adds connection to _user_index"""
        mgr = ConnectionManager()
        ws = self._make_mock_ws()
        conn = await mgr.connect(ws)
        user_id = _make_uuid(1)

        await mgr.bind_user(conn, user_id=user_id, username="alice")

        async with mgr._lock:
            assert user_id in mgr._user_index
            assert conn.connection_id in mgr._user_index[user_id]
        assert conn.user_id == user_id

        await mgr.disconnect(conn)
        async with mgr._lock:
            assert user_id not in mgr._user_index

    @pytest.mark.asyncio
    async def test_subscribe_repository_indexing(self):
        """subscribe_repository adds connection to _repository_index"""
        mgr = ConnectionManager()
        ws = self._make_mock_ws()
        conn = await mgr.connect(ws)
        rid = _make_uuid(42)

        await mgr.subscribe_repository(conn, rid)
        async with mgr._lock:
            assert rid in mgr._repository_index
            assert conn.connection_id in mgr._repository_index[rid]

        await mgr.unsubscribe_repository(conn, rid)
        async with mgr._lock:
            assert rid not in mgr._repository_index
        await mgr.disconnect(conn)

    @pytest.mark.asyncio
    async def test_concurrent_connect_disconnect_no_corruption(self):
        """Many concurrent connect/disconnect operations don't corrupt state"""
        mgr = ConnectionManager()
        n = 50

        async def connect_disconnect_loop(uid: int):
            _uid = _make_uuid(uid)
            for _ in range(10):
                ws = self._make_mock_ws()
                conn = await mgr.connect(ws)
                await mgr.bind_user(conn, _uid, f"user-{uid}")
                await mgr.subscribe_repository(conn, _make_uuid(uid % 5))
                await asyncio.sleep(0)
                await mgr.disconnect(conn)

        tasks = [connect_disconnect_loop(i) for i in range(n)]
        await asyncio.gather(*tasks)

        # After all tasks complete, manager should be empty
        async with mgr._lock:
            assert len(mgr._connections) == 0
            assert len(mgr._user_index) == 0
            assert len(mgr._repository_index) == 0
        assert mgr._connection_counter == n * 10  # each connect increments

    @pytest.mark.asyncio
    async def test_concurrent_send_to_user(self):
        """send_to_user works correctly under concurrent access"""
        mgr = ConnectionManager()
        ws = self._make_mock_ws()
        conn = await mgr.connect(ws)
        user_id = _make_uuid(1)
        await mgr.bind_user(conn, user_id, "alice")

        async def send_concurrently():
            return await mgr.send_to_user(user_id, {"type": "ping"})

        results = await asyncio.gather(*[send_concurrently() for _ in range(20)])
        assert all(r == 1 for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_send_to_repository(self):
        """send_to_repository works correctly under concurrent access"""
        mgr = ConnectionManager()
        ws = self._make_mock_ws()
        conn = await mgr.connect(ws)
        user_id = _make_uuid(1)
        rid = _make_uuid(100)
        await mgr.bind_user(conn, user_id, "alice")
        await mgr.subscribe_repository(conn, rid)

        async def send_concurrently():
            return await mgr.send_to_repository(rid, {"type": "notification"})

        results = await asyncio.gather(*[send_concurrently() for _ in range(20)])
        assert all(r == 1 for r in results)

    @pytest.mark.asyncio
    async def test_user_rebind_updates_index(self):
        """Rebinding a connection to a different user updates index correctly"""
        mgr = ConnectionManager()
        ws = self._make_mock_ws()
        conn = await mgr.connect(ws)
        uid1 = _make_uuid(1)
        uid2 = _make_uuid(2)

        await mgr.bind_user(conn, uid1, "alice")
        async with mgr._lock:
            assert uid1 in mgr._user_index
            assert conn.connection_id in mgr._user_index[uid1]

        await mgr.bind_user(conn, uid2, "bob")
        async with mgr._lock:
            assert uid2 in mgr._user_index
            assert conn.connection_id in mgr._user_index[uid2]
            assert uid1 not in mgr._user_index or conn.connection_id not in mgr._user_index.get(uid1, set())

        await mgr.disconnect(conn)
        async with mgr._lock:
            assert uid2 not in mgr._user_index

    @pytest.mark.asyncio
    async def test_stats_under_concurrent_load(self):
        """get_stats returns consistent data under concurrent load"""
        mgr = ConnectionManager()
        n = 20

        async def create(uid: int):
            _uid = _make_uuid(uid)
            ws = self._make_mock_ws()
            conn = await mgr.connect(ws)
            await mgr.bind_user(conn, _uid, f"u-{uid}")
            await mgr.subscribe_repository(conn, _make_uuid(uid % 3))
            return conn

        conns = await asyncio.gather(*[create(i) for i in range(n)])

        stats = await mgr.get_stats()
        assert stats["total_connections"] == n
        assert stats["active_users"] == n
        assert stats["subscribed_repositories"] == 3

        for c in conns:
            await mgr.disconnect(c)

        stats = await mgr.get_stats()
        assert stats["total_connections"] == 0
