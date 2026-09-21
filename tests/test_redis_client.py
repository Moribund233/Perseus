"""
Redis 客户端（utils/redis_client）硬化测试。

覆盖：未配置回退、惰性连接与缓存、失败后按冷却重试（不再永久冻结）、
强依赖 require_redis 显式失败、统一命名空间 key/ws_channel、pubsub 独立连接。
"""
from types import SimpleNamespace

import pytest

from utils import redis_client


@pytest.fixture(autouse=True)
async def _reset():
    await redis_client.reset_redis()
    yield
    await redis_client.reset_redis()


def _settings(namespace="perseus", pubsub_prefix="", cooldown=0.0):
    return SimpleNamespace(
        namespace=namespace,
        pubsub_prefix=pubsub_prefix,
        ws_prefix=(pubsub_prefix or f"{namespace}:ws").strip(":"),
        reconnect_cooldown=cooldown,
    )


class _FakeRedis:
    """可控的假客户端：ping 失败/成功由类属性切换"""

    fail = False

    def __init__(self):
        self.closed = False

    async def ping(self):
        if type(self).fail:
            raise ConnectionError("redis down")
        return True

    async def aclose(self):
        self.closed = True

    @classmethod
    def from_url(cls, url, *args, **kwargs):
        return cls()


async def test_disabled_when_no_url(monkeypatch):
    monkeypatch.setattr(redis_client, "_redis_url", lambda: "  ")
    assert redis_client.is_configured() is False
    assert await redis_client.get_redis() is None


async def test_lazy_connect_and_cache(monkeypatch):
    _FakeRedis.fail = False
    monkeypatch.setattr(redis_client, "_redis_url", lambda: "redis://x:6379/0")
    monkeypatch.setattr(redis_client, "_redis_settings", lambda: _settings())
    monkeypatch.setattr("redis.asyncio", _FakeRedis)

    first = await redis_client.get_redis()
    second = await redis_client.get_redis()
    assert first is not None and second is first
    assert redis_client.is_configured() is True
    assert await redis_client.require_redis() is first


async def test_reconnect_after_cooldown(monkeypatch):
    """失败后按冷却重试：冷却为 0 时下次调用即恢复"""
    _FakeRedis.fail = True
    monkeypatch.setattr(redis_client, "_redis_url", lambda: "redis://x:6379/0")
    monkeypatch.setattr(redis_client, "_redis_settings", lambda: _settings(cooldown=0.0))
    monkeypatch.setattr("redis.asyncio", _FakeRedis)

    assert await redis_client.get_redis() is None

    _FakeRedis.fail = False
    recovered = await redis_client.get_redis()
    assert recovered is not None


async def test_cooldown_blocks_retry(monkeypatch):
    """冷却期内不重连；冷却放开后恢复"""
    _FakeRedis.fail = True
    monkeypatch.setattr(redis_client, "_redis_url", lambda: "redis://x:6379/0")
    monkeypatch.setattr(redis_client, "_redis_settings", lambda: _settings(cooldown=999.0))
    monkeypatch.setattr("redis.asyncio", _FakeRedis)

    assert await redis_client.get_redis() is None

    _FakeRedis.fail = False
    assert await redis_client.get_redis() is None  # 仍在冷却期

    monkeypatch.setattr(redis_client, "_redis_settings", lambda: _settings(cooldown=0.0))
    assert await redis_client.get_redis() is not None


async def test_require_redis_raises_when_unavailable(monkeypatch):
    monkeypatch.setattr(redis_client, "_redis_url", lambda: "")
    with pytest.raises(redis_client.RedisUnavailableError):
        await redis_client.require_redis()


def test_key_namespace(monkeypatch):
    monkeypatch.setattr(redis_client, "_redis_settings", lambda: _settings(namespace="test"))
    assert redis_client.key("req", "total") == "test:req:total"


def test_ws_channel_and_pattern(monkeypatch):
    monkeypatch.setattr(redis_client, "_redis_settings", lambda: _settings(namespace="test"))
    assert redis_client.ws_channel("room", "abc") == "test:ws:room:abc"
    assert redis_client.ws_channel("broadcast") == "test:ws:broadcast"
    assert redis_client.ws_pattern() == "test:ws:*"


def test_ws_channel_custom_prefix(monkeypatch):
    monkeypatch.setattr(
        redis_client,
        "_redis_settings",
        lambda: _settings(namespace="test", pubsub_prefix="custom:bus"),
    )
    assert redis_client.ws_channel("user", "u1") == "custom:bus:user:u1"


async def test_create_pubsub_client_none_without_url(monkeypatch):
    monkeypatch.setattr(redis_client, "_redis_url", lambda: "")
    assert await redis_client.create_pubsub_client() is None


async def test_create_pubsub_client_ok(monkeypatch):
    _FakeRedis.fail = False
    monkeypatch.setattr(redis_client, "_redis_url", lambda: "redis://x:6379/0")
    monkeypatch.setattr("redis.asyncio", _FakeRedis)

    client = await redis_client.create_pubsub_client()
    assert isinstance(client, _FakeRedis)
    await client.aclose()


async def test_create_pubsub_client_failure_returns_none(monkeypatch):
    _FakeRedis.fail = True
    monkeypatch.setattr(redis_client, "_redis_url", lambda: "redis://x:6379/0")
    monkeypatch.setattr("redis.asyncio", _FakeRedis)
    assert await redis_client.create_pubsub_client() is None
