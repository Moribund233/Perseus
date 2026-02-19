"""
WebSocket消息处理器模块

注册所有消息类型处理器
"""
import logging
from api.websocket.handlers import notification, sync, progress, log_handler
from api.websocket.manager import manager

# 使用标准 logging 避免循环导入
logger = logging.getLogger("websocket")


def register_all_handlers():
    """注册所有消息处理器"""
    # 注册ping/pong心跳处理器
    manager.register_handler("ping", notification.handle_ping)

    # 注册订阅处理器
    manager.register_handler("subscribe", notification.handle_subscribe)
    manager.register_handler("unsubscribe", notification.handle_unsubscribe)

    # 注册同步处理器
    manager.register_handler("sync_request", sync.handle_sync_request)
    manager.register_handler("sync_status", sync.handle_sync_status)

    # 注册进度处理器
    manager.register_handler("progress_update", progress.handle_progress_update)

    # 注册广播处理器（管理员功能）
    manager.register_handler("broadcast", notification.handle_broadcast)

    # 注册实时日志处理器
    manager.register_handler("subscribe_logs", log_handler.handle_subscribe_logs)
    manager.register_handler("unsubscribe_logs", log_handler.handle_unsubscribe_logs)
    manager.register_handler("get_log_stats", log_handler.handle_get_log_stats)

    logger.debug("WebSocket消息处理器注册完成")
