"""
同步消息处理器

处理协作同步相关的WebSocket消息
"""
from typing import Dict, Any
from datetime import datetime
import uuid
from api.websocket.manager import Connection, manager
import logging

logger = logging.getLogger(__name__)


async def handle_sync_request(connection: Connection, message: Dict[str, Any]) -> None:
    """
    处理同步请求
    
    客户端发送:
    {
        "type": "sync_request",
        "repository_id": 123,
        "sync_type": "pull|push|fetch",
        "request_id": "uuid-string"
    }
    
    服务端响应:
    {
        "type": "sync_response",
        "request_id": "uuid-string",
        "status": "accepted|rejected",
        "message": "..."
    }
    """
    repository_id = message.get("repository_id")
    sync_type = message.get("sync_type", "fetch")
    request_id = message.get("request_id")
    
    if not repository_id:
        await connection.send({
            "type": "sync_response",
            "request_id": request_id,
            "status": "rejected",
            "error": "缺少repository_id参数"
        })
        return
    
    # 检查用户是否订阅了该仓库
    if repository_id not in connection.repository_ids:
        await connection.send({
            "type": "sync_response",
            "request_id": request_id,
            "status": "rejected",
            "error": "未订阅该仓库，请先发送subscribe消息"
        })
        return
    
    # TODO: 调用同步服务处理请求
    # 这里简化处理，实际应该调用你的同步服务
    
    await connection.send({
        "type": "sync_response",
        "request_id": request_id,
        "status": "accepted",
        "message": f"{sync_type} 请求已接受，开始处理...",
        "repository_id": repository_id,
        "sync_type": sync_type
    })
    
    # 通知其他用户有同步操作开始
    await manager.send_to_repository(
        repository_id,
        {
            "type": "sync_started",
            "repository_id": repository_id,
            "sync_type": sync_type,
            "started_by": connection.username,
            "started_at": datetime.now().isoformat(),
        },
        exclude_user_id=connection.user_id
    )
    
    logger.info(f"用户 {connection.username} 在仓库 {repository_id} 发起 {sync_type} 同步")


async def handle_sync_status(connection: Connection, message: Dict[str, Any]) -> None:
    """
    处理同步状态更新
    
    客户端发送:
    {
        "type": "sync_status",
        "repository_id": 123,
        "status": "in_progress|completed|failed",
        "progress": 50,
        "message": "正在同步...",
        "details": {...}
    }
    """
    repository_id = message.get("repository_id")
    status = message.get("status")
    progress = message.get("progress", 0)
    
    if not repository_id:
        await connection.send({
            "type": "error",
            "error": "缺少repository_id参数"
        })
        return
    
    # 广播同步状态给仓库的其他订阅者
    sync_update = {
        "type": "sync_status_update",
        "repository_id": repository_id,
        "status": status,
        "progress": progress,
        "message": message.get("message", ""),
        "details": message.get("details", {}),
        "updated_by": connection.username,
        "updated_at": datetime.now().isoformat(),
    }
    
    await manager.send_to_repository(
        repository_id,
        sync_update,
        exclude_user_id=connection.user_id
    )


# ==================== 服务端主动推送方法 ====================

async def broadcast_sync_started(repository_id: uuid.UUID, sync_type: str, initiator_id: uuid.UUID, initiator_name: str) -> int:
    """
    广播同步开始事件
    
    Args:
        repository_id: 仓库ID
        sync_type: 同步类型 (pull/push/fetch)
        initiator_id: 发起者用户ID
        initiator_name: 发起者用户名
        
    Returns:
        int: 通知到的连接数
    """
    message = {
        "type": "sync_event",
        "action": "started",
        "repository_id": repository_id,
        "sync_type": sync_type,
        "initiator": {
            "id": initiator_id,
            "username": initiator_name
        },
        "started_at": datetime.now().isoformat(),
    }
    
    return await manager.send_to_repository(repository_id, message, exclude_user_id=initiator_id)


async def broadcast_sync_completed(repository_id: uuid.UUID, sync_type: str, result: Dict[str, Any]) -> int:
    """
    广播同步完成事件
    
    Args:
        repository_id: 仓库ID
        sync_type: 同步类型
        result: 同步结果数据
        
    Returns:
        int: 通知到的连接数
    """
    message = {
        "type": "sync_event",
        "action": "completed",
        "repository_id": repository_id,
        "sync_type": sync_type,
        "result": result,
        "completed_at": datetime.now().isoformat(),
    }
    
    return await manager.send_to_repository(repository_id, message)


async def broadcast_sync_failed(repository_id: uuid.UUID, sync_type: str, error: str) -> int:
    """
    广播同步失败事件
    
    Args:
        repository_id: 仓库ID
        sync_type: 同步类型
        error: 错误信息
        
    Returns:
        int: 通知到的连接数
    """
    message = {
        "type": "sync_event",
        "action": "failed",
        "repository_id": repository_id,
        "sync_type": sync_type,
        "error": error,
        "failed_at": datetime.now().isoformat(),
    }
    
    return await manager.send_to_repository(repository_id, message)


async def broadcast_file_change(repository_id: uuid.UUID, file_changes: list) -> int:
    """
    广播文件变更事件
    
    Args:
        repository_id: 仓库ID
        file_changes: 文件变更列表
        
    Returns:
        int: 通知到的连接数
    """
    message = {
        "type": "file_change",
        "repository_id": repository_id,
        "changes": file_changes,
        "timestamp": datetime.now().isoformat(),
    }
    
    return await manager.send_to_repository(repository_id, message)
