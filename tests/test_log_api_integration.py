"""
日志接口集成测试

测试日志 API 端点的响应是否正确
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from app import create_app
from utils.logging import LogManager, init_logging, get_log_info, read_log_file


class TestLogAPIIntegration:
    """日志接口集成测试"""

    @pytest.fixture(autouse=True)
    def reset_log_manager(self):
        """重置日志管理器单例"""
        import utils.logging as logging_module
        logging_module._log_manager = None
        yield
        logging_module._log_manager = None

    @pytest.fixture
    def temp_log_dir(self):
        """创建临时日志目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def client(self, temp_log_dir, monkeypatch):
        """创建测试客户端（带本地认证）"""
        # 设置本地认证环境变量
        os.environ["LANGIT_LOCAL_TOKEN"] = "test-local-token"

        # 修改默认日志目录为临时目录
        monkeypatch.setattr(LogManager, "DEFAULT_LOG_DIR", temp_log_dir)

        # 初始化日志系统
        init_logging(
            log_dir=temp_log_dir,
            app_name="test_api",
            level="debug",
            use_date_directory=True,
            separate_error_log=True,
            websocket_output=False  # 禁用 WebSocket 避免事件循环问题
        )

        # 创建应用
        app = create_app()

        # 创建测试客户端
        with TestClient(app) as client:
            # 设置本地认证请求头
            client.headers.update({
                "Authorization": "Bearer test-local-token",
                "X-LanGit-Local": "1"
            })
            yield client

        # 清理环境变量
        if "LANGIT_LOCAL_TOKEN" in os.environ:
            del os.environ["LANGIT_LOCAL_TOKEN"]

    def test_get_log_info_endpoint(self, client, temp_log_dir):
        """测试获取日志信息接口"""
        # 创建一些日志文件
        today = datetime.now().strftime("%Y-%m-%d")
        today_dir = Path(temp_log_dir) / today
        today_dir.mkdir(parents=True, exist_ok=True)

        # 创建测试日志文件
        (today_dir / "test_api.log").write_text("Test log content\n")
        (today_dir / "error.log").write_text("Error log content\n")

        # 调用接口
        response = client.get("/api/app/logs")

        # 验证响应
        assert response.status_code == 200, f"响应错误: {response.text}"
        data = response.json()

        # 验证返回的数据结构
        assert "log_dir" in data
        assert "today_dir" in data
        assert "today_files" in data
        assert "available_dates" in data

        # 验证数据内容（log_dir 应该等于 LogManager.DEFAULT_LOG_DIR）
        assert data["log_dir"] == temp_log_dir
        assert today in data["today_dir"]
        assert len(data["today_files"]) >= 2
        assert today in data["available_dates"]

    def test_get_log_content_endpoint(self, client, temp_log_dir):
        """测试获取日志内容接口"""
        # 创建测试日志文件
        today = datetime.now().strftime("%Y-%m-%d")
        today_dir = Path(temp_log_dir) / today
        today_dir.mkdir(parents=True, exist_ok=True)

        # 写入测试日志内容
        log_content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        (today_dir / "test_api.log").write_text(log_content)

        # 调用接口
        response = client.get("/api/app/logs/content?log_name=test_api&lines=3")

        # 验证响应
        assert response.status_code == 200, f"响应错误: {response.text}"
        data = response.json()

        # 验证返回的数据结构
        assert "date" in data
        assert "log_name" in data
        assert "lines" in data
        assert "total_lines" in data
        assert "content" in data
        assert "exists" in data

        # 验证数据内容
        assert data["exists"] is True
        assert data["log_name"] == "test_api"
        assert data["lines"] == 3
        assert data["total_lines"] == 5
        assert "Line 3" in data["content"]
        assert "Line 5" in data["content"]

    def test_get_log_content_with_level_filter(self, client, temp_log_dir):
        """测试带级别过滤的日志内容接口"""
        # 创建测试日志文件
        today = datetime.now().strftime("%Y-%m-%d")
        today_dir = Path(temp_log_dir) / today
        today_dir.mkdir(parents=True, exist_ok=True)

        # 写入不同级别的日志
        log_content = """DEBUG - Debug message
INFO - Info message
WARNING - Warning message
ERROR - Error message
"""
        (today_dir / "test_api.log").write_text(log_content)

        # 调用接口，过滤 ERROR 级别
        response = client.get("/api/app/logs/content?log_name=test_api&level=error")

        # 验证响应
        assert response.status_code == 200, f"响应错误: {response.text}"
        data = response.json()

        # 验证只返回 ERROR 级别的日志
        assert "ERROR" in data["content"]
        assert "Debug message" not in data["content"]
        assert "Info message" not in data["content"]

    def test_get_log_content_not_found(self, client, temp_log_dir):
        """测试获取不存在的日志文件"""
        response = client.get("/api/app/logs/content?log_name=nonexistent&date=2020-01-01")

        # 验证响应
        assert response.status_code == 200, f"响应错误: {response.text}"
        data = response.json()

        assert data["exists"] is False
        assert data["lines"] == 0
        assert data["total_lines"] == 0
        assert data["content"] == ""

    def test_cleanup_logs_endpoint(self, client, temp_log_dir):
        """测试清理日志接口"""
        # 创建旧日志目录（40天前）
        old_date = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
        old_dir = Path(temp_log_dir) / old_date
        old_dir.mkdir(parents=True)
        (old_dir / "old.log").write_text("Old log content")

        # 创建新日志目录
        today = datetime.now().strftime("%Y-%m-%d")
        today_dir = Path(temp_log_dir) / today
        today_dir.mkdir(parents=True)
        (today_dir / "new.log").write_text("New log content")

        # 调用清理接口
        response = client.post("/api/app/logs/cleanup?keep_days=30")

        # 验证响应
        assert response.status_code == 200, f"响应错误: {response.text}"
        data = response.json()

        assert data["success"] is True
        assert data["deleted_count"] == 1
        assert data["keep_days"] == 30

        # 验证旧目录被删除，新目录保留
        assert not old_dir.exists()
        assert today_dir.exists()

    def test_log_api_with_real_logs(self, client, temp_log_dir):
        """测试使用真实日志记录后的接口响应"""
        from utils.logging import get_logger

        # 获取日志记录器并写入日志
        logger = get_logger("test_real")
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")

        # 刷新处理器确保写入磁盘
        for handler in logger.handlers:
            handler.flush()

        # 调用日志信息接口
        response = client.get("/api/app/logs")
        assert response.status_code == 200, f"响应错误: {response.text}"
        data = response.json()

        # 验证日志文件被检测到
        assert len(data["today_files"]) >= 1

        # 调用日志内容接口
        today = datetime.now().strftime("%Y-%m-%d")
        response = client.get(f"/api/app/logs/content?log_name=test_real&lines=10&date={today}")
        assert response.status_code == 200, f"响应错误: {response.text}"
        data = response.json()

        # 验证日志内容
        if data["exists"]:
            assert "Test info message" in data["content"]


