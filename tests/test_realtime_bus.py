"""
跨 worker 实时广播总线（utils/realtime_bus）测试。

覆盖：Hybrid 去重（跳过 origin 回声）、scope 路由、manager 本地直投 + 发布、
Redis 不可用时退化为进程内、订阅循环启停。
"""
import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.websocket.manager import ConnectionManager
from utils import redis_client, realtime_bus
from utils.realtime_bus import RealtimeBus, WORKER_ID


@pytest.fixture(autouse=True)
def _reset_manager():
    ConnectionManager.reset_instance()
    yield
    ConnectionManager.reset_instance()


def _mock_ws():
    ws = MagicMock()
    ws.accept = AsyncMock(return_value=None)
    ws.send_text = AsyncMock(return_value=True)
    ws.close = AsyncMock(return_value=None)
    return ws


async def _register(mgr, user_id=None, username=None):
    ws = _mock_ws()
    conn = await mgr.connect(ws)
    if user_id is not None:
        await mgr.bind_user(conn, user_id, username or "u")
    return conn, ws


class _FakeBus:
    def __init__(self):
        self.calls = []

    async def publish(self, scope, target_id, message, exclude_user_id=None):
        self.calls.append((scope, target_id, message, exclude_user_id))


# ---------------- manager 集成 ----------------

async def test_manager_publishes_after_local_delivery():
    mgr = ConnectionManager()
    fake = _FakeBus()
    mgr.set_bus(fake)
    conn, ws = await _register(mgr, user_id=uuid.uuid4())
    await mgr.subscribe_room(conn, 1)

    count = await mgr.send_to_room(1, {"type": "x"})

    assert count == 1
    assert ws.send_text.await_count == 1
    assert fake.calls and fake.calls[0][0] == "room"
    assert fake.calls[0][1] == 1


async def test_deliver_local_does_not_publish():
    mgr = ConnectionManager()
    fake = _FakeBus()
    mgr.set_bus(fake)
    conn, ws = await _register(mgr, user_id=uuid.uuid4())
    await mgr.subscribe_room(conn, 1)

    count = await mgr._deliver_room(1, {"type": "x"})

    assert count == 1
    assert fake.calls == []


async def test_send_to_user_publishes_scope():
    mgr = ConnectionManager()
    fake = _FakeBus()
    mgr.set_bus(fake)
    uid = uuid.uuid4()
    await _register(mgr, user_id=uid)

    await mgr.send_to_user(uid, {"type": "n"})

    assert fake.calls and fake.calls[0][0] == "user"


# ---------------- bus 路由与去重 ----------------

async def test_dispatch_skips_own_origin():
    mgr = ConnectionManager()
    conn, ws = await _register(mgr, user_id=uuid.uuid4())
    room_id = uuid.uuid4()
    await mgr.subscribe_room(conn, room_id)
    bus = RealtimeBus(manager=mgr)

    payload = json.dumps({
        "origin": WORKER_ID,
        "scope": "room",
        "target": str(room_id),
        "message": {"type": "x"},
    })
    await bus._dispatch_raw(payload)

    assert ws.send_text.await_count == 0  # 本进程回声被跳过


async def test_dispatch_delivers_for_other_origin():
    mgr = ConnectionManager()
    conn, ws = await _register(mgr, user_id=uuid.uuid4())
    room_id = uuid.uuid4()
    await mgr.subscribe_room(conn, room_id)
    bus = RealtimeBus(manager=mgr)

    payload = json.dumps({
        "origin": "other-worker",
        "scope": "room",
        "target": str(room_id),
        "message": {"type": "x"},
    })
    await bus._dispatch_raw(payload)

    assert ws.send_text.await_count == 1
    sent = json.loads(ws.send_text.await_args[0][0])
    assert sent == {"type": "x"}


async def test_dispatch_bad_payload_ignored():
    mgr = ConnectionManager()
    bus = RealtimeBus(manager=mgr)
    await bus._dispatch_raw("not-json")
    await bus._dispatch_raw(json.dumps(["not", "a", "dict"]))


async def test_deliver_unknown_scope_returns_zero():
    mgr = ConnectionManager()
    bus = RealtimeBus(manager=mgr)
    assert await bus.deliver("nope", 1, {"type": "x"}) == 0


async def test_publish_noop_without_client():
    bus = RealtimeBus()
    await bus.publish("room", 1, {"type": "x"})  # 不抛错


# ---------------- 启停 / 退化 ----------------

class _FakePubSub:
    def __init__(self):
        self.patterns = []
        self.closed = False

    async def psubscribe(self, pattern):
        self.patterns.append(pattern)

    async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
        await asyncio.sleep(0.01)
        return None

    async def punsubscribe(self):
        pass

    async def close(self):
        self.closed = True


class _FakePubSubClient:
    def __init__(self):
        self.sub = _FakePubSub()

    def pubsub(self):
        return self.sub

    async def aclose(self):
        pass


class _FakeCommandClient:
    def __init__(self):
        self.published = []

    async def publish(self, channel, data):
        self.published.append((channel, data))


async def test_start_without_redis_returns_false(monkeypatch):
    async def _none():
        return None

    monkeypatch.setattr(redis_client, "get_redis", _none)
    bus = RealtimeBus()
    assert await bus.start() is False
    assert bus.is_running is False


async def test_start_and_stop_with_fake_redis(monkeypatch):
    cmd = _FakeCommandClient()
    pub = _FakePubSubClient()

    async def _cmd():
        return cmd

    async def _pub():
        return pub

    monkeypatch.setattr(redis_client, "get_redis", _cmd)
    monkeypatch.setattr(redis_client, "create_pubsub_client", _pub)

    bus = RealtimeBus()
    assert await bus.start() is True
    assert bus.is_running is True
    assert pub.sub.patterns == [redis_client.ws_pattern()]

    await bus.stop()
    assert bus.is_running is False
    assert pub.sub.closed is True


async def test_publish_sends_to_channel(monkeypatch):
    cmd = _FakeCommandClient()
    pub = _FakePubSubClient()

    async def _cmd():
        return cmd

    async def _pub():
        return pub

    monkeypatch.setattr(redis_client, "get_redis", _cmd)
    monkeypatch.setattr(redis_client, "create_pubsub_client", _pub)

    bus = RealtimeBus()
    await bus.start()
    await bus.publish("room", "r1", {"type": "x"}, exclude_user_id=uuid.UUID(int=0))

    assert len(cmd.published) == 1
    channel, raw = cmd.published[0]
    assert channel.endswith(":room:r1")
    payload = json.loads(raw)
    assert payload["origin"] == WORKER_ID
    assert payload["scope"] == "room"
    assert payload["message"] == {"type": "x"}

    await bus.stop()
