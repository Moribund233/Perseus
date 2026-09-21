"""全局并发限制器（middleware/concurrency GlobalConcurrencyLimiter）测试（规划 R5-3）"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import Response

from middleware import concurrency as conc_mod
from middleware.concurrency import ConcurrencyMiddleware, GlobalConcurrencyLimiter


class _FakeRedis:
    def __init__(self, maxv):
        self.count = 0
        self.maxv = maxv

    async def eval(self, script, numkeys, key, *args):
        if "INCR" in script:
            self.count += 1
            if self.count > self.maxv:
                self.count -= 1
                return 0
            return self.count
        self.count -= 1
        if self.count < 0:
            self.count = 0
        return self.count


def _patch_redis(monkeypatch, client):
    async def _get():
        return client

    monkeypatch.setattr(conc_mod, "get_redis", _get)


async def test_limiter_allows_up_to_max_then_denies(monkeypatch):
    _patch_redis(monkeypatch, _FakeRedis(maxv=2))
    lim = GlobalConcurrencyLimiter(2)

    assert await lim.acquire() is True
    assert await lim.acquire() is True
    assert await lim.acquire() is False  # 超限

    await lim.release()
    assert await lim.acquire() is True


async def test_limiter_no_redis_allows(monkeypatch):
    async def _none():
        return None

    monkeypatch.setattr(conc_mod, "get_redis", _none)
    lim = GlobalConcurrencyLimiter(1)
    assert await lim.acquire() is True
    await lim.release()  # no-op


async def test_limiter_redis_error_allows(monkeypatch):
    class _Broken:
        async def eval(self, *a, **k):
            raise RuntimeError("boom")

    _patch_redis(monkeypatch, _Broken())
    lim = GlobalConcurrencyLimiter(1)
    assert await lim.acquire() is True  # 降级放行


class _StubGlobal:
    def __init__(self, allow):
        self.allow = allow
        self.max_concurrent = 5
        self.released = 0

    async def acquire(self):
        return self.allow

    async def release(self):
        self.released += 1


def _request():
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/x",
        "headers": [],
        "query_string": b"",
        "server": ("test", 80),
        "client": ("test", 1),
        "scheme": "http",
    })


async def test_middleware_503_when_global_denied():
    mw = ConcurrencyMiddleware(app=MagicMock(), max_concurrent=10, max_wait_time=1.0)
    stub = _StubGlobal(allow=False)
    mw.global_limiter = stub

    async def call_next(request):
        return Response("ok")

    resp = await mw.dispatch(_request(), call_next)
    assert resp.status_code == 503
    assert stub.released == 0
    # 本地许可已释放
    assert mw.limiter.available_slots == mw.limiter.max_concurrent


async def test_middleware_releases_global_on_success():
    mw = ConcurrencyMiddleware(app=MagicMock(), max_concurrent=10, max_wait_time=1.0)
    stub = _StubGlobal(allow=True)
    mw.global_limiter = stub

    async def call_next(request):
        return Response("ok")

    resp = await mw.dispatch(_request(), call_next)
    assert resp.status_code == 200
    assert stub.released == 1
    assert mw.limiter.available_slots == mw.limiter.max_concurrent


async def test_middleware_no_global_limiter_when_zero():
    mw = ConcurrencyMiddleware(app=MagicMock(), max_concurrent=10)
    assert mw.global_limiter is None
