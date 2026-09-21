"""
Redis 异步客户端（单例 + 健康恢复）

- 按 ``config.redis.url`` 惰性创建并缓存异步命令客户端；
- 连接失败后按 ``config.redis.reconnect_cooldown`` 冷却重试（不再永久冻结），
  未配置或持续不可达时返回 None，**可选**调用方回退进程内实现；
- ``require_redis()`` 供**强依赖**场景（OAuth state、WS 广播）使用：
  不可用即抛 ``RedisUnavailableError``，显式降级而非静默出错；
- ``create_pubsub_client()`` 为 pub/sub 订阅提供独立连接（订阅态会阻塞普通命令，
  且不设 ``socket_timeout``）；
- ``key()`` / ``ws_channel()`` 统一 ``perseus:`` 命名空间（分域命名）。
"""
import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

_redis_client: Optional["Redis"] = None
_last_attempt: float = 0.0
_lock: Optional[asyncio.Lock] = None

# 进程生命周期降级计数（供 admin Redis 状态端点观测）
_stats: dict = {
    "unavailable_returns": 0,  # get_redis() 返回 None 的次数
    "connect_failures": 0,     # 建连/ping 失败次数
    "require_failures": 0,     # require_redis() 抛错次数
}


class RedisUnavailableError(RuntimeError):
    """强依赖 Redis 的场景在不可用时抛出（显式降级，不静默）"""


def get_client_stats() -> dict:
    """获取 Redis 客户端降级计数（副本，避免外部篡改内部状态）"""
    return dict(_stats)


def reset_client_stats() -> None:
    """重置降级计数（测试隔离用）"""
    for k in _stats:
        _stats[k] = 0


def _redis_url() -> str:
    try:
        from core.config import get_config

        return (get_config().redis.url or "").strip()
    except Exception:  # noqa: BLE001 — 配置未就绪时视为未启用
        return ""


def _redis_settings():
    try:
        from core.config import get_config

        return get_config().redis
    except Exception:  # noqa: BLE001 — 配置未就绪时退回默认
        return None


def _namespace() -> str:
    settings = _redis_settings()
    return (getattr(settings, "namespace", "") or "perseus").strip(":") or "perseus"


def _reconnect_cooldown() -> float:
    settings = _redis_settings()
    try:
        return float(getattr(settings, "reconnect_cooldown", 5.0))
    except Exception:  # noqa: BLE001
        return 5.0


def _get_lock() -> asyncio.Lock:
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


def is_configured() -> bool:
    """是否配置了 Redis URL（不代表当前可达）"""
    return bool((_redis_url() or "").strip())


def key(*parts: str) -> str:
    """按统一命名空间拼接键，如 ``key("req", "total")`` → ``perseus:req:total``"""
    return ":".join((_namespace(), *[str(p) for p in parts]))


def _ws_prefix() -> str:
    settings = _redis_settings()
    return (getattr(settings, "ws_prefix", None) or f"{_namespace()}:ws").strip(":")


def ws_channel(scope: str, target_id=None) -> str:
    """实时广播通道名，如 ``perseus:ws:room:<uuid>``"""
    if target_id is None:
        return f"{_ws_prefix()}:{scope}"
    return f"{_ws_prefix()}:{scope}:{target_id}"


def ws_pattern() -> str:
    """实时广播通道订阅模式（psubscribe）"""
    return f"{_ws_prefix()}:*"


async def get_redis() -> Optional["Redis"]:
    """
    获取全局异步 Redis 命令客户端（无则返回 None）。

    失败后按冷却重试；连续失败不阻塞业务。
    """
    global _redis_client, _last_attempt
    if _redis_client is not None:
        return _redis_client

    url = _redis_url()
    if not url:
        logger.debug("Redis 未配置，相关功能回退进程内实现")
        _stats["unavailable_returns"] += 1
        return None

    cooldown = _reconnect_cooldown()
    if _last_attempt and (time.monotonic() - _last_attempt) < cooldown:
        _stats["unavailable_returns"] += 1
        return None

    async with _get_lock():
        if _redis_client is not None:
            return _redis_client
        if _last_attempt and (time.monotonic() - _last_attempt) < cooldown:
            _stats["unavailable_returns"] += 1
            return None
        _last_attempt = time.monotonic()
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(
                url,
                decode_responses=True,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
                health_check_interval=2.0,
            )
            await client.ping()
            _redis_client = client
            logger.info("Redis 客户端已就绪")
        except Exception as exc:  # noqa: BLE001 — 失联即降级，不阻塞业务
            logger.warning("Redis 不可用，相关功能回退/降级: %s", exc)
            _stats["connect_failures"] += 1
            _redis_client = None
    return _redis_client


async def require_redis() -> "Redis":
    """强依赖场景取用：不可用即抛 ``RedisUnavailableError``（显式降级，不静默）"""
    client = await get_redis()
    if client is None:
        _stats["require_failures"] += 1
        raise RedisUnavailableError("Redis 不可用（未配置或连接失败），强依赖功能无法继续")
    return client


async def create_pubsub_client() -> Optional["Redis"]:
    """
    为 pub/sub 订阅创建**独立**连接（不复用命令客户端）。

    订阅连接处于订阅态时无法执行普通命令，故不设 ``socket_timeout``；
    由调用方负责 ``aclose()``。
    """
    url = _redis_url()
    if not url:
        return None
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=1.0,
            health_check_interval=2.0,
        )
        await client.ping()
        return client
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis pub/sub 客户端创建失败: %s", exc)
        return None


async def reset_redis() -> None:
    """关闭并清空全局客户端（测试隔离用）"""
    global _redis_client, _last_attempt
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:  # noqa: BLE001
            pass
    _redis_client = None
    _last_attempt = 0.0
