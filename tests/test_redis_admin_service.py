"""Redis 运维状态服务（services/redis_admin_service）测试"""
import pytest

from services import redis_admin_service as svc
from services.redis_admin_service import RedisAdminService, _redact_url


class _FakeRedis:
    async def ping(self):
        return True

    async def info(self, section=None):
        if section == "memory":
            return {"maxmemory": 512 * 1024 * 1024, "maxmemory_policy": "volatile-lru"}
        return {
            "redis_version": "7.4.1",
            "redis_mode": "standalone",
            "os": "Linux",
            "uptime_in_seconds": "3600",
            "used_memory": "1000000",
            "used_memory_peak": "2000000",
            "used_memory_rss": "1200000",
            "maxmemory": "536870912",
            "maxmemory_policy": "volatile-lru",
            "mem_fragmentation_ratio": "1.18",
            "connected_clients": "7",
            "blocked_clients": "0",
            "instantaneous_ops_per_sec": "126.4",
            "keyspace_hits": "900",
            "keyspace_misses": "100",
            "expired_keys": "5",
            "evicted_keys": "2",
        }

    async def pubsub_numpat(self):
        return 4

    async def pubsub_channels(self):
        return ["perseus:collab:doc:x"]

    async def scan(self, cursor=0, match=None, count=500):
        if match and ":oauth:" in match:
            return (0, ["perseus:oauth:state:a", "perseus:oauth:state:b"])
        return (0, [])


class _StubRegistry:
    def __init__(self, items):
        self._items = items

    async def list_workers(self):
        return self._items


class _StubBus:
    def stats(self):
        return {
            "running": True, "published": 5, "received": 3,
            "publish_failures": 1, "dispatch_failures": 0, "last_error": "boom",
        }


@pytest.fixture
def wired(monkeypatch):
    fake = _FakeRedis()

    async def _get():
        return fake

    monkeypatch.setattr(svc.redis_client, "get_redis", _get)
    monkeypatch.setattr(svc.redis_client, "is_configured", lambda: True)
    monkeypatch.setattr(svc, "realtime_bus", _StubBus())
    monkeypatch.setattr(svc, "worker_registry", _StubRegistry([
        {"worker_id": "w1", "alive": True},
        {"worker_id": "w2", "alive": True},
    ]))
    # 清键空间缓存，避免跨用例污染
    svc._keyspace_cache["at"] = 0.0
    svc._keyspace_cache["items"] = []
    return fake


async def test_status_full(wired):
    status = await RedisAdminService().get_status()

    assert status["configured"] is True
    assert status["reachable"] is True
    assert status["latency_ms"] is not None
    assert status["server"]["version"] == "7.4.1"
    assert status["memory"]["maxmemory"] == 536870912
    assert status["clients"]["connected"] == 7
    assert status["stats"]["hit_rate"] == 0.9
    assert status["stats"]["evicted_keys"] == 2

    assert status["workers"]["alive"] == 2
    assert len(status["workers"]["items"]) == 2

    assert status["pubsub"]["pattern_subscriptions"] == 4
    assert status["pubsub"]["mismatch"] is False  # 4 >= 2

    assert status["degradation"]["bus_published"] == 5
    assert status["degradation"]["bus_last_error"] == "boom"

    oauth = [k for k in status["keyspace"] if k["domain"] == "oauth"][0]
    assert oauth["keys"] == 2


async def test_status_mismatch_when_subscriptions_missing(monkeypatch, wired):
    monkeypatch.setattr(svc, "worker_registry", _StubRegistry(
        [{"worker_id": f"w{i}", "alive": True} for i in range(5)]
    ))
    status = await RedisAdminService().get_status()
    # 5 个存活 worker 但只有 4 个模式订阅 → mismatch
    assert status["pubsub"]["mismatch"] is True


async def test_status_unreachable(monkeypatch):
    async def _none():
        return None

    monkeypatch.setattr(svc.redis_client, "get_redis", _none)
    monkeypatch.setattr(svc.redis_client, "is_configured", lambda: False)
    monkeypatch.setattr(svc, "realtime_bus", _StubBus())
    monkeypatch.setattr(svc, "worker_registry", _StubRegistry([]))

    status = await RedisAdminService().get_status()
    assert status["configured"] is False
    assert status["reachable"] is False
    assert status["latency_ms"] is None
    assert status["workers"]["items"] == []


async def test_get_config_runtime(wired):
    cfg = await RedisAdminService().get_config()
    assert cfg["editable"] is False
    assert cfg["runtime"]["maxmemory"] == 512 * 1024 * 1024
    assert cfg["runtime"]["maxmemory_policy"] == "volatile-lru"
    assert "namespace" in cfg["settings"]


def test_redact_url_hides_password():
    redacted = _redact_url("redis://:supersecret@redis:6379/0")
    assert "supersecret" not in redacted
    assert "***" in redacted


def test_redact_url_plain():
    assert _redact_url("redis://redis:6379/0") == "redis://redis:6379/0"
