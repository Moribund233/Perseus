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


# 延迟直方图桶上界（毫秒）：时序接口据此估算 p95，避免存储全量样本。
LATENCY_BUCKETS_MS: tuple = (10, 25, 50, 100, 200, 500, 1000, 2500, 5000)
_INF_LABEL = "inf"
_BUCKET_LABELS: tuple = tuple(str(b) for b in LATENCY_BUCKETS_MS) + (_INF_LABEL,)

# 请求分钟桶的字符串字段（get_stats 仅用前 4 个，其余供时序接口使用）。
_BUCKET_SUFFIXES: tuple = ("count", "ok", "fail", "lat", "s2xx", "s3xx", "s4xx", "s5xx")


def _history_minutes() -> int:
    """指标历史保留分钟数（配置不可用时回退 1440）"""
    try:
        from core.config import get_config

        return int(getattr(get_config().metrics, "history_minutes", 1440) or 1440)
    except Exception:  # noqa: BLE001 — 配置未就绪时用默认值
        return 1440


def _bucket_label(latency_ms: float) -> str:
    """返回命中的直方图桶标签（首个 >= 延迟的上界，超出则 inf）"""
    for bound in LATENCY_BUCKETS_MS:
        if latency_ms <= bound:
            return str(bound)
    return _INF_LABEL


def _status_class_field(status_code: int) -> Optional[str]:
    """2xx/3xx/4xx/5xx → s2xx/...；其他状态码返回 None"""
    cls = int(status_code) // 100
    return f"s{cls}xx" if cls in (2, 3, 4, 5) else None


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def percentile_from_hist(hist: Dict[str, int], q: float = 0.95) -> float:
    """由直方图估算分位数（毫秒）；返回命中桶上界（inf 桶回退到上一上界）"""
    total = sum(hist.values())
    if total <= 0:
        return 0.0
    target = q * total
    cum = 0
    prev_bound = 0.0
    for label in _BUCKET_LABELS:
        cum += hist.get(label, 0)
        if cum >= target:
            if label == _INF_LABEL:
                return float(max(prev_bound, LATENCY_BUCKETS_MS[-1]))
            return float(label)
        if label != _INF_LABEL:
            prev_bound = float(label)
    return float(LATENCY_BUCKETS_MS[-1])


def merge_hist(target: Dict[str, int], source: Dict[str, int]) -> None:
    """把 ``source`` 直方图累加进 ``target``（原地）"""
    for label, count in source.items():
        target[label] = target.get(label, 0) + count