class TestLogServiceFunctions:
    """测试日志服务功能函数"""

    @pytest.fixture
    def temp_log_dir(self):
        """创建临时日志目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    def test_get_log_info_function(self, temp_log_dir):
        """测试 get_log_info 函数"""
        # 创建测试日志文件
        today = datetime.now().strftime("%Y-%m-%d")
        today_dir = Path(temp_log_dir) / today
        today_dir.mkdir(parents=True)
        (today_dir / "app.log").write_text("Test content")

        # 调用函数
        info = get_log_info(log_dir=temp_log_dir)

        # 验证结果
        assert info["log_dir"] == temp_log_dir
        assert today in info["today_dir"]
        assert len(info["files"]) == 1
        assert today in info["available_dates"]

    def test_read_log_file_function(self, temp_log_dir):
        """测试 read_log_file 函数"""
        # 创建测试日志文件
        today = datetime.now().strftime("%Y-%m-%d")
        today_dir = Path(temp_log_dir) / today
        today_dir.mkdir(parents=True)

        # 写入多行日志
        content = "\n".join([f"Line {i}" for i in range(1, 11)]) + "\n"
        (today_dir / "test.log").write_text(content)

        # 读取最后 5 行
        lines = read_log_file(
            date=today,
            filename="test.log",
            lines=5,
            log_dir=temp_log_dir
        )

        # 验证结果
        assert len(lines) == 5
        assert "Line 6" in lines[0]
        assert "Line 10" in lines[4]

    def test_read_log_file_not_exist(self, temp_log_dir):
        """测试读取不存在的日志文件"""
        lines = read_log_file(
            date="2020-01-01",
            filename="nonexistent.log",
            lines=10,
            log_dir=temp_log_dir
        )

        assert lines == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
