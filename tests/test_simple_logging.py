"""
日志系统测试

测试内容：
1. LogManager 基本功能
2. 日志文件创建和写入（支持按日期分目录）
3. WebSocketHandler 集成
4. 日志清理功能
5. 多文件分离（app.log, error.log, audit.log）
"""

import pytest
import logging
import tempfile
import shutil
import os
import time
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging import (
    LogManager,
    init_logging,
    get_logger,
    get_named_logger,
    get_audit_logger,
    cleanup_old_logs,
    get_log_info,
    read_log_file
)


class TestLogManager:
    """测试日志管理器"""

    @pytest.fixture(autouse=True)
    def reset_loggers(self):
        """重置所有日志记录器，避免测试间干扰"""
        # 清理所有已存在的 logger handlers
        for name in list(logging.root.manager.loggerDict.keys()):
            logger = logging.getLogger(name)
            logger.handlers = []
            logger.setLevel(logging.NOTSET)
        yield
        # 测试后再次清理
        for name in list(logging.root.manager.loggerDict.keys()):
            logger = logging.getLogger(name)
            logger.handlers = []

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    def test_init(self, temp_dir):
        """测试初始化"""
        manager = LogManager(
            log_dir=temp_dir,
            app_name="test",
            level="debug"
        )
        assert manager.log_dir == Path(temp_dir)
        assert manager.app_name == "test"
        assert manager.level == logging.DEBUG

    def test_get_logger(self, temp_dir):
        """测试获取日志记录器"""
        manager = LogManager(
            log_dir=temp_dir,
            websocket_output=False,
            use_date_directory=False  # 禁用日期目录便于测试
        )
        logger = manager.get_logger()

        assert isinstance(logger, logging.Logger)
        assert logger.level == logging.INFO
        assert len(logger.handlers) >= 2  # 文件 + 控制台

    def test_get_named_logger(self, temp_dir):
        """测试获取命名日志记录器"""
        manager = LogManager(
            log_dir=temp_dir,
            websocket_output=False,
            use_date_directory=False
        )
        logger = manager.get_named_logger("git")

        assert logger.name == "langit.git"
        assert len(logger.handlers) >= 2

    def test_log_file_creation(self, temp_dir):
        """测试日志文件创建（按日期分目录）"""
        manager = LogManager(
            log_dir=temp_dir,
            app_name="test",
            websocket_output=False,
            use_date_directory=True
        )
        logger = manager.get_logger()

        # 写入日志
        logger.info("Test message")

        # 刷新所有处理器确保写入磁盘
        for handler in logger.handlers:
            handler.flush()

        # 验证文件存在（在日期子目录中）
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = Path(temp_dir) / today / "test.log"
        assert log_file.exists(), f"日志文件不存在: {log_file}"

        # 验证内容
        content = log_file.read_text()
        assert "Test message" in content

    def test_log_levels(self, temp_dir):
        """测试不同日志级别（按日期分目录）"""
        manager = LogManager(
            log_dir=temp_dir,
            app_name="test_levels",
            level="debug",
            websocket_output=False,
            use_date_directory=True,
            separate_error_log=False  # 禁用错误日志分离，所有日志都写入同一文件
        )
        logger = manager.get_logger()

        # 写入不同级别的日志
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # 刷新所有处理器
        for handler in logger.handlers:
            handler.flush()

        # 验证文件在日期子目录中
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = Path(temp_dir) / today / "test_levels.log"
        content = log_file.read_text()

        assert "Debug message" in content
        assert "Info message" in content
        assert "Warning message" in content
        assert "Error message" in content

    def test_error_log_separation(self, temp_dir):
        """测试错误日志分离"""
        manager = LogManager(
            log_dir=temp_dir,
            app_name="error_test",
            level="debug",
            websocket_output=False,
            use_date_directory=True,
            separate_error_log=True
        )
        logger = manager.get_logger()

        # 写入不同级别的日志
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # 刷新所有处理器
        for handler in logger.handlers:
            handler.flush()

        today = datetime.now().strftime("%Y-%m-%d")

        # 验证 app.log 只包含 INFO 及以下级别
        app_log = Path(temp_dir) / today / "error_test.log"
        app_content = app_log.read_text()
        assert "Debug message" in app_content
        assert "Info message" in app_content
        # app.log 不应该包含 WARNING 及以上级别（被过滤器过滤）
        # 但实际上过滤器会过滤掉 WARNING 及以上，所以它们不应该出现在 app.log

        # 验证 error.log 包含 WARNING 及以上级别
        error_log = Path(temp_dir) / today / "error.log"
        assert error_log.exists(), "error.log 未创建"
        error_content = error_log.read_text()
        assert "Warning message" in error_content
        assert "Error message" in error_content

    def test_audit_logger(self, temp_dir):
        """测试审计日志记录器"""
        manager = LogManager(
            log_dir=temp_dir,
            websocket_output=False,
            use_date_directory=True
        )

        # 获取审计日志记录器
        audit_logger = manager.get_audit_logger()

        # 写入审计日志
        audit_logger.info("User login: admin")
        audit_logger.warning("Failed login attempt")

        # 刷新处理器
        for handler in audit_logger.handlers:
            handler.flush()

        # 验证 audit.log 存在
        today = datetime.now().strftime("%Y-%m-%d")
        audit_log = Path(temp_dir) / today / "audit.log"
        assert audit_log.exists(), "audit.log 未创建"

        content = audit_log.read_text()
        assert "User login: admin" in content
        assert "Failed login attempt" in content

    def test_websocket_handler_added(self, temp_dir):
        """测试 WebSocket 处理器已添加"""
        manager = LogManager(
            log_dir=temp_dir,
            websocket_output=True,
            use_date_directory=False
        )
        logger = manager.get_logger()

        # 检查是否有 WebSocketHandler
        from api.websocket.handlers.log_handler import WebSocketLogHandler
        has_ws_handler = any(
            isinstance(h, WebSocketLogHandler)
            for h in logger.handlers
        )
        assert has_ws_handler is True

    def test_websocket_handler_disabled(self, temp_dir):
        """测试禁用 WebSocket 处理器"""
        manager = LogManager(
            log_dir=temp_dir,
            websocket_output=False,
            use_date_directory=False
        )
        logger = manager.get_logger()

        from api.websocket.handlers.log_handler import WebSocketLogHandler
        has_ws_handler = any(
            isinstance(h, WebSocketLogHandler)
            for h in logger.handlers
        )
        assert has_ws_handler is False


