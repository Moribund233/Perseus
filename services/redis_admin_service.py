"""
Redis 运维状态服务（admin 可视化，只读）

聚合运维判断所需信息：
- 连接：是否配置/可达、Ping 延迟、版本/模式/运行时长
- worker：心跳注册表中的各 worker 存活、总线状态、本地连接/房间数
- 订阅：``PUBSUB NUMPAT`` 模式订阅数 vs 存活 worker 数（mismatch 告警）
- 指标：内存/客户端/ops/命中率/过期淘汰（INFO）
- 键空间：各命名空间分域键数（SCAN，带短缓存）
- 降级：客户端回退计数 + 广播总线收发/失败计数

全部优雅降级：Redis 不可用时返回 ``reachable=false`` 与已收集的降级计数。
"""
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urlsplit, urlunsplit

from core.config import get_config
from services.worker_registry import worker_registry
from utils import redis_client
from utils.realtime_bus import bus as realtime_bus

logger = logging.getLogger(__name__)

_KEYSPACE_TTL_SECONDS = 15
_keyspace_cache: Dict[str, Any] = {"at": 0.0, "items": []}

# 命名空间分域：domain, 用途, TTL 语义, 淘汰语义
NAMESPACES = [
    ("req", "请求统计分钟桶", "window*120+60s", "evictable"),
    ("oauth", "OAuth state", "600s", "evictable"),
    ("presence", "在线状态引用计数", "90s 心跳续期", "evictable"),
    ("revoked", "撤销黑名单读缓存", "1h / 60s", "evictable"),
    ("repo", "物理仓库存在缓存 L2", "30s", "evictable"),
    ("limit", "全局并发计数", "60s 自愈", "evictable"),
    ("worker", "worker 心跳注册表", "45s 心跳续期", "evictable"),
    ("collab", "协作 Y.Doc 快照/版本（网关）", "无 TTL", "persistent"),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_url(url: str) -> str:
    """隐藏 URL 中的凭据（密码/用户名）"""
    if not url:
        return ""
    try:
        parts = urlsplit(url)
        if parts.password or (parts.username and not parts.hostname):
            host = parts.hostname or ""
            if parts.port:
                host += f":{parts.port}"
            if parts.username:
                netloc = f"{parts.username}:***@{host}"
            else:
                netloc = f"***@{host}"
            return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
        return url
    except Exception:  # noqa: BLE001
        return "redis://***"


class RedisAdminService:
    async def get_status(self) -> Dict[str, Any]:
        config = get_config()
        expected = config.gunicorn.workers
        result: Dict[str, Any] = {
            "configured": redis_client.is_configured(),
            "reachable": False,
            "latency_ms": None,
            "server": {},
            "memory": {},
            "clients": {},
            "stats": {},
            "workers": {"expected": expected, "alive": 0, "items": []},
            "pubsub": {
                "pattern_subscriptions": None,
                "expected_workers": expected,
                "mismatch": False,
                "channels": [],
            },
            "keyspace": [],
            "degradation": self._degradation(),
            "generated_at": _now_iso(),
        }

        client = await redis_client.get_redis()
        if client is None:
            return result

        result["reachable"] = True
        await self._fill_ping(client, result)
        await self._fill_info(client, result)
        await self._fill_workers(result)
        await self._fill_pubsub(client, result)
        result["keyspace"] = await self._keyspace_counts(client)
        return result

    async def get_config(self) -> Dict[str, Any]:
        settings = get_config().redis
        runtime: Dict[str, Any] = {}
        client = await redis_client.get_redis()
        if client is not None:
            try:
                info = await client.info("memory")
                runtime = {
                    "maxmemory": int(info.get("maxmemory") or 0),
                    "maxmemory_policy": info.get("maxmemory_policy"),
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("读取 Redis memory 配置失败: %s", exc)

        return {
            "settings": {
                "url": _redact_url(settings.url),
                "namespace": settings.namespace,
                "pubsub_prefix": settings.pubsub_prefix or f"{settings.namespace}:ws",
                "reconnect_cooldown": settings.reconnect_cooldown,
            },
            "runtime": runtime,
            "editable": False,
            "source": "env",
            "generated_at": _now_iso(),
        }

    # ---------------- 内部 ----------------

    def _degradation(self) -> Dict[str, Any]:
        cs = redis_client.get_client_stats()
        bs = realtime_bus.stats()
        return {
            "unavailable_returns": cs.get("unavailable_returns", 0),
            "connect_failures": cs.get("connect_failures", 0),
            "require_failures": cs.get("require_failures", 0),
            "bus_running": bs.get("running", False),
            "bus_published": bs.get("published", 0),
            "bus_publish_failures": bs.get("publish_failures", 0),
            "bus_received": bs.get("received", 0),
            "bus_dispatch_failures": bs.get("dispatch_failures", 0),
            "bus_last_error": bs.get("last_error"),
        }

    async def _fill_ping(self, client, result: Dict[str, Any]) -> None:
        try:
            start = time.perf_counter()
            await client.ping()
            result["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis ping 失败: %s", exc)

    async def _fill_info(self, client, result: Dict[str, Any]) -> None:
        try:
            info = await client.info()
        except Exception as exc:  # noqa: BLE001
            logger.warning("读取 Redis INFO 失败: %s", exc)
            return

        result["server"] = {
            "version": info.get("redis_version"),
            "mode": info.get("redis_mode"),
            "os": info.get("os"),
            "uptime_seconds": _int(info.get("uptime_in_seconds")),
        }
        result["memory"] = {
            "used": _int(info.get("used_memory")),
            "used_peak": _int(info.get("used_memory_peak")),
            "rss": _int(info.get("used_memory_rss")),
            "maxmemory": _int(info.get("maxmemory")),
            "maxmemory_policy": info.get("maxmemory_policy"),
            "fragmentation_ratio": _float(info.get("mem_fragmentation_ratio")),
        }
        result["clients"] = {
            "connected": _int(info.get("connected_clients")),
            "blocked": _int(info.get("blocked_clients")),
        }
        hits = _int(info.get("keyspace_hits"))
        misses = _int(info.get("keyspace_misses"))
        total = hits + misses
        result["stats"] = {
            "ops_per_sec": _float(info.get("instantaneous_ops_per_sec")),
            "keyspace_hits": hits,
            "keyspace_misses": misses,
            "hit_rate": round(hits / total, 4) if total else None,
            "expired_keys": _int(info.get("expired_keys")),
            "evicted_keys": _int(info.get("evicted_keys")),
        }

    async def _fill_workers(self, result: Dict[str, Any]) -> None:
        try:
            items = await worker_registry.list_workers()
        except Exception as exc:  # noqa: BLE001
            logger.warning("读取 worker 注册表失败: %s", exc)
            items = []
        result["workers"]["items"] = items
        result["workers"]["alive"] = sum(1 for w in items if w.get("alive"))

    async def _fill_pubsub(self, client, result: Dict[str, Any]) -> None:
        try:
            numpat = await client.pubsub_numpat()
            result["pubsub"]["pattern_subscriptions"] = _int(numpat)
        except Exception as exc:  # noqa: BLE001
            logger.warning("读取 PUBSUB NUMPAT 失败: %s", exc)
        try:
            channels = await client.pubsub_channels()
            result["pubsub"]["channels"] = sorted(channels)[:100]
        except Exception as exc:  # noqa: BLE001
            logger.warning("读取 PUBSUB CHANNELS 失败: %s", exc)

        alive = result["workers"]["alive"]
        numpat = result["pubsub"]["pattern_subscriptions"]
        # 每个存活 worker 的广播总线应有 1 个模式订阅；少于存活数即存在订阅缺失
        result["pubsub"]["mismatch"] = (
            numpat is not None and alive > 0 and numpat < alive
        )

    async def _keyspace_counts(self, client) -> List[Dict[str, Any]]:
        now = time.monotonic()
        if _keyspace_cache["items"] and (now - _keyspace_cache["at"]) < _KEYSPACE_TTL_SECONDS:
            return _keyspace_cache["items"]

        namespace = get_config().redis.namespace
        items: List[Dict[str, Any]] = []
        for domain, use, ttl, policy in NAMESPACES:
            pattern = f"{namespace}:{domain}:*"
            keys = await self._scan_count(client, pattern)
            items.append({
                "namespace": pattern,
                "domain": domain,
                "use": use,
                "ttl": ttl,
                "policy": policy,
                "keys": keys,
            })
        _keyspace_cache["at"] = now
        _keyspace_cache["items"] = items
        return items

    async def _scan_count(self, client, pattern: str, max_iterations: int = 20, count: int = 500) -> int:
        total = 0
        cursor = 0
        try:
            for _ in range(max_iterations):
                cursor, keys = await client.scan(cursor=cursor, match=pattern, count=count)
                total += len(keys)
                if cursor == 0:
                    break
        except Exception as exc:  # noqa: BLE001
            logger.warning("SCAN 统计失败 pattern=%s: %s", pattern, exc)
        return total


def _int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


_redis_admin_service: RedisAdminService = RedisAdminService()


def get_redis_admin_service() -> RedisAdminService:
    return _redis_admin_service
