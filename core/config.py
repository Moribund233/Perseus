"""
配置管理模块

使用 Pydantic Settings 进行配置验证和管理。
所有配置项都通过环境变量或配置文件加载，并经过严格的类型验证。
"""
import os
import toml
import logging
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, ValidationInfo

logger = logging.getLogger(__name__)


class ServerSettings(BaseSettings):
    """服务器配置类"""
    host: str = Field(default="0.0.0.0", description="服务器监听地址")
    port: int = Field(default=8000, ge=1, le=65535, description="服务器监听端口")
    reload: bool = Field(default=False, description="是否启用热重载")
    log_level: str = Field(
        default="info",
        description="日志级别",
        pattern="^(debug|info|warning|error|critical)$"
    )


class GunicornSettings(BaseSettings):
    """Gunicorn生产环境配置类"""
    workers: int = Field(default=4, ge=1, le=32, description="Worker进程数")
    worker_class: str = Field(
        default="gunicorn_worker.PerseusUvicornWorker",
        description="Worker类"
    )
    threads: int = Field(default=1, ge=1, description="每个worker的线程数")
    worker_connections: int = Field(default=1000, ge=100, description="最大并发连接数")
    backlog: int = Field(default=2048, ge=128, description="等待连接的最大队列长度")
    timeout: int = Field(default=30, ge=10, le=300, description="Worker超时时间（秒）")
    graceful_timeout: int = Field(default=30, ge=5, le=120, description="优雅关闭超时时间（秒）")
    keepalive: int = Field(default=2, ge=1, le=60, description="Keep-alive连接超时时间（秒）")
    max_requests: int = Field(default=10000, ge=1000, description="Worker最大请求数")
    max_requests_jitter: int = Field(default=1000, ge=0, description="最大请求数随机偏移量")
    preload_app: bool = Field(default=False, description="是否预加载应用")
    daemon: bool = Field(default=False, description="是否以守护进程模式运行")
    access_log: bool = Field(default=True, description="是否启用访问日志")
    access_log_format: str = Field(
        default='%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s',
        description="访问日志格式"
    )
    capture_output: bool = Field(default=True, description="是否捕获stdout/stderr")
    enable_reuse_port: bool = Field(default=True, description="是否启用SO_REUSEPORT")


class AppSettings(BaseSettings):
    """应用配置类"""
    model_config = SettingsConfigDict(env_prefix="PERSEUS_APP_")

    title: str = Field(default="Perseus API", description="应用标题")
    description: str = Field(default="A Git-based collaborative development tool API", description="应用描述")
    version: str = Field(default="0.1.0", description="应用版本")
    debug: bool = Field(default=False, description="是否启用调试模式")


class CORSSettings(BaseSettings):
    """CORS跨域配置类"""
    allow_origins: list = Field(default=["*"], description="允许的源列表")
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
    proxy: bool = Field(default=True, description="是否启用反向代理")


class StorageSettings(BaseSettings):
    """存储配置类"""
    repo_root: str = Field(default="./repositories", description="Git仓库根目录路径")
    max_repo_size: int = Field(default=1073741824, ge=0, description="单个仓库最大大小（字节）")
    max_file_size: int = Field(default=104857600, ge=0, description="单个文件最大大小（字节）")
    enable_lfs: bool = Field(default=True, description="是否启用Git LFS")
    lfs_storage_path: Optional[str] = Field(default=None, description="LFS文件存储路径")


class SecuritySettings(BaseSettings):
    """安全配置类"""
    model_config = SettingsConfigDict(env_prefix="PERSEUS_SECURITY_")

    secret_key: str = Field(
        default="",
        description="JWT密钥，生产环境必须通过环境变量设置"
    )
    access_token_expire_minutes: int = Field(default=30, ge=1, description="访问令牌过期时间（分钟）")
    refresh_token_expire_days: int = Field(default=7, ge=1, description="刷新令牌过期时间（天）")
    algorithm: str = Field(default="HS256", description="JWT加密算法")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """验证密钥不为空（生产环境）"""
        # 注意：这里不强制要求，因为debug模式可能不需要
        # 实际验证在应用启动时进行
        return v


