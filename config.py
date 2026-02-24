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


class RateLimitItem(BaseSettings):
    """单个限流配置项"""
    mode: str = Field(default="minute", description="限流模式: minute 或 hour", pattern="^(minute|hour)$")
    value: int = Field(default=200, ge=1, description="限流值")
    
    def to_limit_string(self) -> str:
        """转换为 slowapi 兼容的限流字符串"""
        return f"{self.value} per {self.mode}"


class RateLimitSettings(BaseSettings):
    """速率限制配置类 - 支持分钟或小时二选一模式"""
    default_limits: RateLimitItem = Field(
        default_factory=lambda: RateLimitItem(mode="minute", value=200),
        description="默认速率限制"
    )
    strict: RateLimitItem = Field(
        default_factory=lambda: RateLimitItem(mode="minute", value=5),
        description="严格限制（用于敏感操作）"
    )
    standard: RateLimitItem = Field(
        default_factory=lambda: RateLimitItem(mode="minute", value=30),
        description="标准限制（用于普通API）"
    )
    generous: RateLimitItem = Field(
        default_factory=lambda: RateLimitItem(mode="hour", value=2000),
        description="宽松限制（用于读取操作）"
    )
    git_operations: RateLimitItem = Field(
        default_factory=lambda: RateLimitItem(mode="minute", value=10),
        description="Git操作限制"
    )
    download: RateLimitItem = Field(
        default_factory=lambda: RateLimitItem(mode="minute", value=20),
        description="下载限制"
    )


