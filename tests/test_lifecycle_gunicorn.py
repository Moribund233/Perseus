"""
生命周期管理和Gunicorn集成测试

测试内容：
1. IPC管理器基本功能
2. 生命周期管理器多进程模式
3. 优雅关闭流程

运行方式:
    pytest tests/test_lifecycle_gunicorn.py -v
    
或:
    python -m pytest tests/test_lifecycle_gunicorn.py -v
"""
import os
import sys
import time
import json
import signal
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest


class TestIPCManager:
    """IPC管理器测试"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        from utils.ipc_manager import reset_ipc_manager
        reset_ipc_manager()
        
        # 创建临时目录用于IPC文件
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """每个测试方法后执行"""
        from utils.ipc_manager import reset_ipc_manager
        reset_ipc_manager()
        
        # 清理临时目录
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_ipc_manager_singleton(self):
        """测试IPC管理器单例模式"""
        from utils.ipc_manager import get_ipc_manager
        
        manager1 = get_ipc_manager(self.temp_dir)
        manager2 = get_ipc_manager(self.temp_dir)
        
        assert manager1 is manager2
    
    def test_master_initialization(self):
        """测试Master进程初始化"""
        from utils.ipc_manager import get_ipc_manager
        
        manager = get_ipc_manager(self.temp_dir)
        master_pid = os.getpid()
        
        manager.initialize_master(master_pid)
        
        assert manager._master_pid == master_pid
        assert not manager._is_worker
        assert manager._status_file.exists()
    
    def test_worker_initialization(self):
        """测试Worker进程初始化"""
        from utils.ipc_manager import get_ipc_manager
        
        manager = get_ipc_manager(self.temp_dir)
        master_pid = os.getpid()
        worker_id = 1
        
        # 先初始化master
        manager.initialize_master(master_pid)
        
        # 再初始化worker
        manager.initialize_worker(worker_id, master_pid)
        
        assert manager._is_worker
        assert manager._worker_id == worker_id
        assert manager._master_pid == master_pid
    
    def test_shutdown_request(self):
        """测试关闭请求"""
        from utils.ipc_manager import get_ipc_manager
        
        manager = get_ipc_manager(self.temp_dir)
        master_pid = os.getpid()
        
        manager.initialize_master(master_pid)
        
        # 请求关闭
        result = manager.request_shutdown("test")
        
        assert result is True
        assert manager.is_shutdown_requested()
        assert manager._shutdown_file.exists()
    
    def test_shutdown_callback(self):
        """测试关闭回调"""
        from utils.ipc_manager import get_ipc_manager
        
        manager = get_ipc_manager(self.temp_dir)
        callback_called = threading.Event()
        
        def test_callback():
            callback_called.set()
        
        manager.register_shutdown_callback(test_callback)
        
        # 验证回调已注册
        assert test_callback in manager._shutdown_callbacks
    
    def test_status_read_write(self):
        """测试状态读写"""
        from utils.ipc_manager import get_ipc_manager
        
        manager = get_ipc_manager(self.temp_dir)
        master_pid = os.getpid()
        
        manager.initialize_master(master_pid)
        
        status = manager.get_status()
        
        assert "master_pid" in status
        assert status["master_pid"] == master_pid
        assert status["status"] == "running"


class TestLifecycleManager:
    """生命周期管理器测试"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        from core.lifespan import reset_lifecycle_manager
        from utils.ipc_manager import reset_ipc_manager
        
        reset_lifecycle_manager()
        reset_ipc_manager()
        
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """每个测试方法后执行"""
        from core.lifespan import reset_lifecycle_manager
        from utils.ipc_manager import reset_ipc_manager
        
        reset_lifecycle_manager()
        reset_ipc_manager()
        
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_lifecycle_manager_singleton(self):
        """测试生命周期管理器单例模式"""
        from core.lifespan import get_lifecycle_manager
        
        manager1 = get_lifecycle_manager()
        manager2 = get_lifecycle_manager()
        
        assert manager1 is manager2
    
    def test_master_mode_setup(self):
        """测试Master模式设置"""
        from core.lifespan import get_lifecycle_manager
        from utils.ipc_manager import get_ipc_manager
        
        lifecycle_manager = get_lifecycle_manager()
        master_pid = os.getpid()
        
        lifecycle_manager.setup_for_master(master_pid)
        
        assert lifecycle_manager._ipc_manager is not None
        assert lifecycle_manager._ipc_manager._master_pid == master_pid
    
    def test_worker_mode_setup(self):
        """测试Worker模式设置"""
        from core.lifespan import get_lifecycle_manager
        
        lifecycle_manager = get_lifecycle_manager()
        master_pid = os.getpid()
        worker_id = 1
        
        # 先设置master
        lifecycle_manager.setup_for_master(master_pid)
        
        # 再设置worker
        lifecycle_manager.setup_for_worker(worker_id, master_pid)
        
        assert lifecycle_manager._is_worker
        assert lifecycle_manager._worker_id == worker_id
        assert lifecycle_manager._ipc_manager is not None
    
    def test_shutdown_request_single_process(self):
        """测试单进程模式关闭请求"""
        from core.lifespan import get_lifecycle_manager
        
        lifecycle_manager = get_lifecycle_manager()
        
        # 单进程模式下直接返回True（异步执行）
        result = lifecycle_manager.request_graceful_shutdown("test")
        
        assert result is True
    
    def test_shutdown_request_multi_process(self):
        """测试多进程模式关闭请求"""
        from core.lifespan import get_lifecycle_manager
        
        lifecycle_manager = get_lifecycle_manager()
        master_pid = os.getpid()
        
        # 设置为Master模式
        lifecycle_manager.setup_for_master(master_pid)
        
        # 多进程模式下通过IPC发送关闭请求
        result = lifecycle_manager.request_graceful_shutdown("test")
        
        assert result is True
        assert lifecycle_manager._ipc_manager.is_shutdown_requested()