class LoggingSettings(BaseSettings):
    """日志配置类"""
    audit_log_path: str = Field(default="logs/audit.log", description="审计日志文件路径")
    audit_log_max_size: int = Field(default=10485760, ge=1, description="审计日志文件最大大小（字节）")
    audit_log_backup_count: int = Field(default=5, ge=0, description="审计日志备份文件数量")
    audit_log_enabled: bool = Field(default=True, description="是否启用审计日志")


class RateLimitItem(BaseSettings):
    """单个限流配置项"""
    mode: str = Field(
        default="minute",
        description="限流模式",
        pattern="^(minute|hour)$"
    )
    value: int = Field(default=200, ge=1, description="限流值")

    def to_limit_string(self) -> str:
        """转换为 slowapi 兼容的限流字符串"""
        return f"{self.value} per {self.mode}"


class RateLimitSettings(BaseSettings):
    """速率限制配置类"""
    default_limits: RateLimitItem = Field(
        default_factory=lambda: RateLimitItem(mode="minute", value=200),
        description="默认速率限制"
    )
    strict: RateLimitItem = Field(
        default_factory=lambda: RateLimitItem(mode="minute", value=5),
        description="严格限制"
    )
    standard: RateLimitItem = Field(
        default_factory=lambda: RateLimitItem(mode="minute", value=30),
        description="标准限制"
    )
    generous: RateLimitItem = Field(
        default_factory=lambda: RateLimitItem(mode="hour", value=2000),
        description="宽松限制"
    )
    git_operations: RateLimitItem = Field(
        default_factory=lambda: RateLimitItem(mode="minute", value=10),
        description="Git操作限制"
    )
    download: RateLimitItem = Field(
        default_factory=lambda: RateLimitItem(mode="minute", value=20),
        description="下载限制"
    )