# 全局标志：记录是否已进行数据库URL验证（避免重复输出日志）
_db_url_validated = False
_original_db_url = None
_validation_result = None


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
    # 注意：对于高并发测试（100+并发），建议增加连接池大小
    # PostgreSQL 优化：增加连接池以支持更高并发
    stress_pool_size: int = Field(default=30, ge=1, description="压力测试模式：连接池大小")
    stress_max_overflow: int = Field(default=60, ge=0, description="压力测试模式：最大溢出连接数")
    stress_pool_timeout: int = Field(default=15, ge=1, description="压力测试模式：获取连接超时时间（秒）")
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
        
        如果环境变量未设置或配置无效，自动回退到 SQLite 默认值
        """
        import logging
        import sys
        logger = logging.getLogger(__name__)
        global _db_url_validated, _original_db_url, _validation_result
        
        # 从环境变量读取 DATABASE_URL
        env_url = os.environ.get("DATABASE_URL")
        
        # 处理 Windows 环境变量编码问题
        if env_url and sys.platform == "win32":
            try:
                # 在 Windows 上，环境变量可能是系统默认编码（如 GBK）
                # 尝试将其转换为 UTF-8
                if isinstance(env_url, str):
                    # 先编码为字节，再解码为 UTF-8
                    env_url = env_url.encode('utf-8', errors='ignore').decode('utf-8')
            except Exception as e:
                logger.warning(f"处理环境变量编码时出错: {e}")
        
        original_url = env_url
        
        if _db_url_validated and _original_db_url == original_url:
            env_url = _validation_result
        else:
            _original_db_url = original_url
            
            if not env_url:
                env_url = "sqlite:///./langit.db"
            else:
                is_valid, error_msg = self._validate_db_url_with_error(env_url)
                if not is_valid:
                    logger.warning(f"数据库连接失败，回退到 SQLite: {error_msg}")
                    env_url = "sqlite:///./langit.db"
            
            _validation_result = env_url
            _db_url_validated = True
        
        kwargs["url"] = env_url
        
        stress_test = os.environ.get("LANGIT_STRESS_TEST")
        if stress_test is None:
            stress_test = "false"
        kwargs["is_stress_test"] = stress_test.lower() in ("true", "1", "yes")
        
        super().__init__(**kwargs)
    
    @staticmethod
    def _mask_url(url: str) -> str:
        """
        掩码数据库 URL，隐藏敏感信息
        
        Args:
            url: 原始数据库 URL
            
        Returns:
            str: 掩码后的 URL（如: postgresql://***@localhost:5432/dbname）
        """
        if not url or not isinstance(url, str):
            return "invalid_url"
        
        try:
            # 确保 URL 是有效的 UTF-8 字符串
            if isinstance(url, bytes):
                url = url.decode('utf-8', errors='replace')
            
            # 解析 URL 并掩码密码部分
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(url)
            
            if parsed.password:
                # 有密码，需要掩码
                netloc = f"{parsed.username}:****@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                parsed = parsed._replace(netloc=netloc)
            
            return urlunparse(parsed)
        except Exception:
            # 解析失败，返回简化版本
            try:
                if "://" in url:
                    scheme = url.split("://")[0]
                    return f"{scheme}://****"
            except Exception:
                pass
            return "masked_url"

    @staticmethod
    def _validate_db_url_with_error(url: str) -> tuple[bool, str]:
        """
        验证数据库 URL 是否有效，返回详细错误信息
        
        Args:
            url: 数据库连接 URL
            
        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        if not url or not isinstance(url, str):
            return False, "URL 为空或格式错误"
        
        # 确保 URL 是有效的 UTF-8 字符串
        try:
            if isinstance(url, bytes):
                url = url.decode('utf-8', errors='replace')
            # 验证字符串是否可以被正确编码
            url.encode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError) as e:
            return False, f"URL 编码错误: {str(e)}"
        
        url_lower = url.lower()
        valid_prefixes = ("sqlite://", "postgresql://", "postgres://", "mysql://", "mysql+pymysql://", "postgresql+psycopg2://")
        if not any(url_lower.startswith(prefix) for prefix in valid_prefixes):
            return False, f"不支持的协议类型"
        
        # SQLite 不需要测试连接（本地文件）
        if url_lower.startswith("sqlite://"):
            return True, ""
        
        # 对于 PostgreSQL 和 MySQL，尝试测试连接
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.exc import SQLAlchemyError
            
            # 转换 URL 为带驱动的格式（同步验证）
            test_url = url
            if url_lower.startswith("mysql://"):
                test_url = url.replace("mysql://", "mysql+pymysql://", 1)
            elif url_lower.startswith("postgresql://") and not url_lower.startswith("postgresql+psycopg2://"):
                # 如果已经是 postgresql+psycopg2:// 格式，不需要转换
                test_url = url.replace("postgresql://", "postgresql+pg8000://", 1)
            
            # 创建引擎并测试连接
            # pg8000 不支持 connect_timeout 参数，使用 SQLAlchemy 的 pool_pre_ping 代替
            connect_args = {}
            if url_lower.startswith("mysql://"):
                connect_args = {"connect_timeout": 5}
            # PostgreSQL (pg8000) 不使用 connect_timeout
            
            engine = create_engine(test_url, connect_args=connect_args, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            
            return True, ""
            
        except SQLAlchemyError as e:
            error_msg = str(e).split('\n')[0]  # 只取第一行错误信息
            return False, error_msg
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _validate_db_url(url: str) -> bool:
        """
        验证数据库 URL 是否有效（简化版本，无日志输出）
        
        Args:
            url: 数据库连接 URL
            
        Returns:
            bool: 是否有效
        """
        is_valid, _ = DatabaseSettings._validate_db_url_with_error(url)
        return is_valid


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

        # 移除敏感配置项（这些通过环境变量注入，不写入配置文件）
        # 1. 移除 security.secret_key（JWT Secret Key）
        if "security" in config_data and "secret_key" in config_data["security"]:
            del config_data["security"]["secret_key"]

        # 2. 移除 app.debug（调试模式）
        if "app" in config_data and "debug" in config_data["app"]:
            del config_data["app"]["debug"]

        # 3. 移除 database.url 和 database.is_stress_test（数据库连接配置）
        if "database" in config_data:
            if "url" in config_data["database"]:
                del config_data["database"]["url"]
            if "is_stress_test" in config_data["database"]:
                del config_data["database"]["is_stress_test"]

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