class TestGunicornIntegration:
    """Gunicorn集成测试"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        from core.lifespan import reset_lifecycle_manager
        from utils.ipc_manager import reset_ipc_manager
        
        reset_lifecycle_manager()
        reset_ipc_manager()
    
    def teardown_method(self):
        """每个测试方法后执行"""
        from core.lifespan import reset_lifecycle_manager
        from utils.ipc_manager import reset_ipc_manager
        
        reset_lifecycle_manager()
        reset_ipc_manager()
    
    def test_gunicorn_worker_import(self):
        """测试Gunicorn Worker导入"""
        try:
            from core.gunicorn_worker import LanGitUvicornWorker
            assert LanGitUvicornWorker is not None
        except ImportError as e:
            pytest.skip(f"Gunicorn Worker导入失败: {e}")
    
    def test_gunicorn_config_import(self):
        """测试Gunicorn配置导入"""
        try:
            import core.gunicorn.conf as gunicorn_config
            assert hasattr(gunicorn_config, 'bind')
            assert hasattr(gunicorn_config, 'workers')
            assert hasattr(gunicorn_config, 'worker_class')
        except ImportError as e:
            pytest.skip(f"Gunicorn配置导入失败: {e}")
    
    @pytest.mark.asyncio
    async def test_lifespan_context_manager(self):
        """测试lifespan上下文管理器"""
        from core.lifespan import app_lifespan
        from fastapi import FastAPI
        
        app = FastAPI()
        
        async with app_lifespan(app) as state:
            assert "lifecycle_manager" in state
            assert state["lifecycle_manager"] is not None


class TestShutdownAPI:
    """关闭API测试"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        from core.lifespan import reset_lifecycle_manager
        from utils.ipc_manager import reset_ipc_manager
        
        reset_lifecycle_manager()
        reset_ipc_manager()
    
    def teardown_method(self):
        """每个测试方法后执行"""
        from core.lifespan import reset_lifecycle_manager
        from utils.ipc_manager import reset_ipc_manager
        
        reset_lifecycle_manager()
        reset_ipc_manager()
    
    def test_trigger_graceful_shutdown_function(self):
        """测试trigger_graceful_shutdown函数"""
        from core.lifespan import trigger_graceful_shutdown, get_lifecycle_manager
        
        # 单进程模式下应该返回True
        result = trigger_graceful_shutdown("test")
        assert result is True
    
    def test_is_shutdown_requested_function(self):
        """测试is_shutdown_requested函数"""
        from core.lifespan import is_shutdown_requested, get_lifecycle_manager
        
        # 初始状态应该为False
        assert is_shutdown_requested() is False
        
        # 请求关闭后应该为True
        manager = get_lifecycle_manager()
        manager.setup_for_master(os.getpid())
        manager.request_graceful_shutdown("test")
        
        assert is_shutdown_requested() is True


