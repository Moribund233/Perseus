"""
在线状态（presence）全局注册表（规划 R4）

Redis 引用计数：每个 ``(room, user)`` 维护连接数，多连接/多 worker 下按用户去重。

键布局（统一 ``perseus:`` 命名空间）：
- ``perseus:presence:room:<room_id>:n``    HASH  user_id -> 连接数
- ``perseus:presence:room:<room_id>:name`` HASH  user_id -> username

TTL 由 manager 心跳续期；worker 崩溃后条目在 TTL 后自动过期。
Redis 不可用时所有方法为 no-op/空，manager 回退本进程 ``_room_index``（现状）。
"""
import logging
import uuid as _uuid
from typing import Any, Dict, List, Optional

from utils.redis_client import get_redis, key as redis_key

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 90


def _n_key(room_id) -> str:
    return redis_key("presence", "room", str(room_id), "n")


def _name_key(room_id) -> str:
    return redis_key("presence", "room", str(room_id), "name")


def _maybe_uuid(value):
    try:
        return _uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return value


class PresenceStore:
    """跨 worker 在线用户注册表（Redis 引用计数）"""

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self._ttl = ttl_seconds

    @property
    def ttl(self) -> int:
        return self._ttl

    async def enabled(self) -> bool:
        return await get_redis() is not None

    async def add(self, room_id, user_id, username: Optional[str]) -> None:
        client = await get_redis()
        if client is None or user_id is None:
            return
        uid = str(user_id)
        try:
            pipe = client.pipeline()
            pipe.hincrby(_n_key(room_id), uid, 1)
            pipe.hset(_name_key(room_id), uid, username or "")
            pipe.expire(_n_key(room_id), self._ttl)
            pipe.expire(_name_key(room_id), self._ttl)
            await pipe.execute()
        except Exception as exc:  # noqa: BLE001 — presence 失败不影响业务
            logger.warning("presence add 失败: %s", exc)

    async def remove(self, room_id, user_id) -> None:
        client = await get_redis()
        if client is None or user_id is None:
            return
        uid = str(user_id)
        try:
            remaining = await client.hincrby(_n_key(room_id), uid, -1)
            if int(remaining) <= 0:
                await client.hdel(_n_key(room_id), uid)
                await client.hdel(_name_key(room_id), uid)
        except Exception as exc:  # noqa: BLE001
            logger.warning("presence remove 失败: %s", exc)

    async def list_users(self, room_id) -> List[Dict[str, Any]]:
        client = await get_redis()
        if client is None:
            return []
        try:
            counts = await client.hgetall(_n_key(room_id))
            if not counts:
                return []
            names = await client.hgetall(_name_key(room_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning("presence list 失败: %s", exc)
            return []

        users: List[Dict[str, Any]] = []
        for uid, count in counts.items():
            try:
                if int(count) <= 0:
                    continue
            except (TypeError, ValueError):
                continue
            users.append({"user_id": _maybe_uuid(uid), "username": names.get(uid, "")})
        return users

    async def refresh(self, room_ids) -> None:
        """心跳续期：刷新本进程有连接的房间的 TTL"""
        client = await get_redis()
        room_ids = list(room_ids)
        if client is None or not room_ids:
            return
        try:
            pipe = client.pipeline()
            for rid in room_ids:
                pipe.expire(_n_key(rid), self._ttl)
                pipe.expire(_name_key(rid), self._ttl)
            await pipe.execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("presence refresh 失败: %s", exc)


# 全局单例（由 lifespan 绑定到 manager）
presence = PresenceStore()
