"""
PID文件管理器测试

测试PID文件管理功能
"""
import os
import pytest
from unittest.mock import patch

from utils.port_utils import PidFileManager, get_pid_manager


class TestPidFileManager:
    """测试PID文件管理器"""

    @pytest.fixture
    def pid_manager(self, tmp_path):
        """创建临时PID管理器"""
        pid_file = tmp_path / "test.pid"
        return PidFileManager(str(pid_file))

    def test_write_pid(self, pid_manager):
        """测试写入PID"""
        current_pid = os.getpid()
        pid_file = pid_manager.write_pid()

        assert pid_file.exists()
        assert pid_file.read_text() == str(current_pid)

    def test_write_pid_custom(self, pid_manager):
        """测试写入自定义PID"""
        custom_pid = 12345
        pid_file = pid_manager.write_pid(custom_pid)

        assert pid_file.exists()
        assert pid_file.read_text() == str(custom_pid)

    def test_write_pid_overwrite(self, pid_manager):
        """测试PID文件覆盖写入"""
        pid_manager.write_pid(11111)
        pid_manager.write_pid(22222)

        assert pid_manager.read_pid() == 22222

    def test_read_pid(self, pid_manager):
        """测试读取PID"""
        pid_manager.write_pid(12345)
        assert pid_manager.read_pid() == 12345

    def test_read_pid_not_exists(self, pid_manager):
        """测试读取不存在的PID文件"""
        assert pid_manager.read_pid() is None

    def test_read_pid_invalid(self, pid_manager):
        """测试读取无效的PID文件"""
        pid_manager.pid_file.write_text("invalid")
        assert pid_manager.read_pid() is None

    def test_is_process_running_current(self, pid_manager):
        """测试检查当前进程是否运行中"""
        pid_manager.write_pid()
        assert pid_manager.is_process_running() is True

    def test_is_process_running_not_exists(self, pid_manager):
        """测试检查不存在的PID文件"""
        assert pid_manager.is_process_running() is False

    def test_is_process_running_dead_process(self, pid_manager):
        """测试检查已终止的进程"""
        import psutil
        # 写入一个不可能存在的PID
        pid_manager.write_pid(99999)

        with patch('psutil.Process') as mock_process:
            mock_process.side_effect = psutil.NoSuchProcess(99999)
            assert pid_manager.is_process_running() is False

    def test_get_pid_manager_default(self):
        """测试获取默认PID管理器"""
        manager = get_pid_manager()
        assert isinstance(manager, PidFileManager)
        assert manager.pid_file.name == "langit.pid"

    def test_get_pid_manager_custom(self):
        """测试获取自定义PID管理器"""
        manager = get_pid_manager("custom.pid")
        assert isinstance(manager, PidFileManager)
        assert manager.pid_file.name == "custom.pid"


class TestPidFileManagerIntegration:
    """PID管理器集成测试"""

    def test_full_lifecycle(self, tmp_path):
        """测试完整的生命周期"""
        pid_file = tmp_path / "lifecycle.pid"
        manager = PidFileManager(str(pid_file))

        # 1. 初始状态：文件不存在
        assert not manager.pid_file.exists()
        assert manager.read_pid() is None

        # 2. 写入PID
        manager.write_pid(12345)
        assert manager.pid_file.exists()
        assert manager.read_pid() == 12345

        # 3. 覆盖写入新PID
        manager.write_pid(67890)
        assert manager.read_pid() == 67890

        # 4. 验证进程检查（当前进程）
        manager.write_pid()
        assert manager.is_process_running() is True