class TestAppServiceIntegration:
    """AppService集成测试"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        from core.lifespan import reset_lifecycle_manager
        from utils.ipc_manager import reset_ipc_manager
        
        reset_lifecycle_manager()
        reset_ipc_manager()
    
    def teardown_method(self):
        """每个测试方法后执行"""
        from core.lifespan import reset_lifecycle_manager
        from utils.ipc_manager import reset_ipc_manager
        
        reset_lifecycle_manager()
        reset_ipc_manager()
    
    def test_app_service_shutdown(self):
        """测试AppService关闭功能"""
        from services.app_service import AppService
        
        service = AppService()
        
        # 调试模式下应该成功
        result = service.shutdown(is_debug=True, is_admin=False)
        
        assert result is True
    
    def test_app_service_shutdown_no_permission(self):
        """测试AppService关闭权限检查"""
        from services.app_service import AppService
        from core.exception import AuthorizationException
        
        service = AppService()
        
        # 非调试模式且非管理员应该抛出异常
        with pytest.raises(AuthorizationException):
            service.shutdown(is_debug=False, is_admin=False)


# ==================== 手动测试脚本 ====================

def manual_test_ipc():
    """
    手动测试IPC功能
    
    运行方式:
        python tests/test_lifecycle_gunicorn.py ipc
    """
    print("=" * 60)
    print("IPC管理器手动测试")
    print("=" * 60)
    
    from utils.ipc_manager import get_ipc_manager, reset_ipc_manager
    
    reset_ipc_manager()
    temp_dir = tempfile.mkdtemp()
    
    try:
        manager = get_ipc_manager(temp_dir)
        master_pid = os.getpid()
        
        print(f"\n1. 初始化Master进程 (PID: {master_pid})")
        manager.initialize_master(master_pid)
        print("   ✓ Master初始化成功")
        
        print(f"\n2. 检查状态文件")
        status = manager.get_status()
        print(f"   Master PID: {status.get('master_pid')}")
        print(f"   状态: {status.get('status')}")
        print("   ✓ 状态读取成功")
        
        print(f"\n3. 模拟Worker初始化")
        worker_id = 1
        manager.initialize_worker(worker_id, master_pid)
        print(f"   Worker ID: {worker_id}")
        print("   ✓ Worker初始化成功")
        
        print(f"\n4. 发送关闭请求")
        result = manager.request_shutdown("manual_test")
        print(f"   结果: {result}")
        print(f"   关闭标志: {manager.is_shutdown_requested()}")
        print("   ✓ 关闭请求发送成功")
        
        print(f"\n5. 读取关闭信息")
        if manager._shutdown_file.exists():
            with open(manager._shutdown_file, 'r') as f:
                shutdown_info = json.load(f)
            print(f"   关闭原因: {shutdown_info.get('reason')}")
            print(f"   请求时间: {shutdown_info.get('requested_at')}")
            print("   ✓ 关闭信息读取成功")
        
        print("\n" + "=" * 60)
        print("IPC测试完成")
        print("=" * 60)
        
    finally:
        manager.cleanup()
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def manual_test_lifecycle():
    """
    手动测试生命周期管理器
    
    运行方式:
        python tests/test_lifecycle_gunicorn.py lifecycle
    """
    print("=" * 60)
    print("生命周期管理器手动测试")
    print("=" * 60)
    
    from core.lifespan import get_lifecycle_manager, reset_lifecycle_manager
    from utils.ipc_manager import reset_ipc_manager
    
    reset_lifecycle_manager()
    reset_ipc_manager()
    
    try:
        manager = get_lifecycle_manager()
        master_pid = os.getpid()
        
        print(f"\n1. 设置Master模式 (PID: {master_pid})")
        manager.setup_for_master(master_pid)
        print("   ✓ Master模式设置成功")
        
        print(f"\n2. 设置Worker模式")
        worker_id = 1
        manager.setup_for_worker(worker_id, master_pid)
        print(f"   Worker ID: {worker_id}")
        print("   ✓ Worker模式设置成功")
        
        print(f"\n3. 请求优雅关闭")
        result = manager.request_graceful_shutdown("manual_test")
        print(f"   结果: {result}")
        print("   ✓ 关闭请求已发送")
        
        print(f"\n4. 检查关闭状态")
        from core.lifespan import is_shutdown_requested
        is_requested = is_shutdown_requested()
        print(f"   关闭已请求: {is_requested}")
        print("   ✓ 状态检查完成")
        
        print("\n" + "=" * 60)
        print("生命周期管理器测试完成")
        print("=" * 60)
        
    finally:
        if manager._ipc_manager:
            manager._ipc_manager.cleanup()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "ipc":
            manual_test_ipc()
        elif command == "lifecycle":
            manual_test_lifecycle()
        else:
            print(f"未知命令: {command}")
            print("可用命令: ipc, lifecycle")
    else:
        # 运行pytest
        pytest.main([__file__, "-v"])
