"""Presence 全局注册表（services/realtime/presence_service）+ manager 接线（规划 R4）"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.realtime import presence_service
from services.realtime.presence_service import PresenceStore


class _Pipe:
    def __init__(self, client):
        self._c = client
        self._cmds = []

    def hincrby(self, *a):
        self._cmds.append(("hincrby", a))
        return self

    def hset(self, *a):
        self._cmds.append(("hset", a))
        return self

    def expire(self, *a):
        self._cmds.append(("expire", a))
        return self

    async def execute(self):
        for name, args in self._cmds:
            await getattr(self._c, name)(*args)


class _FakeRedis:
    def __init__(self):
        self.hashes = {}

    def pipeline(self):
        return _Pipe(self)

    async def hincrby(self, key, field, delta):
        h = self.hashes.setdefault(key, {})
        h[field] = h.get(field, 0) + delta
        return h[field]

    async def hset(self, key, field, value):
        self.hashes.setdefault(key, {})[field] = value
        return 1

    async def hdel(self, key, field):
        self.hashes.get(key, {}).pop(field, None)
        return 1

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    async def expire(self, key, ttl):
        return True


@pytest.fixture
def no_redis(monkeypatch):
    async def _none():
        return None

    monkeypatch.setattr(presence_service, "get_redis", _none)


@pytest.fixture
def fake_redis(monkeypatch):
    fake = _FakeRedis()

    async def _fake():
        return fake

    monkeypatch.setattr(presence_service, "get_redis", _fake)
    return fake


async def test_disabled_without_redis(no_redis):
    store = PresenceStore()
    assert await store.enabled() is False
    await store.add(1, uuid.uuid4(), "alice")  # no-op
    assert await store.list_users(1) == []


async def test_add_and_list_unique_user(fake_redis):
    store = PresenceStore()
    uid = uuid.uuid4()
    await store.add(1, uid, "alice")
    await store.add(1, uid, "alice")  # 两个连接

    users = await store.list_users(1)
    assert len(users) == 1
    assert users[0]["user_id"] == uid
    assert users[0]["username"] == "alice"


async def test_remove_decrements_and_cleans(fake_redis):
    store = PresenceStore()
    uid = uuid.uuid4()
    await store.add(1, uid, "alice")
    await store.add(1, uid, "alice")

    await store.remove(1, uid)
    assert len(await store.list_users(1)) == 1  # 仍有一个连接

    await store.remove(1, uid)
    assert await store.list_users(1) == []  # 归零清理


async def test_multiple_users(fake_redis):
    store = PresenceStore()
    a, b = uuid.uuid4(), uuid.uuid4()
    await store.add(1, a, "alice")
    await store.add(1, b, "bob")
    ids = {u["user_id"] for u in await store.list_users(1)}
    assert ids == {a, b}


async def test_refresh_noop_without_rooms(fake_redis):
    store = PresenceStore()
    await store.refresh([])  # 不抛错


# ---------------- manager 接线 ----------------

class _StubPresence:
    def __init__(self):
        self.added = []
        self.removed = []
        self.users = []
        self.refreshed = []
        self._enabled = True

    async def enabled(self):
        return self._enabled

    async def add(self, room_id, user_id, username):
        self.added.append((room_id, user_id, username))

    async def remove(self, room_id, user_id):
        self.removed.append((room_id, user_id))

    async def list_users(self, room_id):
        return self.users

    async def refresh(self, room_ids):
        self.refreshed.append(list(room_ids))


@pytest.fixture(autouse=True)
def _reset_manager():
    from api.websocket.manager import ConnectionManager
    ConnectionManager.reset_instance()
    yield
    ConnectionManager.reset_instance()


async def _register(mgr, user_id=None, username=None):
    ws = MagicMock()
    ws.accept = AsyncMock(return_value=None)
    ws.send_text = AsyncMock(return_value=True)
    ws.close = AsyncMock(return_value=None)
    conn = await mgr.connect(ws)
    if user_id is not None:
        await mgr.bind_user(conn, user_id, username or "u")
    return conn, ws


async def test_manager_subscribe_adds_presence_idempotent():
    from api.websocket.manager import ConnectionManager

    mgr = ConnectionManager()
    stub = _StubPresence()
    mgr.set_presence(stub)
    uid = uuid.uuid4()
    conn, _ = await _register(mgr, user_id=uid, username="alice")

    await mgr.subscribe_room(conn, 1)
    await mgr.subscribe_room(conn, 1)  # 幂等，不重复计数

    assert stub.added == [(1, uid, "alice")]


async def test_manager_unsubscribe_removes_presence():
    from api.websocket.manager import ConnectionManager

    mgr = ConnectionManager()
    stub = _StubPresence()
    mgr.set_presence(stub)
    uid = uuid.uuid4()
    conn, _ = await _register(mgr, user_id=uid, username="alice")

    await mgr.subscribe_room(conn, 1)
    await mgr.unsubscribe_room(conn, 1)

    assert stub.removed == [(1, uid)]


async def test_manager_disconnect_removes_presence():
    from api.websocket.manager import ConnectionManager

    mgr = ConnectionManager()
    stub = _StubPresence()
    mgr.set_presence(stub)
    uid = uuid.uuid4()
    conn, _ = await _register(mgr, user_id=uid, username="alice")
    await mgr.subscribe_room(conn, 1)

    await mgr.disconnect(conn)

    assert (1, uid) in stub.removed


async def test_manager_online_users_delegates_to_presence():
    from api.websocket.manager import ConnectionManager

    mgr = ConnectionManager()
    stub = _StubPresence()
    uid = uuid.uuid4()
    stub.users = [{"user_id": uid, "username": "alice"}]
    mgr.set_presence(stub)

    assert await mgr.get_room_online_users(1) == stub.users


async def test_manager_online_users_local_fallback():
    from api.websocket.manager import ConnectionManager

    mgr = ConnectionManager()
    stub = _StubPresence()
    stub._enabled = False
    mgr.set_presence(stub)
    uid = uuid.uuid4()
    conn, _ = await _register(mgr, user_id=uid, username="alice")
    await mgr.subscribe_room(conn, 1)

    users = await mgr.get_room_online_users(1)
    assert {u["user_id"] for u in users} == {uid}