def _fresh_bucket(minute: int) -> _MinuteBucket:
    return {
        "minute": minute,
        "count": 0,
        "ok": 0,
        "fail": 0,
        "lat_sum": 0.0,
        "s2xx": 0,
        "s3xx": 0,
        "s4xx": 0,
        "s5xx": 0,
        "hist": {},
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
        self._minutes: Deque[_MinuteBucket] = deque(
            maxlen=max(window_minutes, _history_minutes())
        )
        self._current: _MinuteBucket = _fresh_bucket(_redis_minute())

    async def _backend(self) -> Optional[Any]:
        """解析 Redis 后端（惰性、失败后固定回退内存）"""
        if not self._redis_probed:
            self._redis_probed = True
            self._redis = await get_redis()
        return self._redis

    async def record_request(
        self,
        response_time_ms: float,
        success: bool,
        status_code: Optional[int] = None,
    ):
        """记录一个请求（``status_code`` 可选，用于 2xx/3xx/4xx/5xx 分布）"""
        backend = await self._backend()
        async with self._lock:
            if backend is not None:
                await self._record_redis(backend, response_time_ms, success, status_code)
            else:
                self._record_memory(response_time_ms, success, status_code)

    async def _record_redis(
        self,
        backend: Any,
        response_time_ms: float,
        success: bool,
        status_code: Optional[int] = None,
    ) -> None:
        minute = _redis_minute()
        pipe = backend.pipeline()
        pipe.incr(_key("total"))
        pipe.incr(_key("m", str(minute), "count"))
        pipe.incr(_key("m", str(minute), "ok") if success else _key("m", str(minute), "fail"))
        pipe.incrbyfloat(_key("m", str(minute), "lat"), response_time_ms)

        cls_field = _status_class_field(status_code) if status_code is not None else None
        if cls_field:
            pipe.incr(_key("m", str(minute), cls_field))

        hist_key = _key("m", str(minute), "hist")
        pipe.hincrby(hist_key, _bucket_label(response_time_ms), 1)

        ttl = max(self.window_minutes * 120 + 60, _history_minutes() * 60 + 60)
        for suffix in _BUCKET_SUFFIXES:
            pipe.expire(_key("m", str(minute), suffix), ttl)
        pipe.expire(hist_key, ttl)
        await pipe.execute()

    def _record_memory(
        self,
        response_time_ms: float,
        success: bool,
        status_code: Optional[int] = None,
    ) -> None:
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
        if status_code is not None:
            field = _status_class_field(status_code)
            if field:
                current[field] = current.get(field, 0) + 1
        label = _bucket_label(response_time_ms)
        current["hist"][label] = current["hist"].get(label, 0) + 1
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
        # _minutes 的 maxlen 已扩大到历史保留量，实时统计只取最近 window 分钟
        buckets = list(self._minutes)[-self.window_minutes:]
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

    # ---------------- 时序历史（admin 概览趋势图） ----------------

    async def get_history(self, minutes: int) -> Dict[int, _MinuteBucket]:
        """
        读取最近 ``minutes`` 分钟的每分钟请求桶（含状态分布与延迟直方图）。

        不含当前未走完的分钟，与 ``get_stats`` 口径一致；缺失分钟不补零，
        由调用方按时间轴对齐。
        """
        backend = await self._backend()
        if backend is not None:
            return await self._history_redis(backend, minutes)
        return self._history_memory(minutes)

    def _history_memory(self, minutes: int) -> Dict[int, _MinuteBucket]:
        lo = _redis_minute() - minutes + 1
        return {b["minute"]: b for b in self._minutes if b["minute"] >= lo}

    async def _history_redis(self, backend: Any, minutes: int) -> Dict[int, _MinuteBucket]:
        now_min = _redis_minute()
        mins = list(range(now_min - minutes + 1, now_min))  # 排除当前未走完分钟
        if not mins:
            return {}

        pipe = backend.pipeline()
        for m in mins:
            pipe.mget(*[_key("m", str(m), suffix) for suffix in _BUCKET_SUFFIXES])
            pipe.hgetall(_key("m", str(m), "hist"))
        raw = await pipe.execute()

        out: Dict[int, _MinuteBucket] = {}
        for idx, m in enumerate(mins):
            vals = raw[idx * 2] or []
            hist = raw[idx * 2 + 1] or {}

            def _get(i: int):
                return vals[i] if len(vals) > i else None

            bucket = _fresh_bucket(m)
            bucket.update(
                count=_as_int(_get(0)),
                ok=_as_int(_get(1)),
                fail=_as_int(_get(2)),
                lat_sum=_as_float(_get(3)),
                s2xx=_as_int(_get(4)),
                s3xx=_as_int(_get(5)),
                s4xx=_as_int(_get(6)),
                s5xx=_as_int(_get(7)),
            )
            bucket["hist"] = {str(k): _as_int(v) for k, v in hist.items()}
            out[m] = bucket
        return out

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

            # 记录请求（2xx 和 3xx 视为成功；status_code 供状态分布使用）
            success = 200 <= response.status_code < 400
            await self.stats.record_request(response_time_ms, success, response.status_code)

            return response
        except Exception as e:
            # 记录失败的请求
            response_time_ms = (time.time() - start_time) * 1000
            await self.stats.record_request(response_time_ms, False, 500)
            raise