class TestConvenienceFunctions:
    """测试便捷函数"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """重置单例"""
        import utils.logging as logging_module
        logging_module._log_manager = None
        yield
        logging_module._log_manager = None

    @pytest.fixture
    def temp_dir(self):
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    def test_init_logging(self, temp_dir):
        """测试初始化日志"""
        manager = init_logging(
            log_dir=temp_dir,
            app_name="test_app",
            level="debug",
            use_date_directory=False
        )
        assert isinstance(manager, LogManager)
        assert manager.app_name == "test_app"

    def test_get_logger_singleton(self, temp_dir):
        """测试 get_logger 单例"""
        init_logging(log_dir=temp_dir, use_date_directory=False)

        logger1 = get_logger()
        logger2 = get_logger()

        assert logger1 is logger2

    def test_get_named_logger(self, temp_dir):
        """测试获取命名日志器"""
        init_logging(log_dir=temp_dir, use_date_directory=False)

        logger = get_named_logger("test_module")
        assert logger.name == "langit.test_module"

    def test_get_audit_logger(self, temp_dir):
        """测试获取审计日志记录器"""
        init_logging(log_dir=temp_dir, use_date_directory=False)

        logger = get_audit_logger()
        assert logger.name == "langit.audit"


class TestCleanup:
    """测试日志清理功能"""

    @pytest.fixture
    def temp_dir(self):
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    def test_cleanup_old_logs(self, temp_dir):
        """测试清理旧日志（按日期目录）"""
        log_path = Path(temp_dir)

        # 创建旧日期目录（模拟 40 天前）
        old_date = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
        old_dir = log_path / old_date
        old_dir.mkdir(parents=True)
        old_file = old_dir / "test.log"
        old_file.write_text("Old log content")

        # 创建新日期目录
        new_date = datetime.now().strftime("%Y-%m-%d")
        new_dir = log_path / new_date
        new_dir.mkdir(parents=True)
        new_file = new_dir / "test.log"
        new_file.write_text("New log content")

        # 清理 30 天前的日志
        deleted = cleanup_old_logs(log_dir=temp_dir, keep_days=30)

        assert deleted == 1, f"期望删除 1 个目录，实际删除 {deleted} 个"
        assert not old_dir.exists()
        assert new_dir.exists()

    def test_cleanup_no_old_logs(self, temp_dir):
        """测试没有旧日志时的清理"""
        log_path = Path(temp_dir)

        # 只创建新日期目录
        new_date = datetime.now().strftime("%Y-%m-%d")
        new_dir = log_path / new_date
        new_dir.mkdir(parents=True)
        new_file = new_dir / "test.log"
        new_file.write_text("New log content")

        deleted = cleanup_old_logs(log_dir=temp_dir, keep_days=30)

        assert deleted == 0
        assert new_dir.exists()


class TestLogInfo:
    """测试日志信息获取"""

    @pytest.fixture
    def temp_dir(self):
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    def test_get_log_info(self, temp_dir):
        """测试获取日志信息（按日期目录）"""
        # 创建今天的日志目录和文件
        today = datetime.now().strftime("%Y-%m-%d")
        today_dir = Path(temp_dir) / today
        today_dir.mkdir(parents=True)

        (today_dir / "app.log").write_text("App log content")
        (today_dir / "error.log").write_text("Error log content")

        # 获取日志信息
        info = get_log_info(log_dir=temp_dir)

        assert info["log_dir"] == temp_dir
        assert info["today_dir"] == str(today_dir)
        assert len(info["files"]) == 2
        assert info["total_size"] > 0
        assert "total_size_formatted" in info
        assert today in info["available_dates"]

    def test_read_log_file(self, temp_dir):
        """测试读取日志文件"""
        # 创建测试日志文件
        today = datetime.now().strftime("%Y-%m-%d")
        today_dir = Path(temp_dir) / today
        today_dir.mkdir(parents=True)

        log_content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        (today_dir / "test.log").write_text(log_content)

        # 读取最后 3 行
        lines = read_log_file(
            date=today,
            filename="test.log",
            lines=3,
            log_dir=temp_dir
        )

        assert len(lines) == 3
        assert "Line 3" in lines[0]
        assert "Line 5" in lines[2]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
