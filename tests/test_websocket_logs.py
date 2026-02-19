"""
WebSocket 实时日志功能测试

测试内容：
1. WebSocketLogHandler 基本功能
2. LogBuffer 缓冲区操作
3. LogSubscriptionManager 订阅管理
4. WebSocket 日志端点连接测试
"""

import pytest
import asyncio
import logging
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# 添加项目根目录到路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.websocket.handlers.log_handler import (
    LogEntry,
    LogBuffer,
    LogSubscriptionManager,
    WebSocketLogHandler,
    get_websocket_log_handler
)


class TestLogEntry:
    """测试日志条目数据类"""

    def test_log_entry_creation(self):
        """测试创建日志条目"""
        entry = LogEntry(
            timestamp="2026-02-18 10:30:45",
            level="INFO",
            logger="test",
            message="Test message"
        )
        assert entry.timestamp == "2026-02-18 10:30:45"
        assert entry.level == "INFO"
        assert entry.logger == "test"
        assert entry.message == "Test message"


class TestLogBuffer:
    """测试日志缓冲区"""

    @pytest.fixture
    def buffer(self):
        return LogBuffer(max_size=100)

    @pytest.mark.asyncio
    async def test_append_and_get_recent(self, buffer):
        """测试添加和获取日志"""
        entry = LogEntry(
            timestamp="2026-02-18 10:30:45",
            level="INFO",
            logger="test",
            message="Test message"
        )

        await buffer.append(entry)
        logs = await buffer.get_recent(count=10)

        assert len(logs) == 1
        assert logs[0].message == "Test message"

    @pytest.mark.asyncio
    async def test_buffer_size_limit(self):
        """测试缓冲区大小限制"""
        buffer = LogBuffer(max_size=5)

        # 添加 10 条日志
        for i in range(10):
            entry = LogEntry(
                timestamp=f"2026-02-18 10:30:{i:02d}",
                level="INFO",
                logger="test",
                message=f"Message {i}"
            )
            await buffer.append(entry)

        logs = await buffer.get_recent(count=100)
        assert len(logs) == 5  # 只保留最近的 5 条
        assert logs[-1].message == "Message 9"

    @pytest.mark.asyncio
    async def test_level_filter(self, buffer):
        """测试级别过滤"""
        # 添加不同级别的日志
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            entry = LogEntry(
                timestamp="2026-02-18 10:30:45",
                level=level,
                logger="test",
                message=f"{level} message"
            )
            await buffer.append(entry)

        # 过滤 ERROR 级别
        error_logs = await buffer.get_recent(count=100, level="ERROR")
        assert len(error_logs) == 1
        assert error_logs[0].level == "ERROR"

    @pytest.mark.asyncio
    async def test_get_stats(self, buffer):
        """测试获取统计信息"""
        # 添加一些日志
        for i in range(5):
            entry = LogEntry(
                timestamp=f"2026-02-18 10:30:{i:02d}",
                level="INFO" if i % 2 == 0 else "ERROR",
                logger="test",
                message=f"Message {i}"
            )
            await buffer.append(entry)

        stats = await buffer.get_stats()
        assert stats["total_buffered"] == 5
        assert stats["buffer_capacity"] == 100
        assert "INFO" in stats["level_counts"]
        assert "ERROR" in stats["level_counts"]


