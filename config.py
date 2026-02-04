import os
import toml
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class ServerSettings(BaseSettings):
    """服务器配置类"""
    host: str = Field(default="0.0.0.0", description="服务器监听地址")
    port: int = Field(default=8000, ge=1, le=65535, description="服务器监听端口")  # 添加端口范围验证
    reload: bool = Field(default=False, description="是否启用热重载")
    workers: int = Field(default=1, ge=1, description="服务器工作进程数")  # 添加workers数量验证
    log_level: str = Field(default="info", description="日志级别", pattern="^(debug|info|warning|error|critical)$")  # 添加日志级别验证


class AppSettings(BaseSettings):
    """应用配置类"""
    title: str = Field(default="LanGit API", description="应用标题")
    description: str = Field(default="A Git-based collaborative development tool API", description="应用描述")
    version: str = Field(default="0.1.0", description="应用版本")
    debug: bool = Field(default=True, description="是否启用调试模式")


class SystemSettings(BaseSettings):
    """系统配置类"""
    platform: str = Field(description="操作系统平台")
    python_version: str = Field(description="Python版本")
    python_version_info: Dict[str, Any] = Field(description="Python版本信息")


class Config(BaseSettings):
    """配置主类"""
    server: ServerSettings = ServerSettings()
    app: AppSettings = AppSettings()
    system: Optional[SystemSettings] = Field(default=None, description="系统信息")
    
    class Config:
        extra = 'forbid'  # 严格验证配置，禁止额外的配置项


class ConfigManager:
    """
    配置管理器类，负责配置文件的读取、解析和缓存
    
    功能：
    1. 从config.toml文件读取配置
    2. 提供配置缓存机制，避免重复读取文件
    3. 支持配置的动态更新
    4. 提供配置验证
    """
    
    _instance: Optional['ConfigManager'] = None
    _cache: Optional[Config] = None
    _cache_time: float = 0.0
    _cache_ttl: float = 300.0  # 缓存有效期，单位：秒
    
    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = "config.toml"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为当前目录下的config.toml
        """
        self.config_path = config_path
        self._load_config()
    
    def _load_config(self) -> Config:
        """
        从配置文件加载配置
        
        Returns:
            Config: 配置对象
        """
        config_data: Dict[str, Any] = {}
        
        # 如果配置文件存在，读取配置
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = toml.load(f)
        
        # 验证并创建配置对象
        config = Config(**config_data)
        
        # 更新缓存
        self._cache = config
        self._cache_time = os.path.getmtime(self.config_path) if os.path.exists(self.config_path) else 0.0
        
        return config
    
    def get_config(self, force_reload: bool = False) -> Config:
        """
        获取配置对象，支持缓存机制
        
        Args:
            force_reload: 是否强制重新加载配置，默认为False
            
        Returns:
            Config: 配置对象
        """
        # 检查是否需要重新加载配置
        if force_reload or self._cache is None:
            return self._load_config()
        
        # 检查配置文件是否被修改
        if os.path.exists(self.config_path):
            current_mtime = os.path.getmtime(self.config_path)
            if current_mtime > self._cache_time:
                return self._load_config()
        
        return self._cache
    
    def update_config(self, new_config: Dict[str, Any]) -> Config:
        """
        更新配置文件和缓存
        
        Args:
            new_config: 新的配置数据
            
        Returns:
            Config: 更新后的配置对象
        """
        # 读取当前配置
        current_config = self.get_config()
        
        # 合并新配置
        config_data = current_config.model_dump()
        self._deep_merge(config_data, new_config)
        
        # 写入配置文件
        with open(self.config_path, "w", encoding="utf-8") as f:
            toml.dump(config_data, f)
        
        # 重新加载配置
        return self._load_config()
    
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        深度合并两个字典
        
        Args:
            target: 目标字典
            source: 源字典，将合并到目标字典中
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value


# 创建全局配置管理器实例
config_manager = ConfigManager()


def get_config(force_reload: bool = False) -> Config:
    """
    获取配置的便捷函数
    
    Args:
        force_reload: 是否强制重新加载配置
        
    Returns:
        Config: 配置对象
    """
    return config_manager.get_config(force_reload)


def update_config(new_config: Dict[str, Any]) -> Config:
    """
    更新配置的便捷函数
    
    Args:
        new_config: 新的配置数据
        
    Returns:
        Config: 更新后的配置对象
    """
    return config_manager.update_config(new_config)
