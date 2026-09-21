"""
请求统计类（异步安全，支持跨 worker 聚合）

Redis 可用时经 Redis 聚合多 worker 的请求指标，使 admin 概览的
请求速率与成功/失败数在任意副本间保持一致；Redis 未配置或不可达时
回退进程内实现（语义与 Redis 口径一致）。

指标口径（``window_minutes`` 分钟滑动窗）：
- ``total``: 累计总请求数（进程生命周期，跨 worker 求和）
- ``success`` / ``failed``: 最近 ``window_minutes`` 个「完整分钟」内的成功/失败数
- ``avg_response_time_ms``: 同一完整分钟窗口内的平均响应时间
- ``requests_per_minute``: 完整分钟窗口的平均每分钟请求速率
- ``window_minutes``: 本窗口长度（分钟）

当前未走完的分钟不参与任何统计，避免“从 1 爬升到 59 再归零”的锯齿。
"""
import asyncio
import time
from collections import deque
from typing import Any, Deque, Dict, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from utils.redis_client import get_redis, key as redis_key

# 内存回退：单个条目
_MinuteBucket = Dict[str, Any]


def _key(*parts: str) -> str:
    """统一命名空间：``perseus:req:*``"""
    return redis_key("req", *parts)


def _redis_minute() -> int:
    """当前分钟桶（Unix 秒 // 60）"""
    return int(time.time()) // 60


def _fresh_bucket(minute: int) -> _MinuteBucket:
    return {
        "minute": minute,
        "count": 0,
        "ok": 0,
        "fail": 0,
        "lat_sum": 0.0,
    }


class RequestStats:
    """请求统计类（异步安全）"""

    def __init__(self, window_minutes: int = 5):
        self.window_minutes = window_minutes
        self._lock = asyncio.Lock()
        self._redis = None  # None|Redis|未探测哨兵
        self._redis_probed = False
        # 内存回退状态
        self._total = 0
        self._ok = 0
        self._fail = 0
        self._minutes: Deque[_MinuteBucket] = deque(maxlen=window_minutes)
        self._current: _MinuteBucket = _fresh_bucket(_redis_minute())

    async def _backend(self) -> Optional[Any]:
        """解析 Redis 后端（惰性、失败后固定回退内存）"""
        if not self._redis_probed:
            self._redis_probed = True
            self._redis = await get_redis()
        return self._redis

    async def record_request(self, response_time_ms: float, success: bool):
        """记录一个请求"""
        backend = await self._backend()
        async with self._lock:
            if backend is not None:
                await self._record_redis(backend, response_time_ms, success)
            else:
                self._record_memory(response_time_ms, success)

    async def _record_redis(
        self, backend: Any, response_time_ms: float, success: bool
    ) -> None:
        minute = _redis_minute()
        pipe = backend.pipeline()
        pipe.incr(_key("total"))
        pipe.incr(_key("m", str(minute), "count"))
        pipe.incr(_key("m", str(minute), "ok") if success else _key("m", str(minute), "fail"))
        pipe.incrbyfloat(_key("m", str(minute), "lat"), response_time_ms)
        ttl = self.window_minutes * 120 + 60
        for suffix in ("count", "ok", "fail", "lat"):
            pipe.expire(_key("m", str(minute), suffix), ttl)
        await pipe.execute()

    def _record_memory(self, response_time_ms: float, success: bool) -> None:
        now = _redis_minute()
        if now > self._current["minute"]:
            self._minutes.append(self._current)
            self._current = _fresh_bucket(now)

        current = self._current
        current["count"] += 1
        current["lat_sum"] += response_time_ms
        if success:
            self._ok += 1
            current["ok"] += 1
        else:
            self._fail += 1
            current["fail"] += 1
        self._total += 1

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        backend = await self._backend()
        async with self._lock:
            if backend is not None:
                return await self._stats_redis(backend)
            return self._stats_memory()

    async def _stats_redis(self, backend: Any) -> Dict[str, Any]:
        total = int((await backend.get(_key("total"))) or 0)

        now_min = _redis_minute()
        complete = [now_min - i for i in range(1, self.window_minutes + 1)]
        parts = await backend.mget(
            *[
                _key("m", str(m), suffix)
                for m in complete
                for suffix in ("count", "ok", "fail", "lat")
            ]
        )

        counts = [int(parts[i] or 0) for i in range(0, len(parts), 4)]
        oks = [int(parts[i] or 0) for i in range(1, len(parts), 4)]
        fails = [int(parts[i] or 0) for i in range(2, len(parts), 4)]
        lats = [float(parts[i] or 0.0) for i in range(3, len(parts), 4)]

        count_sum = sum(counts)
        count_minutes = max(1, sum(1 for c in counts if c > 0))
        rpm = round(count_sum / count_minutes, 2) if count_sum else 0.0

        lat_sum = sum(lats)
        lat_n = count_sum
        avg = round(lat_sum / lat_n, 2) if lat_n else 0.0

        return {
            "total": total,
            "success": sum(oks),
            "failed": sum(fails),
            "avg_response_time_ms": avg,
            "requests_per_minute": rpm,
            "window_minutes": self.window_minutes,
        }

    def _stats_memory(self) -> Dict[str, Any]:
        buckets = list(self._minutes)
        count = sum(b["count"] for b in buckets)
        success = sum(b["ok"] for b in buckets)
        failed = sum(b["fail"] for b in buckets)
        lat_sum = sum(b["lat_sum"] for b in buckets)

        n = max(1, len(buckets))
        rpm = round(count / n, 2) if count else 0.0
        avg = round(lat_sum / count, 2) if count else 0.0

        return {
            "total": self._total,
            "success": success,
            "failed": failed,
            "avg_response_time_ms": avg,
            "requests_per_minute": rpm,
            "window_minutes": self.window_minutes,
        }

    async def reset(self, backend: Optional[Any] = None):
        """重置统计（Redis 键一并清理）"""
        async with self._lock:
            self._total = 0
            self._ok = 0
            self._fail = 0
            self._minutes.clear()
            self._current = _fresh_bucket(_redis_minute())
            client = backend if backend is not None else await self._backend()
            if client is not None:
                try:
                    await client.delete(_key("total"))
                except Exception:  # noqa: BLE001 — 清理为尽力而为
                    pass


# 全局统计实例
_request_stats: Optional[RequestStats] = None


def get_request_stats() -> RequestStats:
    """获取全局请求统计实例"""
    global _request_stats
    if _request_stats is None:
        _request_stats = RequestStats()
    return _request_stats


class RequestStatsMiddleware(BaseHTTPMiddleware):
    """
    请求统计中间件

    统计所有 HTTP 请求的性能指标
    """

    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
        self.stats = get_request_stats()

    def _should_record(self, path: str) -> bool:
        """检查是否应该记录该路径"""
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        return True

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        if not self._should_record(request.url.path):
            return await call_next(request)

        start_time = time.time()

        try:
            response = await call_next(request)

            # 计算响应时间（毫秒）
            response_time_ms = (time.time() - start_time) * 1000

            # 记录请求（2xx 和 3xx 视为成功）
            success = 200 <= response.status_code < 400
            await self.stats.record_request(response_time_ms, success)

            return response
        except Exception as e:
            # 记录失败的请求
            response_time_ms = (time.time() - start_time) * 1000
            await self.stats.record_request(response_time_ms, False)
            raise