"""
进度消息处理器

处理操作进度推送相关的WebSocket消息
"""
from typing import Dict, Any, Optional
from datetime import datetime
from api.websocket.manager import Connection, manager
import logging

logger = logging.getLogger(__name__)

# 存储正在进行的操作进度
_active_operations: Dict[str, Dict[str, Any]] = {}


async def handle_progress_update(connection: Connection, message: Dict[str, Any]) -> None:
    """
    处理进度更新请求
    
    客户端发送:
    {
        "type": "progress_update",
        "operation_id": "uuid-string",
        "operation_type": "clone|pull|push|upload|download",
        "progress": 50,
        "status": "running|paused|completed|failed",
        "message": "正在下载文件...",
        "details": {
            "current": 50,
            "total": 100,
            "speed": "1.5MB/s",
            "eta": "30s"
        }
    }
    """
    operation_id = message.get("operation_id")
    operation_type = message.get("operation_type", "unknown")
    progress = message.get("progress", 0)
    status = message.get("status", "running")
    
    if not operation_id:
        await connection.send({
            "type": "error",
            "error": "缺少operation_id参数"
        })
        return
    
    # 存储操作进度
    _active_operations[operation_id] = {
        "operation_type": operation_type,
        "progress": progress,
        "status": status,
        "message": message.get("message", ""),
        "details": message.get("details", {}),
        "user_id": connection.user_id,
        "username": connection.username,
        "updated_at": datetime.now().isoformat(),
    }
    
    # 向用户推送进度更新
    progress_message = {
        "type": "progress",
        "operation_id": operation_id,
        "operation_type": operation_type,
        "progress": progress,
        "status": status,
        "message": message.get("message", ""),
        "details": message.get("details", {}),
        "timestamp": datetime.now().isoformat(),
    }
    
    await connection.send(progress_message)
    
    # 如果操作完成或失败，清理记录
    if status in ["completed", "failed"]:
        if operation_id in _active_operations:
            del _active_operations[operation_id]
    
    logger.debug(f"进度更新 operation_id={operation_id}, progress={progress}%, status={status}")


async def handle_progress_query(connection: Connection, message: Dict[str, Any]) -> None:
    """
    处理进度查询请求
    
    客户端发送:
    {
        "type": "progress_query",
        "operation_id": "uuid-string"
    }
    """
    operation_id = message.get("operation_id")
    
    if not operation_id:
        await connection.send({
            "type": "error",
            "error": "缺少operation_id参数"
        })
        return
    
    operation = _active_operations.get(operation_id)
    
    if operation:
        await connection.send({
            "type": "progress",
            "operation_id": operation_id,
            **operation,
            "timestamp": datetime.now().isoformat(),
        })
    else:
        await connection.send({
            "type": "progress_not_found",
            "operation_id": operation_id,
            "message": "未找到该操作的进度信息"
        })


# ==================== 服务端主动推送方法 ====================

async def push_progress(
    user_id: int,
    operation_id: str,
    operation_type: str,
    progress: int,
    message: str = "",
    details: Optional[Dict[str, Any]] = None
) -> int:
    """
    向用户推送进度更新
    
    Args:
        user_id: 用户ID
        operation_id: 操作ID
        operation_type: 操作类型
        progress: 进度百分比 (0-100)
        message: 进度消息
        details: 详细信息
        
    Returns:
        int: 通知到的连接数
    """
    progress_message = {
        "type": "progress",
        "operation_id": operation_id,
        "operation_type": operation_type,
        "progress": progress,
        "status": "running" if progress < 100 else "completed",
        "message": message,
        "details": details or {},
        "timestamp": datetime.now().isoformat(),
    }
    
    # 更新操作记录
    _active_operations[operation_id] = {
        "operation_type": operation_type,
        "progress": progress,
        "status": progress_message["status"],
        "message": message,
        "details": details or {},
        "updated_at": datetime.now().isoformat(),
    }
    
    return await manager.send_to_user(user_id, progress_message)


async def push_progress_to_repository(
    repository_id: int,
    operation_id: str,
    operation_type: str,
    progress: int,
    message: str = "",
    details: Optional[Dict[str, Any]] = None,
    exclude_user_id: Optional[int] = None
) -> int:
    """
    向仓库订阅者推送进度更新
    
    Args:
        repository_id: 仓库ID
        operation_id: 操作ID
        operation_type: 操作类型
        progress: 进度百分比
        message: 进度消息
        details: 详细信息
        exclude_user_id: 排除的用户ID
        
    Returns:
        int: 通知到的连接数
    """
    progress_message = {
        "type": "progress",
        "operation_id": operation_id,
        "operation_type": operation_type,
        "progress": progress,
        "status": "running" if progress < 100 else "completed",
        "message": message,
        "details": details or {},
        "timestamp": datetime.now().isoformat(),
    }
    
    return await manager.send_to_repository(repository_id, progress_message, exclude_user_id)


async def notify_operation_completed(
    user_id: int,
    operation_id: str,
    operation_type: str,
    result: Optional[Dict[str, Any]] = None
) -> int:
    """
    通知操作完成
    
    Args:
        user_id: 用户ID
        operation_id: 操作ID
        operation_type: 操作类型
        result: 操作结果
        
    Returns:
        int: 通知到的连接数
    """
    message = {
        "type": "progress",
        "operation_id": operation_id,
        "operation_type": operation_type,
        "progress": 100,
        "status": "completed",
        "message": "操作完成",
        "result": result or {},
        "completed_at": datetime.now().isoformat(),
    }
    
    # 清理操作记录
    if operation_id in _active_operations:
        del _active_operations[operation_id]
    
    return await manager.send_to_user(user_id, message)


async def notify_operation_failed(
    user_id: int,
    operation_id: str,
    operation_type: str,
    error: str
) -> int:
    """
    通知操作失败
    
    Args:
        user_id: 用户ID
        operation_id: 操作ID
        operation_type: 操作类型
        error: 错误信息
        
    Returns:
        int: 通知到的连接数
    """
    message = {
        "type": "progress",
        "operation_id": operation_id,
        "operation_type": operation_type,
        "progress": _active_operations.get(operation_id, {}).get("progress", 0),
        "status": "failed",
        "message": f"操作失败: {error}",
        "error": error,
        "failed_at": datetime.now().isoformat(),
    }
    
    # 清理操作记录
    if operation_id in _active_operations:
        del _active_operations[operation_id]
    
    return await manager.send_to_user(user_id, message)


def get_active_operations(user_id: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """
    获取活跃的操作列表
    
    Args:
        user_id: 用户ID，不提供则返回所有操作
        
    Returns:
        Dict: 操作ID到操作信息的映射
    """
    if user_id is None:
        return _active_operations.copy()
    
    return {
        op_id: op_info
        for op_id, op_info in _active_operations.items()
        if op_info.get("user_id") == user_id
    }
