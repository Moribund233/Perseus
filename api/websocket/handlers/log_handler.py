"""
WebSocket 日志处理器

提供实时日志推送功能，替代传统的 HTTP 轮询日志接口
"""
import logging
import asyncio
from collections import deque
from datetime import datetime
from typing import Dict, Set, Optional, Any, List
from dataclasses import dataclass, field

from api.websocket.manager import manager, Connection


@dataclass
class LogEntry:
    """日志条目数据类"""
    timestamp: str
    level: str
    logger: str
    message: str
    raw: str = field(default="")


class LogBuffer:
    """
    环形日志缓冲区

    在内存中维护最近 N 条日志，支持快速查询历史日志
    """

    def __init__(self, max_size: int = 10000):
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = asyncio.Lock()

    async def append(self, entry: LogEntry) -> None:
        """添加日志条目"""
        async with self._lock:
            self._buffer.append(entry)

    async def get_recent(self, count: int = 100, level: Optional[str] = None) -> List[LogEntry]:
        """
        获取最近的日志

        Args:
            count: 返回条目数量
            level: 过滤级别（可选）

        Returns:
            List[LogEntry]: 日志条目列表
        """
        async with self._lock:
            logs = list(self._buffer)

        if level:
            level_upper = level.upper()
            logs = [log for log in logs if log.level.upper() == level_upper]

        return logs[-count:] if len(logs) > count else logs

    async def get_stats(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        async with self._lock:
            total = len(self._buffer)
            level_counts = {}
            for entry in self._buffer:
                level_counts[entry.level] = level_counts.get(entry.level, 0) + 1

        return {
            "total_buffered": total,
            "buffer_capacity": self._buffer.maxlen,
            "level_counts": level_counts
        }


class LogSubscriptionManager:
    """
    日志订阅管理器

    管理 WebSocket 连接的日志订阅，支持按级别过滤
    """

    def __init__(self):
        # connection_id -> subscription_info
        self._subscriptions: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        connection: Connection,
        levels: Optional[List[str]] = None,
        loggers: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None
    ) -> None:
        """
        订阅日志

        Args:
            connection: WebSocket 连接
            levels: 关注的日志级别（如 ['INFO', 'ERROR']）
            loggers: 关注的日志器名称
            keywords: 关键字过滤
        """
        async with self._lock:
            self._subscriptions[connection.connection_id] = {
                "connection": connection,
                "levels": set(levels) if levels else None,
                "loggers": set(loggers) if loggers else None,
                "keywords": keywords,
                "subscribed_at": datetime.now().isoformat()
            }

    async def unsubscribe(self, connection: Connection) -> None:
        """取消订阅"""
        async with self._lock:
            self._subscriptions.pop(connection.connection_id, None)

    def should_send(self, connection_id: str, entry: LogEntry) -> bool:
        """
        检查是否应该向该连接发送日志

        Args:
            connection_id: 连接 ID
            entry: 日志条目

        Returns:
            bool: 是否应该发送
        """
        sub = self._subscriptions.get(connection_id)
        if not sub:
            return False

        # 级别过滤
        if sub["levels"] and entry.level.upper() not in sub["levels"]:
            return False

        # 日志器过滤
        if sub["loggers"] and entry.logger not in sub["loggers"]:
            return False

        # 关键字过滤
        if sub["keywords"]:
            if not any(kw.lower() in entry.message.lower() for kw in sub["keywords"]):
                return False

        return True

    async def broadcast(self, entry: LogEntry) -> None:
        """
        广播日志给所有订阅者

        Args:
            entry: 日志条目
        """
        dead_connections = []

        async with self._lock:
            subscriptions = list(self._subscriptions.items())

        for connection_id, sub in subscriptions:
            if not self.should_send(connection_id, entry):
                continue

            connection = sub["connection"]
            if not connection.is_alive:
                dead_connections.append(connection_id)
                continue

            try:
                await connection.send({
                    "type": "log",
                    "timestamp": entry.timestamp,
                    "level": entry.level,
                    "logger": entry.logger,
                    "message": entry.message
                })
            except Exception:
                dead_connections.append(connection_id)

        # 清理失效连接
        async with self._lock:
            for conn_id in dead_connections:
                self._subscriptions.pop(conn_id, None)


class WebSocketLogHandler(logging.Handler):
    """
    WebSocket 日志处理器

    将日志记录实时广播给订阅了日志频道的 WebSocket 客户端
    同时维护内存缓冲区供历史查询
    """

    def __init__(self, level: int = logging.NOTSET):
        super().__init__(level)
        self.buffer = LogBuffer(max_size=10000)
        self.subscription_manager = LogSubscriptionManager()
        self._formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    def format_time(self, timestamp: float) -> str:
        """格式化时间戳"""
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    def emit(self, record: logging.LogRecord) -> None:
        """
        发送日志到 WebSocket

        这个方法在日志记录时被调用，需要快速执行避免阻塞
        """
        entry = LogEntry(
            timestamp=self.format_time(record.created),
            level=record.levelname,
            logger=record.name,
            message=record.getMessage(),
            raw=self._formatter.format(record)
        )

        # 添加到缓冲区（异步操作，使用 create_task 避免阻塞）
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.buffer.append(entry))
        except RuntimeError:
            # 没有事件循环时，直接同步添加到缓冲区（跳过锁）
            self.buffer._buffer.append(entry)

        # 广播给订阅者
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.subscription_manager.broadcast(entry))
        except RuntimeError:
            # 没有事件循环时，跳过广播
            pass


# 全局实例
_log_handler: Optional[WebSocketLogHandler] = None


def get_websocket_log_handler() -> WebSocketLogHandler:
    """获取 WebSocket 日志处理器实例（单例）"""
    global _log_handler
    if _log_handler is None:
        _log_handler = WebSocketLogHandler()
    return _log_handler


# ==================== WebSocket 消息处理器 ====================

async def handle_subscribe_logs(connection: Connection, data: Dict[str, Any]) -> None:
    """
    处理日志订阅请求

    Args:
        connection: WebSocket 连接
        data: 消息数据，包含 filters
    """
    handler = get_websocket_log_handler()
    filters = data.get("filters", {})

    levels = filters.get("levels", ["INFO", "WARNING", "ERROR"])
    loggers = filters.get("loggers")
    keywords = filters.get("keywords")

    await handler.subscription_manager.subscribe(
        connection,
        levels=levels,
        loggers=loggers,
        keywords=keywords
    )

    # 发送确认
    await connection.send({
        "type": "logs_subscribed",
        "filters": {
            "levels": levels,
            "loggers": loggers,
            "keywords": keywords
        }
    })

    # 发送最近的历史日志
    history_count = data.get("history_count", 50)
    recent_logs = await handler.buffer.get_recent(count=history_count)

    if recent_logs:
        await connection.send({
            "type": "log_history",
            "logs": [
                {
                    "timestamp": log.timestamp,
                    "level": log.level,
                    "logger": log.logger,
                    "message": log.message
                }
                for log in recent_logs
            ],
            "total": len(recent_logs)
        })


async def handle_unsubscribe_logs(connection: Connection, data: Dict[str, Any]) -> None:
    """处理取消订阅请求"""
    handler = get_websocket_log_handler()
    await handler.subscription_manager.unsubscribe(connection)

    await connection.send({
        "type": "logs_unsubscribed"
    })


async def handle_get_log_stats(connection: Connection, data: Dict[str, Any]) -> None:
    """处理获取日志统计请求"""
    handler = get_websocket_log_handler()
    stats = await handler.buffer.get_stats()

    await connection.send({
        "type": "log_stats",
        "stats": stats
    })
