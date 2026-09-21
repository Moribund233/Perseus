"""撤销黑名单读缓存（services/revocation_cache）+ token/invite 接线（规划 R5-1）"""
from unittest.mock import AsyncMock

import pytest

from services import revocation_cache


class _FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True


@pytest.fixture
def no_redis(monkeypatch):
    async def _none():
        return None

    monkeypatch.setattr(revocation_cache, "get_redis", _none)


@pytest.fixture
def fake_redis(monkeypatch):
    fake = _FakeRedis()

    async def _fake():
        return fake

    monkeypatch.setattr(revocation_cache, "get_redis", _fake)
    return fake


async def test_get_returns_none_without_redis(no_redis):
    assert await revocation_cache.get("token", "abc") is None


async def test_get_none_for_empty_jti(fake_redis):
    assert await revocation_cache.get("token", None) is None


async def test_positive_then_get_true(fake_redis):
    await revocation_cache.set("token", "j1", True)
    assert await revocation_cache.get("token", "j1") is True


async def test_negative_then_get_false(fake_redis):
    await revocation_cache.set("token", "j1", False)
    assert await revocation_cache.get("token", "j1") is False


async def test_negative_nx_does_not_override_positive(fake_redis):
    await revocation_cache.set("token", "j1", True)
    # 并发 DB 查询回写负缓存时不得覆盖已撤销的正键（避免复活）
    await revocation_cache.set("token", "j1", False)
    assert await revocation_cache.get("token", "j1") is True


async def test_set_noop_without_redis(no_redis):
    await revocation_cache.set("token", "j1", True)  # 不抛错


# ---------------- token_service 接线 ----------------

async def test_token_revoked_false_caches_negative(monkeypatch, async_db):
    from services import token_service

    monkeypatch.setattr(revocation_cache, "get", AsyncMock(return_value=None))
    set_mock = AsyncMock()
    monkeypatch.setattr(revocation_cache, "set", set_mock)

    assert await token_service.is_token_revoked(async_db, "no-such-jti") is False
    set_mock.assert_awaited_once_with("token", "no-such-jti", False)


async def test_token_revoked_true_from_db_caches_positive(monkeypatch, async_db):
    from models.revoked_token import RevokedToken
    from services import token_service

    async_db.add(RevokedToken(jti="revoked-jti", token_type="access"))
    await async_db.commit()

    monkeypatch.setattr(revocation_cache, "get", AsyncMock(return_value=None))
    set_mock = AsyncMock()
    monkeypatch.setattr(revocation_cache, "set", set_mock)

    assert await token_service.is_token_revoked(async_db, "revoked-jti") is True
    set_mock.assert_awaited_once_with("token", "revoked-jti", True)


async def test_token_revoked_cache_hit_skips_db(monkeypatch, async_db):
    from services import token_service

    monkeypatch.setattr(revocation_cache, "get", AsyncMock(return_value=True))
    set_mock = AsyncMock()
    monkeypatch.setattr(revocation_cache, "set", set_mock)

    assert await token_service.is_token_revoked(async_db, "cached-jti") is True
    set_mock.assert_not_awaited()


# ---------------- collab invite 接线 ----------------

async def test_invite_revoked_false_caches_negative(monkeypatch, async_db):
    from services import collab_invite_service as svc

    monkeypatch.setattr(revocation_cache, "get", AsyncMock(return_value=None))
    set_mock = AsyncMock()
    monkeypatch.setattr(revocation_cache, "set", set_mock)

    assert await svc.is_invite_token_revoked(async_db, "inv-jti") is False
    set_mock.assert_awaited_once_with("collab_invite", "inv-jti", False)
