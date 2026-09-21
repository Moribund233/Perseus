"""OAuthStateStore：Redis 共享 + 内存回退 + 显式告警（规划 R3 / D2）"""
import time

import pytest

from services import oauth_service
from services.oauth_service import OAuthStateStore, STATE_TTL


class _FakeRedis:
    def __init__(self):
        self.data = {}
        self.setex_calls = 0
        self.getdel_calls = 0

    async def setex(self, key, ttl, value):
        self.setex_calls += 1
        self.data[key] = value

    async def getdel(self, key):
        self.getdel_calls += 1
        return self.data.pop(key, None)


@pytest.fixture
def no_redis(monkeypatch):
    async def _none():
        return None

    monkeypatch.setattr(oauth_service, "get_redis", _none)


async def test_memory_fallback_single_use(no_redis):
    store = OAuthStateStore()
    state = await store.generate("github")
    assert await store.consume(state, "github") is True
    assert await store.consume(state, "github") is False  # 一次性


async def test_memory_fallback_wrong_provider(no_redis):
    store = OAuthStateStore()
    state = await store.generate("github")
    assert await store.consume(state, "gitlab") is False


async def test_memory_fallback_expired(no_redis):
    store = OAuthStateStore()
    state = await store.generate("github")
    store._states[state]["created_at"] = time.time() - STATE_TTL - 1
    assert await store.consume(state, "github") is False


async def test_redis_shared_across_instances(monkeypatch):
    fake = _FakeRedis()

    async def _fake_get_redis():
        return fake

    monkeypatch.setattr(oauth_service, "get_redis", _fake_get_redis)

    issuer = OAuthStateStore()
    state = await issuer.generate("github")
    assert fake.setex_calls == 1

    # 另一实例（模拟另一个 worker）经共享 Redis 校验通过
    verifier = OAuthStateStore()
    assert await verifier.consume(state, "github") is True
    assert await verifier.consume(state, "github") is False


async def test_redis_write_failure_falls_back_to_memory(monkeypatch):
    class _BrokenRedis(_FakeRedis):
        async def setex(self, key, ttl, value):
            raise ConnectionError("boom")

    fake = _BrokenRedis()

    async def _fake_get_redis():
        return fake

    monkeypatch.setattr(oauth_service, "get_redis", _fake_get_redis)

    store = OAuthStateStore()
    state = await store.generate("github")
    assert store._warned is True
    assert await store.consume(state, "github") is True
