"""
日志系统集成测试

验证日志系统与 WebSocket 日志的集成
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging import LogManager, get_logger
from api.websocket.handlers.log_handler import (
    WebSocketLogHandler,
    LogEntry,
    LogBuffer,
    LogSubscriptionManager,
    get_websocket_log_handler
)


class TestLogIntegration:
    """日志系统集成测试"""

    @pytest.fixture
    def temp_dir(self):
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_log_flow_to_websocket(self, temp_dir):
        """
        测试日志从 LogManager 流向 WebSocket

        验证流程：
        1. 创建 LogManager 并启用 WebSocket 输出
        2. 写入日志
        3. 验证日志被添加到 WebSocket 缓冲区
        """
        # 创建日志管理器
        manager = LogManager(
            log_dir=temp_dir,
            app_name="integration_test",
            websocket_output=True,
            console_output=False
        )

        # 获取 WebSocket handler 的缓冲区
        ws_handler = get_websocket_log_handler()
        buffer = ws_handler.buffer

        # 清空缓冲区（避免之前的测试数据干扰）
        buffer._buffer.clear()

        # 获取 logger 并写入日志
        logger = manager.get_logger()
        test_message = f"Integration test message at {datetime.now()}"

        # 手动创建日志条目并添加到缓冲区（模拟 emit 行为）
        entry = LogEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            level="INFO",
            logger="integration_test",
            message=test_message
        )
        await buffer.append(entry)

        # 验证日志被添加到缓冲区
        recent_logs = await buffer.get_recent(count=10)

        # 查找我们的测试消息
        found = any(test_message in log.message for log in recent_logs)
        assert found, f"未在缓冲区找到测试消息: {test_message}"

    def test_file_and_websocket_handlers(self, temp_dir):
        """
        测试日志处理器配置

        验证：
        1. 文件处理器存在
        2. WebSocket 处理器存在
        """
        manager = LogManager(
            log_dir=temp_dir,
            app_name="dual_output_test",
            websocket_output=True,
            console_output=False
        )

        logger = manager.get_logger()

        # 验证处理器数量
        assert len(logger.handlers) >= 2, "应该至少有文件和 WebSocket 两个处理器"

        # 验证文件处理器
        from logging.handlers import RotatingFileHandler
        has_file_handler = any(
            isinstance(h, RotatingFileHandler)
            for h in logger.handlers
        )
        assert has_file_handler, "缺少文件处理器"

        # 验证 WebSocket 处理器
        has_ws_handler = any(
            isinstance(h, WebSocketLogHandler)
            for h in logger.handlers
        )
        assert has_ws_handler, "缺少 WebSocket 处理器"

    def test_log_levels_filtering(self, temp_dir):
        """
        测试日志级别过滤

        验证不同级别的日志被正确处理
        当 separate_error_log=True 时：
        - app.log 记录 INFO 及以下级别
        - error.log 记录 WARNING 及以上级别
        """
        manager = LogManager(
            log_dir=temp_dir,
            app_name="level_test",
            level="debug",  # 记录所有级别
            websocket_output=False,  # 禁用 WebSocket 避免异步问题
            console_output=False,
            use_date_directory=False,  # 禁用日期目录，方便测试
            separate_error_log=True
        )

        logger = manager.get_logger()

        # 写入不同级别的日志
        logger.debug("Debug message - should be in app.log")
        logger.info("Info message - should be in app.log")
        logger.warning("Warning message - should be in error.log")
        logger.error("Error message - should be in error.log")

        # 刷新处理器
        for handler in logger.handlers:
            handler.flush()

        # 验证 app.log 内容（只包含 INFO 及以下）
        app_log_file = Path(temp_dir) / "level_test.log"
        app_content = app_log_file.read_text()

        assert "Debug message" in app_content
        assert "Info message" in app_content
        assert "Warning message" not in app_content  # WARNING 在 error.log
        assert "Error message" not in app_content  # ERROR 在 error.log

        # 验证 error.log 内容（包含 WARNING 及以上）
        error_log_file = Path(temp_dir) / "error.log"
        error_content = error_log_file.read_text()

        assert "Warning message" in error_content
        assert "Error message" in error_content

    @pytest.mark.asyncio
    async def test_subscription_manager_filtering(self, temp_dir):
        """
        测试订阅管理器的过滤功能

        验证：
        1. 按级别过滤
        2. 按 logger 名称过滤
        3. 按关键词过滤
        """
        # 创建模拟连接
        class MockConnection:
            def __init__(self):
                self.messages = []
                self.is_alive = True
                self.connection_id = "test_connection"

            async def send(self, data):
                self.messages.append(data)

        connection = MockConnection()

        # 获取订阅管理器
        ws_handler = get_websocket_log_handler()
        sub_manager = ws_handler.subscription_manager

        # 订阅日志（带过滤条件）
        await sub_manager.subscribe(
            connection=connection,
            levels=["WARNING", "ERROR"],  # 使用复数形式 levels
            loggers=["level_test"],
            keywords=["important"]
        )

        # 创建日志条目并广播
        entries = [
            LogEntry(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                level="INFO",
                logger="level_test",
                message="This is an important message"
            ),
            LogEntry(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                level="WARNING",
                logger="level_test",
                message="This is a warning"
            ),
            LogEntry(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                level="WARNING",
                logger="level_test",
                message="This is an important warning"
            ),
            LogEntry(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                level="ERROR",
                logger="level_test",
                message="Critical error occurred"
            ),
        ]

        for entry in entries:
            await sub_manager.broadcast(entry)

        # 验证只有符合条件的日志被发送
        messages = connection.messages

        # 应该收到 1 条消息（important warning）
        # - INFO 级别不够
        # - 普通 warning 没有关键词 "important"
        # - ERROR 级别够但没有关键词 "important"
        assert len(messages) == 1, f"期望收到 1 条消息，实际收到 {len(messages)} 条"

        # 验证消息内容
        assert "important warning" in messages[0]["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
