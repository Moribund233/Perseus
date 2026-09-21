"""
Worker 心跳注册表（跨 worker 存活与订阅观测）

每个应用 worker 周期性把自己写入 Redis 哈希 ``perseus:worker:<worker_id>``
（带 TTL，由心跳续期）。任一 worker 的 HTTP 请求据此即可看到**全部** worker 的
存活、广播总线状态与本地连接/房间数——这是 Redis INFO 无法提供的信息。

Redis 不可用时写入/读取均为 no-op/空，不影响业务。
"""
import logging
import os
import socket
import time
from typing import Any, Dict, List, Optional

from utils.redis_client import get_redis, key as redis_key
from utils.realtime_bus import WORKER_ID

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 45
_STARTED_AT = time.time()


def _worker_key(worker_id: str) -> str:
    return redis_key("worker", worker_id)


class WorkerRegistry:
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self._ttl = ttl_seconds

    @property
    def ttl(self) -> int:
        return self._ttl

    async def heartbeat(self, manager=None, bus=None) -> None:
        """写入/续期本 worker 的心跳记录（Redis 不可用时静默跳过）"""
        client = await get_redis()
        if client is None:
            return

        fields: Dict[str, str] = {
            "worker_id": WORKER_ID,
            "pid": str(os.getpid()),
            "host": socket.gethostname(),
            "started_at": str(int(_STARTED_AT)),
            "last_seen": str(int(time.time())),
        }
        if bus is not None:
            try:
                stats = bus.stats()
                fields["bus_running"] = "1" if stats.get("running") else "0"
                fields["bus_published"] = str(stats.get("published", 0))
                fields["bus_received"] = str(stats.get("received", 0))
                fields["bus_publish_failures"] = str(stats.get("publish_failures", 0))
            except Exception:  # noqa: BLE001
                pass
        if manager is not None:
            try:
                fields["local_connections"] = str(len(manager.active_connections))
                async with manager._lock:
                    fields["presence_rooms"] = str(len(manager._room_index))
            except Exception:  # noqa: BLE001
                pass

        try:
            await client.hset(_worker_key(WORKER_ID), mapping=fields)
            await client.expire(_worker_key(WORKER_ID), self._ttl)
        except Exception as exc:  # noqa: BLE001 — 心跳失败不影响业务
            logger.warning("worker 心跳写入失败: %s", exc)

    async def list_workers(self) -> List[Dict[str, Any]]:
        """列出注册表中全部 worker（含存活判定）"""
        client = await get_redis()
        if client is None:
            return []

        now = time.time()
        items: List[Dict[str, Any]] = []
        pattern = redis_key("worker", "*")
        try:
            cursor = 0
            for _ in range(20):
                cursor, keys = await client.scan(cursor=cursor, match=pattern, count=200)
                for k in keys:
                    raw = await client.hgetall(k)
                    if raw:
                        items.append(self._decode(raw, now))
                if cursor == 0:
                    break
        except Exception as exc:  # noqa: BLE001
            logger.warning("worker 列表读取失败: %s", exc)
            return []

        items.sort(key=lambda x: x.get("worker_id") or "")
        return items

    def _decode(self, raw: Dict[str, Any], now: float) -> Dict[str, Any]:
        last_seen = _to_int(raw.get("last_seen"), 0)
        age = max(0, int(now - last_seen)) if last_seen else None
        return {
            "worker_id": raw.get("worker_id"),
            "pid": _to_int(raw.get("pid"), None),
            "host": raw.get("host"),
            "started_at": _to_int(raw.get("started_at"), None),
            "last_seen": last_seen or None,
            "age_seconds": age,
            "alive": age is not None and age <= self._ttl,
            "bus_running": raw.get("bus_running") == "1",
            "bus_published": _to_int(raw.get("bus_published"), 0),
            "bus_received": _to_int(raw.get("bus_received"), 0),
            "bus_publish_failures": _to_int(raw.get("bus_publish_failures"), 0),
            "local_connections": _to_int(raw.get("local_connections"), 0),
            "presence_rooms": _to_int(raw.get("presence_rooms"), 0),
        }


def _to_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# 全局单例
worker_registry = WorkerRegistry()
