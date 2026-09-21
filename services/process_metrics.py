"""
进程指标采样器（内存 / CPU）

后台按固定间隔读取当前进程（psutil）的内存与 CPU，写入 Redis 分钟桶
``perseus:metrics:proc:<minute>``（字段 ``m:<pid>`` / ``c:<pid>``，按 pid 区分，
读取端跨 worker 聚合），Redis 不可用时退回进程内字典。

``get_samples(minutes)`` 返回 ``{minute: {"mem_mb": float, "cpu_pct": float}}``，
供 admin 概览时序接口与请求指标合并。多 worker 下内存求和、CPU 求和（总占用）。
"""
import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional

from utils.redis_client import get_redis, key as redis_key

logger = logging.getLogger(__name__)


def _proc_key(minute: int) -> str:
    """进程指标分钟桶键"""
    return redis_key("metrics", "proc", str(minute))


def _now_minute() -> int:
    return int(time.time()) // 60


def _history_minutes() -> int:
    """历史保留分钟数（配置不可用时回退 1440）"""
    try:
        from core.config import get_config

        return int(getattr(get_config().metrics, "history_minutes", 1440) or 1440)
    except Exception:  # noqa: BLE001
        return 1440


def _sample_interval() -> int:
    """采样间隔秒数（配置不可用时回退 15）"""
    try:
        from core.config import get_config

        return int(getattr(get_config().metrics, "sample_interval_seconds", 15) or 15)
    except Exception:  # noqa: BLE001
        return 15


def _aggregate(items) -> Dict[str, float]:
    """跨 pid 聚合：内存求和、CPU 求和（总占用）"""
    mems = [i["mem_mb"] for i in items]
    cpus = [i["cpu_pct"] for i in items]
    return {
        "mem_mb": round(sum(mems), 2),
        "cpu_pct": round(sum(cpus), 2),
    }


class ProcessMetrics:
    """进程内存/CPU 分钟级采样与读取"""

    def __init__(self):
        # 内存回退：minute -> pid -> {"mem_mb", "cpu_pct"}
        self._samples: Dict[int, Dict[int, Dict[str, float]]] = {}
        self._task: Optional[asyncio.Task] = None
        # 缓存 psutil.Process：cpu_percent(interval=None) 的基线存在实例上，
        # 每次新建实例会永远返回 0.0。
        self._proc: Optional[Any] = None

    def _read_process(self) -> Dict[str, float]:
        """读取当前进程内存（RSS）与 CPU 占用"""
        import psutil

        if self._proc is None:
            self._proc = psutil.Process(os.getpid())
        cpu = self._proc.cpu_percent(interval=None) or 0.0
        mem = self._proc.memory_info().rss / (1024 * 1024)
        return {"mem_mb": round(mem, 2), "cpu_pct": round(cpu, 2)}

    async def sample(self) -> Dict[str, float]:
        """采样一次并写入内存回退与 Redis"""
        info = self._read_process()
        minute = _now_minute()
        pid = os.getpid()

        self._samples.setdefault(minute, {})[pid] = info
        self._prune()

        client = await get_redis()
        if client is not None:
            k = _proc_key(minute)
            try:
                await client.hset(
                    k,
                    mapping={
                        f"m:{pid}": info["mem_mb"],
                        f"c:{pid}": info["cpu_pct"],
                    },
                )
                await client.expire(k, _history_minutes() * 60 + 60)
            except Exception as exc:  # noqa: BLE001 — 采样失败不影响主流程
                logger.debug("进程指标写入 Redis 失败: %s", exc)
        return info

    def _prune(self) -> None:
        lo = _now_minute() - _history_minutes()
        for minute in [m for m in self._samples if m < lo]:
            self._samples.pop(minute, None)

    async def get_samples(self, minutes: int) -> Dict[int, Dict[str, float]]:
        """读取最近 ``minutes`` 分钟进程指标（含当前分钟），按分钟聚合"""
        client = await get_redis()
        if client is not None:
            return await self._get_samples_redis(client, minutes)
        return self._get_samples_memory(minutes)

    def _get_samples_memory(self, minutes: int) -> Dict[int, Dict[str, float]]:
        lo = _now_minute() - minutes + 1
        return {
            m: _aggregate(pids.values())
            for m, pids in self._samples.items()
            if m >= lo
        }

    async def _get_samples_redis(self, client: Any, minutes: int) -> Dict[int, Dict[str, float]]:
        now = _now_minute()
        mins = list(range(now - minutes + 1, now + 1))
        if not mins:
            return {}

        pipe = client.pipeline()
        for m in mins:
            pipe.hgetall(_proc_key(m))
        raw = await pipe.execute()

        out: Dict[int, Dict[str, float]] = {}
        for m, data in zip(mins, raw):
            if not data:
                continue
            mems, cpus = [], []
            for field, value in data.items():
                try:
                    num = float(value)
                except (TypeError, ValueError):
                    continue
                if field.startswith("m:"):
                    mems.append(num)
                elif field.startswith("c:"):
                    cpus.append(num)
            if mems or cpus:
                out[m] = {
                    "mem_mb": round(sum(mems), 2),
                    "cpu_pct": round(sum(cpus), 2),
                }
        return out

    async def start(self) -> None:
        """启动后台采样（幂等）；先立即采样一次避免首屏无数据"""
        if self._task is not None and not self._task.done():
            return
        try:
            await self.sample()
        except Exception as exc:  # noqa: BLE001
            logger.warning("进程指标首次采样失败: %s", exc)
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """停止后台采样"""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None

    async def _loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(_sample_interval())
                try:
                    await self.sample()
                except Exception as exc:  # noqa: BLE001 — 单次失败不影响循环
                    logger.warning("进程指标采样失败: %s", exc)
        except asyncio.CancelledError:
            pass


_process_metrics: Optional[ProcessMetrics] = None


def get_process_metrics() -> ProcessMetrics:
    """获取全局进程指标采样器实例"""
    global _process_metrics
    if _process_metrics is None:
        _process_metrics = ProcessMetrics()
    return _process_metrics


def reset_process_metrics() -> None:
    """重置全局实例（测试隔离用）"""
    global _process_metrics
    _process_metrics = None
