import os
import tempfile
from config import ConfigManager, get_config, update_config, reset_module_config_manager
from config import ServerSettings, AppSettings, Config


def test_config_initialization():
    """
    测试配置初始化
    """
    # 使用临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
        temp_config_path = f.name
    
    try:
        # 创建配置管理器
        config_manager = ConfigManager(temp_config_path)
        
        # 获取配置
        config = config_manager.get_config()
        
        # 验证配置类型
        assert isinstance(config, Config)
        assert isinstance(config.server, ServerSettings)
        assert isinstance(config.app, AppSettings)
        
        # 验证默认值
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8000
        assert config.server.reload == False
        assert config.server.workers == 1
        assert config.server.log_level == "info"
        
        assert config.app.title == "LanGit API"
        assert config.app.description == "A Git-based collaborative development tool API"
        assert config.app.version == "0.1.0"
        assert config.app.debug == True
    finally:
        # 清理临时文件
        if os.path.exists(temp_config_path):
            os.unlink(temp_config_path)
        # 重置模块级配置管理器
        reset_module_config_manager()


def test_config_update():
    """
    测试配置更新
    """
    # 使用临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
        temp_config_path = f.name
    
    try:
        # 创建配置管理器
        config_manager = ConfigManager(temp_config_path)
        
        # 更新配置
        new_config = {
            "server": {
                "port": 8080,
                "workers": 2
            },
            "app": {
                "title": "Test API",
                "debug": False
            }
        }
        
        updated_config = config_manager.update_config(new_config)
        
        # 验证更新后的配置
        assert updated_config.server.port == 8080
        assert updated_config.server.workers == 2
        assert updated_config.app.title == "Test API"
        assert updated_config.app.debug == False
        
        # 验证配置持久化
        reloaded_config = config_manager.get_config(force_reload=True)
        assert reloaded_config.server.port == 8080
        assert reloaded_config.server.workers == 2
        assert reloaded_config.app.title == "Test API"
        assert reloaded_config.app.debug == False
    finally:
        # 清理临时文件
        if os.path.exists(temp_config_path):
            os.unlink(temp_config_path)
        # 重置模块级配置管理器
        reset_module_config_manager()


def test_config_validation():
    """
    测试配置验证
    """
    # 使用临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
        temp_config_path = f.name
    
    try:
        # 创建配置管理器
        config_manager = ConfigManager(temp_config_path)
        
        # 尝试更新无效配置（端口超出范围）
        invalid_config = {
            "server": {
                "port": 70000  # 超出端口范围
            }
        }
        
        # 应该抛出异常
        try:
            config_manager.update_config(invalid_config)
            assert False, "应该抛出验证异常"
        except Exception:
            pass
    finally:
        # 清理临时文件
        if os.path.exists(temp_config_path):
            os.unlink(temp_config_path)
        # 重置模块级配置管理器
        reset_module_config_manager()


def test_module_level_functions():
    """
    测试模块级别的便捷函数
    """
    # 使用临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
        temp_config_path = f.name
    
    try:
        # 重置模块级配置管理器
        reset_module_config_manager()
        
        # 测试get_config函数
        config = get_config(config_path=temp_config_path)
        assert isinstance(config, Config)
        
        # 测试update_config函数
        new_config = {
            "app": {
                "title": "Module Test API"
            }
        }
        updated_config = update_config(new_config, config_path=temp_config_path)
        assert updated_config.app.title == "Module Test API"
    finally:
        # 清理临时文件
        if os.path.exists(temp_config_path):
            os.unlink(temp_config_path)
        # 重置模块级配置管理器
        reset_module_config_manager()