class TestLogSubscriptionManager:
    """测试日志订阅管理器"""

    @pytest.fixture
    def manager(self):
        return LogSubscriptionManager()

    @pytest.fixture
    def mock_connection(self):
        conn = Mock()
        conn.connection_id = "test_conn_1"
        conn.is_alive = True
        conn.send = AsyncMock()
        return conn

    @pytest.mark.asyncio
    async def test_subscribe(self, manager, mock_connection):
        """测试订阅功能"""
        await manager.subscribe(
            mock_connection,
            levels=["INFO", "ERROR"],
            loggers=["app"],
            keywords=["test"]
        )

        assert mock_connection.connection_id in manager._subscriptions
        sub = manager._subscriptions[mock_connection.connection_id]
        assert sub["levels"] == {"INFO", "ERROR"}
        assert sub["loggers"] == {"app"}
        assert sub["keywords"] == ["test"]

    @pytest.mark.asyncio
    async def test_unsubscribe(self, manager, mock_connection):
        """测试取消订阅"""
        await manager.subscribe(mock_connection, levels=["INFO"])
        await manager.unsubscribe(mock_connection)

        assert mock_connection.connection_id not in manager._subscriptions

    def test_should_send_with_level_filter(self, manager, mock_connection):
        """测试级别过滤"""
        asyncio.run(manager.subscribe(mock_connection, levels=["INFO", "ERROR"]))

        info_entry = LogEntry(
            timestamp="2026-02-18 10:30:45",
            level="INFO",
            logger="test",
            message="Info message"
        )
        debug_entry = LogEntry(
            timestamp="2026-02-18 10:30:45",
            level="DEBUG",
            logger="test",
            message="Debug message"
        )

        assert manager.should_send(mock_connection.connection_id, info_entry) is True
        assert manager.should_send(mock_connection.connection_id, debug_entry) is False

    def test_should_send_with_logger_filter(self, manager, mock_connection):
        """测试日志器过滤"""
        asyncio.run(manager.subscribe(mock_connection, loggers=["app", "git"]))

        app_entry = LogEntry(
            timestamp="2026-02-18 10:30:45",
            level="INFO",
            logger="app",
            message="App message"
        )
        other_entry = LogEntry(
            timestamp="2026-02-18 10:30:45",
            level="INFO",
            logger="other",
            message="Other message"
        )

        assert manager.should_send(mock_connection.connection_id, app_entry) is True
        assert manager.should_send(mock_connection.connection_id, other_entry) is False

    def test_should_send_with_keyword_filter(self, manager, mock_connection):
        """测试关键字过滤"""
        asyncio.run(manager.subscribe(mock_connection, keywords=["error", "failed"]))

        error_entry = LogEntry(
            timestamp="2026-02-18 10:30:45",
            level="INFO",
            logger="test",
            message="An error occurred"
        )
        success_entry = LogEntry(
            timestamp="2026-02-18 10:30:45",
            level="INFO",
            logger="test",
            message="Operation succeeded"
        )

        assert manager.should_send(mock_connection.connection_id, error_entry) is True
        assert manager.should_send(mock_connection.connection_id, success_entry) is False

    @pytest.mark.asyncio
    async def test_broadcast(self, manager, mock_connection):
        """测试广播功能"""
        await manager.subscribe(mock_connection, levels=["INFO"])

        entry = LogEntry(
            timestamp="2026-02-18 10:30:45",
            level="INFO",
            logger="test",
            message="Test message"
        )

        await manager.broadcast(entry)

        # 验证消息已发送
        mock_connection.send.assert_called_once()
        call_args = mock_connection.send.call_args[0][0]
        assert call_args["type"] == "log"
        assert call_args["message"] == "Test message"

    @pytest.mark.asyncio
    async def test_broadcast_skips_inactive_connections(self, manager, mock_connection):
        """测试跳过非活跃连接"""
        await manager.subscribe(mock_connection, levels=["INFO"])
        mock_connection.is_alive = False

        entry = LogEntry(
            timestamp="2026-02-18 10:30:45",
            level="INFO",
            logger="test",
            message="Test message"
        )

        await manager.broadcast(entry)

        # 验证消息未发送到非活跃连接
        mock_connection.send.assert_not_called()
        # 验证连接已被清理
        assert mock_connection.connection_id not in manager._subscriptions


class TestWebSocketLogHandler:
    """测试 WebSocket 日志处理器"""

    @pytest.fixture
    def handler(self):
        return WebSocketLogHandler()

    def test_handler_creation(self, handler):
        """测试处理器创建"""
        assert handler.buffer is not None
        assert handler.subscription_manager is not None

    def test_format_time(self, handler):
        """测试时间格式化"""
        timestamp = datetime(2026, 2, 18, 10, 30, 45).timestamp()
        formatted = handler.format_time(timestamp)
        assert formatted == "2026-02-18 10:30:45"

    @pytest.mark.asyncio
    async def test_emit(self, handler):
        """测试日志发射"""
        # 创建模拟的日志记录
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.created = datetime(2026, 2, 18, 10, 30, 45).timestamp()

        # 发射日志
        handler.emit(record)

        # 等待异步操作完成
        await asyncio.sleep(0.1)

        # 验证日志已添加到缓冲区
        logs = await handler.buffer.get_recent(count=10)
        assert len(logs) == 1
        assert logs[0].message == "Test message"
        assert logs[0].level == "INFO"


class TestSingleton:
    """测试单例模式"""

    def test_get_websocket_log_handler_singleton(self):
        """测试 WebSocketLogHandler 单例"""
        handler1 = get_websocket_log_handler()
        handler2 = get_websocket_log_handler()
        assert handler1 is handler2


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_log_flow(self):
        """测试完整的日志流程"""
        handler = get_websocket_log_handler()

        # 创建模拟连接
        mock_conn = Mock()
        mock_conn.connection_id = "integration_test"
        mock_conn.is_alive = True
        mock_conn.send = AsyncMock()

        # 订阅日志
        await handler.subscription_manager.subscribe(
            mock_conn,
            levels=["INFO", "ERROR"]
        )

        # 创建并发射日志记录
        record = logging.LogRecord(
            name="integration",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Integration test message",
            args=(),
            exc_info=None
        )
        record.created = datetime.now().timestamp()

        handler.emit(record)

        # 等待异步操作
        await asyncio.sleep(0.2)

        # 验证日志在缓冲区中
        logs = await handler.buffer.get_recent(count=10)
        assert any(log.message == "Integration test message" for log in logs)

        # 清理
        await handler.subscription_manager.unsubscribe(mock_conn)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
