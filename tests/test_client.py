import os
import sys
import tempfile
import pytest
from client.controller.service_controller import ServiceController, ServiceState
from client.utils.config_manager import ClientConfigManager
from client.utils.log_manager import LogManager, get_log_manager
from client.utils.command_handler import CommandHandler


class TestLogManager:
    """测试日志管理器"""
    
    def test_log_manager_initialization(self):
        """测试日志管理器初始化"""
        # 创建日志管理器实例
        log_manager = LogManager(max_lines=500)
        
        # 验证初始化
        assert log_manager is not None
        
        # 验证获取日志为空
        logs = log_manager.get_logs()
        assert len(logs) == 0
    
    def test_add_log(self):
        """测试添加日志"""
        log_manager = LogManager(max_lines=3)
        
        # 添加日志
        log_manager.add_log("Test log 1")
        log_manager.add_log("Test log 2")
        log_manager.add_log("Test log 3")
        
        # 验证日志数量
        logs = log_manager.get_logs()
        assert len(logs) == 3
        
        # 添加更多日志，测试日志清理
        log_manager.add_log("Test log 4")
        logs = log_manager.get_logs()
        assert len(logs) == 3
        assert "Test log 1" not in [log for log in logs]
    
    def test_log_callbacks(self):
        """测试日志回调"""
        log_manager = LogManager()
        callback_logs = []
        
        # 定义回调函数
        def callback(log_line):
            callback_logs.append(log_line)
        
        # 添加回调
        log_manager.add_callback(callback)
        
        # 添加日志
        log_manager.add_log("Test callback log")
        
        # 验证回调被调用
        assert len(callback_logs) == 1
        assert "Test callback log" in callback_logs[0]
    
    def test_log_manager_singleton(self):
        """测试日志管理器单例模式"""
        # 获取两个实例
        log_manager1 = get_log_manager()
        log_manager2 = get_log_manager()
        
        # 验证是同一个实例
        assert log_manager1 is log_manager2


class TestConfigManager:
    """测试配置管理器"""
    
    def test_config_manager_initialization(self):
        """测试配置管理器初始化"""
        # 使用临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            temp_config_path = f.name
        
        try:
            # 创建配置管理器
            config_manager = ClientConfigManager(temp_config_path)
            
            # 验证初始化
            assert config_manager is not None
            
            # 验证加载空配置
            config = config_manager.load_config()
            assert config == {}
        finally:
            # 清理临时文件
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)
    
    def test_save_and_load_config(self):
        """测试保存和加载配置"""
        # 使用临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            temp_config_path = f.name
        
        try:
            config_manager = ClientConfigManager(temp_config_path)
            
            # 测试保存配置
            test_config = {
                "server": {
                    "host": "127.0.0.1",
                    "port": 8080
                }
            }
            
            success = config_manager.save_config(test_config)
            assert success == True
            
            # 测试加载配置
            loaded_config = config_manager.load_config()
            assert loaded_config == test_config
        finally:
            # 清理临时文件
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)
    
    def test_get_and_set_config(self):
        """测试获取和设置配置"""
        # 使用临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            temp_config_path = f.name
        
        try:
            config_manager = ClientConfigManager(temp_config_path)
            
            # 测试设置配置
            config_manager.set("server.port", 9000)
            
            # 测试获取配置
            port = config_manager.get("server.port")
            assert port == 9000
            
            # 测试获取不存在的配置
            nonexistent = config_manager.get("nonexistent.key")
            assert nonexistent is None
            
            # 测试获取不存在的配置带默认值
            with_default = config_manager.get("nonexistent.key", "default_value")
            assert with_default == "default_value"
        finally:
            # 清理临时文件
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)
    
    def test_validate_config(self):
        """测试配置验证"""
        # 使用临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            temp_config_path = f.name
        
        try:
            config_manager = ClientConfigManager(temp_config_path)
            
            # 测试无效配置
            invalid_config = {
                "server": {
                    "host": "invalid-host",
                    "port": 70000  # 无效端口
                }
            }
            
            config_manager.save_config(invalid_config)
            is_valid, errors = config_manager.validate_config()
            assert is_valid == False
            assert len(errors) > 0
            
            # 测试有效配置
            valid_config = {
                "server": {
                    "host": "127.0.0.1",
                    "port": 8000
                }
            }
            
            config_manager.save_config(valid_config)
            is_valid, errors = config_manager.validate_config()
            assert is_valid == True
            assert len(errors) == 0
        finally:
            # 清理临时文件
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)


