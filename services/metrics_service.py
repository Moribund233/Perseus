"""
admin 概览时序聚合服务

把请求分钟桶（middleware/request_stats）与进程分钟桶（services/process_metrics）
合并、按范围降采样为前端趋势图所需的点序列。

Redis 为权威来源（跨 worker 聚合）；不可用时退回各模块的进程内回退实现，
口径一致，仅缺少跨 worker 聚合。返回结构对应前端
``GET /api/app/metrics/timeseries?range=…``。
"""
import math
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from middleware.request_stats import (
    get_request_stats,
    merge_hist,
    percentile_from_hist,
)
from services.process_metrics import get_process_metrics
from utils.redis_client import get_redis

# 支持的取值范围 → 分钟数
RANGES: Dict[str, int] = {"5m": 5, "30m": 30, "1h": 60, "6h": 360, "24h": 1440}

DEFAULT_RANGE = "1h"


def _now_minute() -> int:
    return int(time.time()) // 60


def _max_points() -> int:
    """单次返回的最大点数（配置不可用时回退 120）"""
    try:
        from core.config import get_config

        return int(getattr(get_config().metrics, "max_points", 120) or 120)
    except Exception:  # noqa: BLE001
        return 120


def _aggregate_bucket(
    req: Dict[int, Dict[str, Any]],
    proc: Dict[int, Dict[str, float]],
    start: int,
    end: int,
) -> Dict[str, Any]:
    """聚合 ``[start, end)`` 分钟区间为一个时序点"""
    width = max(1, end - start)
    count = ok = fail = 0
    lat_sum = 0.0
    status = {"s2xx": 0, "s3xx": 0, "s4xx": 0, "s5xx": 0}
    hist: Dict[str, int] = {}

    for minute in range(start, end):
        bucket = req.get(minute)
        if not bucket:
            continue
        count += bucket.get("count", 0)
        ok += bucket.get("ok", 0)
        fail += bucket.get("fail", 0)
        lat_sum += bucket.get("lat_sum", 0.0)
        for key in status:
            status[key] += bucket.get(key, 0)
        merge_hist(hist, bucket.get("hist") or {})

    mems = [proc[m]["mem_mb"] for m in range(start, end) if m in proc]
    cpus = [proc[m]["cpu_pct"] for m in range(start, end) if m in proc]

    return {
        "t": end * 60 * 1000,  # 桶结束时刻（epoch ms）
        "rpm": round(count / width, 2),
        "err_rate": round(fail / count * 100, 2) if count else 0.0,
        "avg_ms": round(lat_sum / count, 2) if count else 0.0,
        "p95_ms": round(percentile_from_hist(hist), 2) if count else 0.0,
        "mem_mb": round(sum(mems) / len(mems), 2) if mems else None,
        "cpu_pct": round(sum(cpus) / len(cpus), 2) if cpus else None,
        **status,
    }


async def get_timeseries(range_key: str) -> Dict[str, Any]:
    """
    返回指定范围的时序点序列。

    Args:
        range_key: 取值范围（``5m`` / ``30m`` / ``1h`` / ``6h`` / ``24h``）

    Returns:
        dict: ``{range, step, generated_at, source, points}``；``step`` 为秒，
        ``points`` 已降采样至配置的 ``max_points`` 以内，且不含当前未走完的分钟。
    """
    minutes = RANGES.get(range_key, RANGES[DEFAULT_RANGE])
    step = max(1, math.ceil(minutes / max(1, _max_points())))
    now = _now_minute()
    lo = now - minutes

    req = await get_request_stats().get_history(minutes)
    proc = await get_process_metrics().get_samples(minutes)
    source = "redis" if await get_redis() is not None else "memory"

    points: List[Dict[str, Any]] = []
    start = lo
    while start < now:
        end = min(start + step, now)
        points.append(_aggregate_bucket(req, proc, start, end))
        start = end

    return {
        "range": range_key if range_key in RANGES else DEFAULT_RANGE,
        "step": step * 60,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "points": points,
    }
