from typing import Dict, Any
from datetime import datetime, timezone
from api.websocket.manager import Connection, ConnectionManager
import logging

logger = logging.getLogger(__name__)


def _get_manager():
    """获取当前连接管理器单例"""
    return ConnectionManager()


async def handle_room_join(connection: Connection, message: Dict[str, Any]) -> None:
    if connection.user_id is None:
        await connection.send({
            "type": "error",
            "error": "需要认证才能加入房间",
            "original_type": "room_join"
        })
        return

    room_id = message.get("room_id")
    if room_id is None:
        await connection.send({
            "type": "error",
            "error": "缺少 room_id",
            "original_type": "room_join"
        })
        return

    mgr = _get_manager()
    await mgr.subscribe_room(connection, room_id)

    # Broadcast presence_join to room
    if connection.username:
        await mgr.send_to_room(room_id, {
            "type": "presence_join",
            "room_id": room_id,
            "user_id": connection.user_id,
            "username": connection.username,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, exclude_user_id=connection.user_id)

    await connection.send({
        "type": "room_joined",
        "room_id": room_id,
        "message": f"已加入房间 {room_id}"
    })

    logger.info(f"用户 {connection.username} 加入房间 {room_id}")


async def handle_room_leave(connection: Connection, message: Dict[str, Any]) -> None:
    if connection.user_id is None:
        await connection.send({
            "type": "error",
            "error": "需要认证才能离开房间",
            "original_type": "room_leave"
        })
        return

    room_id = message.get("room_id")
    if room_id is None:
        await connection.send({
            "type": "error",
            "error": "缺少 room_id",
            "original_type": "room_leave"
        })
        return

    mgr = _get_manager()
    await mgr.unsubscribe_room(connection, room_id)

    # Broadcast presence_leave to room
    if connection.username:
        await mgr.send_to_room(room_id, {
            "type": "presence_leave",
            "room_id": room_id,
            "user_id": connection.user_id,
            "username": connection.username,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, exclude_user_id=connection.user_id)

    await connection.send({
        "type": "room_left",
        "room_id": room_id,
        "message": f"已离开房间 {room_id}"
    })

    logger.info(f"用户 {connection.username} 离开房间 {room_id}")


async def handle_presence_list(connection: Connection, message: Dict[str, Any]) -> None:
    if connection.user_id is None:
        await connection.send({
            "type": "error",
            "error": "需要认证才能查询在线状态",
            "original_type": "presence_list"
        })
        return

    room_id = message.get("room_id")
    if room_id is None:
        await connection.send({
            "type": "error",
            "error": "缺少 room_id",
            "original_type": "presence_list"
        })
        return

    mgr = _get_manager()
    users = await mgr.get_room_online_users(room_id)

    await connection.send({
        "type": "presence_list",
        "room_id": room_id,
        "users": users,
    })