class DatabaseSettings(BaseSettings):
    """
    数据库配置类

    使用 Pydantic 的验证机制，从环境变量自动读取配置。
    不再在 __init__ 中手动处理，而是通过 validators 和 Field 配置。
    """
    # 数据库连接URL - 优先从环境变量 DATABASE_URL 读取
    url: str = Field(
        default="sqlite:///./perseus.db",
        description="数据库连接URL"
    )

    # 压力测试模式 - 优先从环境变量 PERSEUS_STRESS_TEST 读取
    is_stress_test: bool = Field(default=False, description="是否启用压力测试模式")

    # 连接池配置
    pool_size: int = Field(default=20, ge=1, description="连接池大小")
    max_overflow: int = Field(default=40, ge=0, description="最大溢出连接数")
    pool_timeout: int = Field(default=10, ge=1, description="获取连接超时时间（秒）")
    pool_recycle: int = Field(default=1800, ge=0, description="连接回收时间（秒）")
    echo: bool = Field(default=False, description="是否打印SQL语句")

    # SQLite 特定配置
    sqlite_timeout: int = Field(default=10, ge=1, description="SQLite内部超时时间（秒）")
    sqlite_check_same_thread: bool = Field(default=False, description="是否检查同线程")
    sqlite_isolation_level: Optional[str] = Field(default=None, description="SQLite隔离级别")

    # WAL 模式配置
    enable_wal: bool = Field(default=True, description="是否启用WAL模式")
    wal_synchronous: str = Field(default="NORMAL", description="WAL同步模式")
    wal_cache_size: int = Field(default=10000, description="WAL缓存大小")
    wal_temp_store: str = Field(default="MEMORY", description="临时表存储位置")

    # 压力测试模式专用配置
    stress_pool_size: int = Field(default=30, ge=1, description="压力测试模式：连接池大小")
    stress_max_overflow: int = Field(default=60, ge=0, description="压力测试模式：最大溢出连接数")
    stress_pool_timeout: int = Field(default=15, ge=1, description="压力测试模式：获取连接超时时间")
    stress_pool_recycle: int = Field(default=300, ge=0, description="压力测试模式：连接回收时间")
    stress_sqlite_timeout: int = Field(default=5, ge=1, description="压力测试模式：SQLite超时")
    stress_echo: bool = Field(default=False, description="压力测试模式：打印SQL")

    # PostgreSQL 特定配置
    pg_ssl_mode: str = Field(default="prefer", description="PostgreSQL SSL模式")
    pg_connect_timeout: int = Field(default=10, ge=1, description="PostgreSQL连接超时")
    pg_application_name: str = Field(default="perseus", description="PostgreSQL应用名称")

    model_config = SettingsConfigDict(
        env_prefix="PERSEUS_DATABASE_",
        extra='ignore'
    )

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_from_env(cls, v):
        """从环境变量 DATABASE_URL 读取数据库URL"""
        env_url = os.environ.get("DATABASE_URL")
        if env_url:
            # 验证 URL 格式
            is_valid, error_msg = cls._validate_db_url_with_error(env_url)
            if not is_valid:
                raise ValueError(f"DATABASE_URL 格式无效: {error_msg}")
            return env_url
        return v

    @field_validator("is_stress_test", mode="before")
    @classmethod
    def validate_stress_test_from_env(cls, v):
        """从环境变量 PERSEUS_STRESS_TEST 读取压力测试模式"""
        env_stress = os.environ.get("PERSEUS_STRESS_TEST")
        if env_stress is not None:
            return env_stress.lower() in ("true", "1", "yes")
        return v

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        """验证数据库URL格式"""
        if not v:
            raise ValueError("数据库URL不能为空")

        url_lower = v.lower()
        valid_prefixes = ("sqlite://", "postgresql://", "postgres://", "postgresql+psycopg2://")
        if not any(url_lower.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"不支持的数据库协议类型: {v}")

        return v

    @property
    def db_type(self) -> str:
        """根据 URL 自动检测数据库类型"""
        url_lower = self.url.lower()
        if url_lower.startswith("sqlite"):
            return "sqlite"
        elif url_lower.startswith("postgresql") or url_lower.startswith("postgres"):
            return "postgresql"
        return "unknown"

    @property
    def is_sqlite(self) -> bool:
        """是否为 SQLite 数据库"""
        return self.db_type == "sqlite"

    @property
    def is_postgresql(self) -> bool:
        """是否为 PostgreSQL 数据库"""
        return self.db_type == "postgresql"

    @staticmethod
    def _mask_url(url: str) -> str:
        """掩码数据库 URL，隐藏敏感信息"""
        if not url or not isinstance(url, str):
            return "invalid_url"

        try:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(url)

            if parsed.password:
                netloc = f"{parsed.username}:****@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                parsed = parsed._replace(netloc=netloc)

            return urlunparse(parsed)
        except Exception:
            try:
                if "://" in url:
                    scheme = url.split("://")[0]
                    return f"{scheme}://****"
            except Exception:
                pass
            return "masked_url"

    @staticmethod
    def _validate_db_url_with_error(url: str) -> tuple[bool, str]:
        """验证数据库 URL 是否有效"""
        if not url or not isinstance(url, str):
            return False, "URL 为空或格式错误"

        try:
            url.encode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError) as e:
            return False, f"URL 编码错误: {str(e)}"

        url_lower = url.lower()
        valid_prefixes = ("sqlite://", "postgresql://", "postgres://", "postgresql+psycopg2://")
        if not any(url_lower.startswith(prefix) for prefix in valid_prefixes):
            return False, f"不支持的协议类型"

        return True, ""


class Config(BaseSettings):
    """配置主类"""
    server: ServerSettings = Field(default_factory=ServerSettings)
    gunicorn: GunicornSettings = Field(default_factory=GunicornSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)


class ConfigManager:
    """配置管理器 - 单例模式"""
    _instance: Optional['ConfigManager'] = None
    _config: Optional[Config] = None

    def __new__(cls, config_path: str = "config.toml"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config_path = config_path
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置"""
        # Pydantic 会自动从环境变量读取配置
        self._config = Config()

        # 如果配置文件存在，从文件加载额外配置
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    file_config = toml.load(f)
                    # 这里可以添加从文件覆盖配置的逻辑
                    logger.info(f"配置文件已加载: {self._config_path}")
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}")

    @property
    def config(self) -> Config:
        """获取配置对象"""
        return self._config

    def reload(self):
        """重新加载配置"""
        self._load_config()


def get_config() -> Config:
    """获取配置对象的便捷函数"""
    return ConfigManager().config


def reset_module_config_manager():
    """重置配置管理器单例（用于测试）"""
    ConfigManager._instance = None
    ConfigManager._config = None
