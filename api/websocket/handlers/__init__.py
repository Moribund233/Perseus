"""
WebSocket消息处理器模块

注册所有消息类型处理器
"""
import logging
from api.websocket.handlers import notification, sync, progress, log_handler
from api.websocket.manager import manager

logger = logging.getLogger("websocket")


def register_all_handlers():
    """
    注册所有消息处理器
    
    处理器类型：
    - ping: 心跳检测
    - subscribe/unsubscribe: 仓库订阅
    - sync_request/sync_status: 同步操作
    - progress_update: 进度更新
    - broadcast: 管理员广播
    - subscribe_logs/unsubscribe_logs/get_log_stats: 实时日志
    """
    handlers = {
        "ping": notification.handle_ping,
        "subscribe": notification.handle_subscribe,
        "unsubscribe": notification.handle_unsubscribe,
        "sync_request": sync.handle_sync_request,
        "sync_status": sync.handle_sync_status,
        "progress_update": progress.handle_progress_update,
        "broadcast": notification.handle_broadcast,
        "progress_query": progress.handle_progress_query,
        "subscribe_logs": log_handler.handle_subscribe_logs,
        "unsubscribe_logs": log_handler.handle_unsubscribe_logs,
        "get_log_stats": log_handler.handle_get_log_stats,
    }
    
    for msg_type, handler in handlers.items():
        manager.register_handler(msg_type, handler)
    
    logger.debug(f"WebSocket处理器注册完成: {len(handlers)}个")