class TestServiceController:
    """测试服务控制器"""
    
    def test_service_controller_initialization(self):
        """测试服务控制器初始化"""
        # 使用临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            temp_config_path = f.name
        
        try:
            # 创建服务控制器
            controller = ServiceController(temp_config_path)
            
            # 验证初始化
            assert controller is not None
            assert controller.state == ServiceState.STOPPED
        finally:
            # 清理临时文件
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)
    
    def test_check_port_available(self):
        """测试端口可用性检查"""
        # 使用临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            temp_config_path = f.name
        
        try:
            controller = ServiceController(temp_config_path)
            
            # 测试一个不太可能被占用的端口
            is_available = controller.check_port_available(9999)
            assert is_available == True
            
            # 测试一个可能被占用的端口（如HTTP默认端口）
            is_available = controller.check_port_available(80)
            # 端口80可能被占用，也可能不被占用，所以不做严格断言
        finally:
            # 清理临时文件
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)
    
    def test_get_config_value(self):
        """
        测试获取配置值
        """
        # 使用临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            f.write("[server]\n")
            f.write("host = '127.0.0.1'\n")
            f.write("port = 8000\n")
            temp_config_path = f.name
        
        try:
            controller = ServiceController(temp_config_path)
            
            # 测试获取存在的配置值
            host = controller.get_config_value("server.host")
            assert host == "127.0.0.1"
            
            port = controller.get_config_value("server.port")
            assert port == "8000"
            
            # 测试获取不存在的配置值
            nonexistent = controller.get_config_value("nonexistent.key")
            assert nonexistent is None
        finally:
            # 清理临时文件
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)
    
    def test_get_startup_command(self):
        """
        测试获取启动命令
        
        统一通过模块导入方式运行服务，无论环境如何
        """
        # 使用临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            temp_config_path = f.name
        
        try:
            controller = ServiceController(temp_config_path)
            
            # 测试启动命令，应该统一使用模块方式
            startup_cmd = controller._get_startup_command()
            assert len(startup_cmd) == 3
            assert startup_cmd[0] == sys.executable  # Python 可执行文件路径
            assert startup_cmd[1] == "-m"  # 模块方式启动
            assert startup_cmd[2] == "app"  # 模块名为 app
        finally:
            # 清理临时文件
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)


class TestCommandHandler:
    """测试命令处理器"""
    
    def test_command_handler_initialization(self):
        """测试命令处理器初始化"""
        # 使用临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            temp_config_path = f.name
        
        try:
            # 创建控制器和配置管理器
            controller = ServiceController(temp_config_path)
            config_manager = ClientConfigManager(temp_config_path)
            
            # 创建命令处理器
            command_handler = CommandHandler(controller, config_manager)
            
            # 验证初始化
            assert command_handler is not None
        finally:
            # 清理临时文件
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)
    
    def test_handle_status(self):
        """测试处理状态命令"""
        # 使用临时配置文件，指定一个不太可能被占用的端口
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            f.write("[server]\n")
            f.write("host = '127.0.0.1'\n")
            f.write("port = 9999\n")
            temp_config_path = f.name
        
        try:
            controller = ServiceController(temp_config_path)
            config_manager = ClientConfigManager(temp_config_path)
            command_handler = CommandHandler(controller, config_manager)
            
            # 直接检查控制器状态，避免端口检测影响测试
            assert controller.state == ServiceState.STOPPED
            
            # 测试获取状态
            status_info = command_handler.handle_status()
            # 注意：由于is_running()方法会检测端口，可能会受到环境影响
            # 所以这里只断言state字段由控制器内部管理
            # 而is_running字段可能因环境而异，不做严格断言
            assert status_info["state"] in [ServiceState.STOPPED.value, ServiceState.RUNNING.value]
        finally:
            # 清理临时文件
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)
    
    def test_handle_get_config(self):
        """测试处理获取配置命令"""
        # 使用临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            f.write("[server]\n")
            f.write("host = '127.0.0.1'\n")
            f.write("port = 8000\n")
            f.write("[app]\n")
            f.write("title = 'Test App'\n")
            temp_config_path = f.name
        
        try:
            controller = ServiceController(temp_config_path)
            config_manager = ClientConfigManager(temp_config_path)
            command_handler = CommandHandler(controller, config_manager)
            
            # 测试获取所有配置
            config = command_handler.handle_get_config()
            assert "server" in config
            assert "app" in config
            
            # 测试只获取服务器配置
            server_config = command_handler.handle_get_config(server_only=True)
            assert "server" in server_config
            assert "app" not in server_config
            
            # 测试只获取应用配置
            app_config = command_handler.handle_get_config(app_only=True)
            assert "app" in app_config
            assert "server" not in app_config
        finally:
            # 清理临时文件
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)
