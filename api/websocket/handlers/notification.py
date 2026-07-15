"""
通知消息处理器

处理各类通知相关的WebSocket消息
"""
from typing import Dict, Any
from datetime import datetime
import uuid
from api.websocket.manager import Connection, manager
import logging

logger = logging.getLogger(__name__)


async def handle_ping(connection: Connection, message: Dict[str, Any]) -> None:
    """
    处理心跳ping消息
    
    客户端发送: {"type": "ping", "timestamp": "2024-01-01T12:00:00Z"}
    服务端响应: {"type": "pong", "timestamp": "...", "server_time": "..."}
    """
    connection.update_ping()
    
    await connection.send({
        "type": "pong",
        "timestamp": message.get("timestamp"),
        "server_time": datetime.now().isoformat(),
    })


async def handle_subscribe(connection: Connection, message: Dict[str, Any]) -> None:
    """
    处理订阅请求
    
    客户端发送:
    {
        "type": "subscribe",
        "channel": "repository",
        "repository_id": 123
    }
    
    或订阅用户通知:
    {
        "type": "subscribe",
        "channel": "user_notifications"
    }
    """
    channel = message.get("channel", "")
    
    if channel == "repository":
        repository_id = message.get("repository_id")
        if repository_id is None:
            await connection.send({
                "type": "error",
                "error": "订阅仓库需要提供repository_id",
                "original_type": "subscribe"
            })
            return
        
        await manager.subscribe_repository(connection, repository_id)
        
        await connection.send({
            "type": "subscribed",
            "channel": "repository",
            "repository_id": repository_id,
            "message": f"成功订阅仓库 {repository_id} 的通知"
        })
        
        logger.info(f"用户 {connection.username} 订阅仓库 {repository_id}")
    
    elif channel == "user_notifications":
        # 用户通知订阅（自动基于用户绑定）
        await connection.send({
            "type": "subscribed",
            "channel": "user_notifications",
            "message": "成功订阅用户通知"
        })
    
    else:
        await connection.send({
            "type": "error",
            "error": f"未知的订阅频道: {channel}",
            "supported_channels": ["repository", "user_notifications"]
        })


async def handle_unsubscribe(connection: Connection, message: Dict[str, Any]) -> None:
    """
    处理取消订阅请求
    
    客户端发送:
    {
        "type": "unsubscribe",
        "channel": "repository",
        "repository_id": 123
    }
    """
    channel = message.get("channel", "")
    
    if channel == "repository":
        repository_id = message.get("repository_id")
        if repository_id:
            await manager.unsubscribe_repository(connection, repository_id)
            
            await connection.send({
                "type": "unsubscribed",
                "channel": "repository",
                "repository_id": repository_id,
                "message": f"已取消订阅仓库 {repository_id}"
            })
    
    elif channel == "user_notifications":
        await connection.send({
            "type": "unsubscribed",
            "channel": "user_notifications",
            "message": "已取消订阅用户通知"
        })


async def handle_broadcast(connection: Connection, message: Dict[str, Any]) -> None:
    """
    处理广播请求（管理员功能）
    
    客户端发送:
    {
        "type": "broadcast",
        "content": {
            "type": "system_notification",
            "title": "系统维护通知",
            "message": "系统将于今晚10点维护"
        }
    }
    """
    # 检查是否为管理员
    if not connection.metadata.get("is_admin", False):
        await connection.send({
            "type": "error",
            "error": "权限不足，只有管理员可以发送广播"
        })
        return
    
    content = message.get("content", {})
    
    # 添加广播元数据
    broadcast_message = {
        **content,
        "broadcast_at": datetime.now().isoformat(),
        "broadcast_by": connection.username,
    }
    
    # 发送给所有连接
    count = await manager.broadcast(broadcast_message)
    
    await connection.send({
        "type": "broadcast_sent",
        "recipient_count": count,
        "message": f"广播已发送给 {count} 个连接"
    })
    
    logger.info(f"管理员 {connection.username} 发送广播，覆盖 {count} 个连接")


# ==================== 服务端主动推送方法 ====================

async def notify_commit_new(repository_id: uuid.UUID, commit_data: Dict[str, Any], exclude_user_id: uuid.UUID = None) -> int:
    """
    通知仓库有新提交
    
    Args:
        repository_id: 仓库ID
        commit_data: 提交信息
        exclude_user_id: 排除的用户ID（提交者自己）
        
    Returns:
        int: 通知到的连接数
    """
    message = {
        "type": "notification",
        "action": "commit_new",
        "repository_id": repository_id,
        "data": commit_data,
        "timestamp": datetime.now().isoformat(),
    }
    
    return await manager.send_to_repository(repository_id, message, exclude_user_id)


async def notify_branch_update(repository_id: uuid.UUID, branch_data: Dict[str, Any]) -> int:
    """
    通知分支更新
    
    Args:
        repository_id: 仓库ID
        branch_data: 分支信息
        
    Returns:
        int: 通知到的连接数
    """
    message = {
        "type": "notification",
        "action": "branch_update",
        "repository_id": repository_id,
        "data": branch_data,
        "timestamp": datetime.now().isoformat(),
    }
    
    return await manager.send_to_repository(repository_id, message)


async def notify_repository_event(repository_id: uuid.UUID, event_type: str, event_data: Dict[str, Any]) -> int:
    """
    通用仓库事件通知
    
    Args:
        repository_id: 仓库ID
        event_type: 事件类型
        event_data: 事件数据
        
    Returns:
        int: 通知到的连接数
    """
    message = {
        "type": "notification",
        "action": event_type,
        "repository_id": repository_id,
        "data": event_data,
        "timestamp": datetime.now().isoformat(),
    }
    
    return await manager.send_to_repository(repository_id, message)


async def notify_user(user_id: uuid.UUID, notification_type: str, data: Dict[str, Any]) -> int:
    """
    向用户发送个人通知
    
    Args:
        user_id: 用户ID
        notification_type: 通知类型
        data: 通知数据
        
    Returns:
        int: 通知到的连接数
    """
    message = {
        "type": "user_notification",
        "notification_type": notification_type,
        "data": data,
        "timestamp": datetime.now().isoformat(),
    }
    
    return await manager.send_to_user(user_id, message)
