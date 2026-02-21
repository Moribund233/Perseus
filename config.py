import os
import toml
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class ServerSettings(BaseSettings):
    """服务器配置类"""
    host: str = Field(default="0.0.0.0", description="服务器监听地址")
    port: int = Field(default=8000, ge=1, le=65535, description="服务器监听端口")  # 添加端口范围验证
    reload: bool = Field(default=False, description="是否启用热重载")
    workers: int = Field(default=1, ge=1, description="服务器工作进程数")  # 添加workers数量验证
    log_level: str = Field(default="info", description="日志级别", pattern="^(debug|info|warning|error|critical)$")  # 添加日志级别验证


class AppSettings(BaseSettings):
    """应用配置类 - 调试模式优先从环境变量 LANGIT_APP_DEBUG 读取"""
    model_config = SettingsConfigDict(env_prefix="LANGIT_APP_")
    
    title: str = Field(default="LanGit API", description="应用标题")
    description: str = Field(default="A Git-based collaborative development tool API", description="应用描述")
    version: str = Field(default="0.1.0", description="应用版本")
    debug: bool = Field(default=False, description="是否启用调试模式，优先从环境变量 LANGIT_APP_DEBUG 读取")


class SystemSettings(BaseSettings):
    """系统配置类"""
    platform: str = Field(description="操作系统平台")
    python_version: str = Field(description="Python版本")
    python_version_info: Dict[str, Any] = Field(description="Python版本信息")


class CORSSettings(BaseSettings):
    """CORS跨域配置类"""
    # 开发环境默认值
    allow_origins: list = Field(
        default=["*"],
        description="允许的源列表，生产环境应该限制为特定域名"
    )
    allow_credentials: bool = Field(default=True, description="是否允许携带凭证")
    allow_methods: list = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="允许的HTTP方法"
    )
    allow_headers: list = Field(
        default=["Content-Type", "Authorization", "X-Requested-With"],
        description="允许的请求头"
    )
    max_age: int = Field(default=600, description="预检请求缓存时间（秒）")


class ProxySettings(BaseSettings):
    """代理配置类"""
    proxy: bool = Field(default=True, description="是否启用反向代理（保留用于服务端内部判断）")


class StorageSettings(BaseSettings):
    """存储配置类"""
    repo_root: str = Field(default="./repositories", description="Git仓库根目录路径")
    max_repo_size: int = Field(default=1073741824, ge=0, description="单个仓库最大大小（字节），默认1GB")
    max_file_size: int = Field(default=104857600, ge=0, description="单个文件最大大小（字节），默认100MB")
    enable_lfs: bool = Field(default=True, description="是否启用Git LFS")
    lfs_storage_path: Optional[str] = Field(default=None, description="LFS文件存储路径，默认在repo_root/lfs")


class SecuritySettings(BaseSettings):
    """安全配置类 - JWT密钥优先从环境变量 LANGIT_SECURITY_SECRET_KEY 读取"""
    model_config = SettingsConfigDict(env_prefix="LANGIT_SECURITY_")
    
    secret_key: str = Field(default="", description="JWT密钥，优先从环境变量 LANGIT_SECURITY_SECRET_KEY 读取")
    access_token_expire_minutes: int = Field(default=30, ge=1, description="访问令牌过期时间（分钟）")
    refresh_token_expire_days: int = Field(default=7, ge=1, description="刷新令牌过期时间（天）")
    algorithm: str = Field(default="HS256", description="JWT加密算法")


class LoggingSettings(BaseSettings):
    """日志配置类"""
    audit_log_path: str = Field(default="logs/audit.log", description="审计日志文件路径")
    audit_log_max_size: int = Field(default=10485760, ge=1, description="审计日志文件最大大小（字节），默认10MB")
    audit_log_backup_count: int = Field(default=5, ge=0, description="审计日志备份文件数量")
    audit_log_enabled: bool = Field(default=True, description="是否启用审计日志")


