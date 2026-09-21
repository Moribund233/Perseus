"""Worker 心跳注册表（services/worker_registry）测试"""
import asyncio
import fnmatch
import time

import pytest

from services import worker_registry as wr
from services.worker_registry import WorkerRegistry, _worker_key
from utils.realtime_bus import WORKER_ID


class _FakeRedis:
    def __init__(self):
        self.hashes = {}
        self.expires = {}

    async def hset(self, key, mapping=None):
        self.hashes.setdefault(key, {}).update(mapping or {})
        return len(mapping or {})

    async def expire(self, key, ttl):
        self.expires[key] = ttl
        return True

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    async def scan(self, cursor=0, match=None, count=200):
        keys = [k for k in self.hashes if fnmatch.fnmatch(k, match or "*")]
        return (0, keys)


class _StubBus:
    def stats(self):
        return {
            "running": True,
            "published": 12,
            "received": 7,
            "publish_failures": 1,
            "dispatch_failures": 0,
            "last_error": None,
        }


class _StubManager:
    def __init__(self):
        self.active_connections = {"c1": object(), "c2": object()}
        self._room_index = {1: set(), 2: set()}
        self._lock = asyncio.Lock()


@pytest.fixture
def no_redis(monkeypatch):
    async def _none():
        return None

    monkeypatch.setattr(wr, "get_redis", _none)


@pytest.fixture
def fake_redis(monkeypatch):
    fake = _FakeRedis()

    async def _fake():
        return fake

    monkeypatch.setattr(wr, "get_redis", _fake)
    return fake


async def test_heartbeat_noop_without_redis(no_redis):
    reg = WorkerRegistry()
    await reg.heartbeat(_StubManager(), _StubBus())  # 不抛错
    assert await reg.list_workers() == []


async def test_heartbeat_writes_fields(fake_redis):
    reg = WorkerRegistry()
    await reg.heartbeat(_StubManager(), _StubBus())

    key = _worker_key(WORKER_ID)
    assert key in fake_redis.hashes
    fields = fake_redis.hashes[key]
    assert fields["worker_id"] == WORKER_ID
    assert fields["bus_running"] == "1"
    assert fields["bus_published"] == "12"
    assert fields["bus_publish_failures"] == "1"
    assert fields["local_connections"] == "2"
    assert fields["presence_rooms"] == "2"
    assert fake_redis.expires[key] == reg.ttl


async def test_list_workers_alive_flag(fake_redis):
    reg = WorkerRegistry(ttl_seconds=45)
    now = int(time.time())
    fake_redis.hashes[_worker_key("w-alive")] = {
        "worker_id": "w-alive", "last_seen": str(now), "bus_running": "1",
        "local_connections": "3",
    }
    fake_redis.hashes[_worker_key("w-stale")] = {
        "worker_id": "w-stale", "last_seen": str(now - 999), "bus_running": "0",
    }

    items = {w["worker_id"]: w for w in await reg.list_workers()}
    assert items["w-alive"]["alive"] is True
    assert items["w-alive"]["bus_running"] is True
    assert items["w-alive"]["local_connections"] == 3
    assert items["w-stale"]["alive"] is False
    assert items["w-stale"]["bus_running"] is False


async def test_list_workers_no_redis(no_redis):
    assert await WorkerRegistry().list_workers() == []