class RateLimitSettings(BaseSettings):
    """速率限制配置类"""
    default_limits: list = Field(default=["200 per minute", "1000 per hour"], description="默认速率限制")
    strict: list = Field(default=["5 per minute", "20 per hour"], description="严格限制（用于敏感操作）")
    standard: list = Field(default=["30 per minute", "500 per hour"], description="标准限制（用于普通API）")
    generous: list = Field(default=["100 per minute", "2000 per hour"], description="宽松限制（用于读取操作）")
    git_operations: list = Field(default=["10 per minute", "100 per hour"], description="Git操作限制")
    download: list = Field(default=["20 per minute", "200 per hour"], description="下载限制")


class DatabaseSettings(BaseSettings):
    """
    数据库配置类
    
    注意：DATABASE_URL 和 IS_STRESS_TEST 仅通过环境变量注入，不写入配置文件
    - DATABASE_URL: 数据库连接URL，环境变量名称为 DATABASE_URL（必需）
    - IS_STRESS_TEST: 是否启用压力测试模式，环境变量名称为 LANGIT_STRESS_TEST（必需）
    """
    # 环境变量注入的配置（不写入配置文件，无默认值，必须从环境变量读取）
    url: str = Field(
        description="数据库连接URL，必须通过环境变量 DATABASE_URL 注入"
    )
    is_stress_test: bool = Field(
        description="是否启用压力测试模式，必须通过环境变量 LANGIT_STRESS_TEST 注入"
    )
    
    # 服务端记录的数据库类型（由服务端维护，用于迁移检测）
    current_db_type: Optional[str] = Field(
        default=None, 
        description="服务端记录的上次实际数据库类型，用于检测类型变更和迁移"
    )
    
    # 可写入配置文件的配置项
    pool_size: int = Field(default=20, ge=1, description="连接池大小（增加以支持高并发）")
    max_overflow: int = Field(default=40, ge=0, description="最大溢出连接数（增加以支持高并发）")
    pool_timeout: int = Field(default=10, ge=1, description="获取连接超时时间（秒），减少以避免长时间等待")
    pool_recycle: int = Field(default=1800, ge=0, description="连接回收时间（秒），减少以更快释放空闲连接")
    echo: bool = Field(default=False, description="是否打印SQL语句（调试用）")
    
    # SQLite 特定配置
    sqlite_timeout: int = Field(default=10, ge=1, description="SQLite内部超时时间（秒）")
    sqlite_check_same_thread: bool = Field(default=False, description="是否检查同线程")
    sqlite_isolation_level: Optional[str] = Field(default=None, description="SQLite隔离级别，null表示自动提交模式")
    
    # WAL 模式配置
    enable_wal: bool = Field(default=True, description="是否启用WAL模式")
    wal_synchronous: str = Field(default="NORMAL", description="WAL同步模式")
    wal_cache_size: int = Field(default=10000, description="WAL缓存大小")
    wal_temp_store: str = Field(default="MEMORY", description="临时表存储位置")
    
    # 压力测试模式专用配置（仅在 is_stress_test=true 时生效）
    stress_pool_size: int = Field(default=5, ge=1, description="压力测试模式：连接池大小")
    stress_max_overflow: int = Field(default=10, ge=0, description="压力测试模式：最大溢出连接数")
    stress_pool_timeout: int = Field(default=5, ge=1, description="压力测试模式：获取连接超时时间（秒）")
    stress_pool_recycle: int = Field(default=300, ge=0, description="压力测试模式：连接回收时间（秒）")
    stress_sqlite_timeout: int = Field(default=5, ge=1, description="压力测试模式：SQLite内部超时时间（秒）")
    stress_echo: bool = Field(default=False, description="压力测试模式：是否打印SQL语句")
    
    # PostgreSQL 特定配置
    pg_ssl_mode: str = Field(default="prefer", description="PostgreSQL SSL模式")
    pg_connect_timeout: int = Field(default=10, ge=1, description="PostgreSQL连接超时时间（秒）")
    pg_application_name: str = Field(default="langit", description="PostgreSQL应用名称")
    
    # MySQL 特定配置
    mysql_charset: str = Field(default="utf8mb4", description="MySQL字符集")
    mysql_pool_recycle: int = Field(default=3600, ge=0, description="MySQL连接回收时间（秒）")
    mysql_connect_timeout: int = Field(default=10, ge=1, description="MySQL连接超时时间（秒）")
    mysql_read_timeout: int = Field(default=30, ge=1, description="MySQL读取超时时间（秒）")
    mysql_write_timeout: int = Field(default=30, ge=1, description="MySQL写入超时时间（秒）")
    
    model_config = SettingsConfigDict(
        env_prefix="LANGIT_DATABASE_",
        extra='ignore'  # 忽略额外的环境变量
    )
    
    @property
    def db_type(self) -> str:
        """
        根据 DATABASE_URL 自动检测数据库类型
        
        Returns:
            str: 数据库类型 (sqlite, postgresql, mysql)
        """
        url_lower = self.url.lower()
        if url_lower.startswith("sqlite"):
            return "sqlite"
        elif url_lower.startswith("postgresql") or url_lower.startswith("postgres"):
            return "postgresql"
        elif url_lower.startswith("mysql"):
            return "mysql"
        else:
            return "unknown"
    
    @property
    def is_sqlite(self) -> bool:
        """是否为 SQLite 数据库"""
        return self.db_type == "sqlite"
    
    @property
    def is_postgresql(self) -> bool:
        """是否为 PostgreSQL 数据库"""
        return self.db_type == "postgresql"
    
    @property
    def is_mysql(self) -> bool:
        """是否为 MySQL 数据库"""
        return self.db_type == "mysql"
    
    def __init__(self, **kwargs):
        """
        初始化时从环境变量读取必需配置
        
        Raises:
            ValueError: 当必需的配置项未在环境变量中设置时抛出
        """
        # 从环境变量读取 DATABASE_URL（必需）
        env_url = os.environ.get("DATABASE_URL")
        if not env_url:
            raise ValueError(
                "缺少必需的环境变量: DATABASE_URL\n"
                "请设置数据库连接URL，例如:\n"
                "  export DATABASE_URL=\"sqlite:///./langit.db\"\n"
                "  export DATABASE_URL=\"postgresql://user:pass@localhost/dbname\""
            )
        kwargs["url"] = env_url
        
        # 从环境变量读取 LANGIT_STRESS_TEST（必需）
        stress_test = os.environ.get("LANGIT_STRESS_TEST")
        if stress_test is None:
            raise ValueError(
                "缺少必需的环境变量: LANGIT_STRESS_TEST\n"
                "请设置压力测试模式标志，例如:\n"
                "  export LANGIT_STRESS_TEST=\"false\"  # 正常模式\n"
                "  export LANGIT_STRESS_TEST=\"true\"   # 压力测试模式"
            )
        kwargs["is_stress_test"] = stress_test.lower() in ("true", "1", "yes")
        
        super().__init__(**kwargs)


class Config(BaseSettings):
    """配置主类"""
    server: ServerSettings = Field(default_factory=ServerSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    system: Optional[SystemSettings] = Field(default=None, description="系统信息")

    model_config = SettingsConfigDict(extra='forbid')  # 严格验证配置，禁止额外的配置项


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


# 模块级别的单例实例，用于向后兼容
# 但建议在新代码中直接使用ConfigManager类
_module_config_manager = None


def get_module_config_manager(config_path: str = "config.toml") -> ConfigManager:
    """
    获取模块级别的配置管理器实例（用于向后兼容）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        ConfigManager: 配置管理器实例
    """
    global _module_config_manager
    if _module_config_manager is None:
        _module_config_manager = ConfigManager(config_path)
    return _module_config_manager


def get_config(force_reload: bool = False, config_path: str = "config.toml") -> Config:
    """
    获取配置的便捷函数
    
    Args:
        force_reload: 是否强制重新加载配置
        config_path: 配置文件路径（仅首次调用时有效）
        
    Returns:
        Config: 配置对象
    """
    manager = get_module_config_manager(config_path)
    return manager.get_config(force_reload)


def update_config(new_config: Dict[str, Any], config_path: str = "config.toml") -> Config:
    """
    更新配置的便捷函数
    
    Args:
        new_config: 新的配置数据
        config_path: 配置文件路径（仅首次调用时有效）
        
    Returns:
        Config: 更新后的配置对象
    """
    manager = get_module_config_manager(config_path)
    return manager.update_config(new_config)


def reset_module_config_manager():
    """
    重置模块级别的配置管理器实例，用于测试
    """
    global _module_config_manager
    _module_config_manager = None
