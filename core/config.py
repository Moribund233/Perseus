"""
配置管理模块

使用 Pydantic Settings 进行配置验证和管理。
所有配置项都通过环境变量或配置文件加载，并经过严格的类型验证。
"""
import os
import toml
import logging
from typing import Dict, Any, Literal, Optional
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
    """CORS跨域配置类 (仅用于文档说明，实际CORS由Nginx处理)"""
    allow_origins: list = Field(default=["*"], description="允许的源列表（由Nginx处理）")
    allow_credentials: bool = Field(default=True, description="是否允许携带凭证（由Nginx处理）")
    allow_methods: list = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="允许的HTTP方法（由Nginx处理）"
    )
    allow_headers: list = Field(
        default=["Content-Type", "Authorization", "X-Requested-With"],
        description="允许的请求头（由Nginx处理）"
    )
    max_age: int = Field(default=600, description="预检请求缓存时间（秒）（由Nginx处理）")


class StorageSettings(BaseSettings):
    """存储配置类"""
    model_config = SettingsConfigDict(env_prefix="PERSEUS_STORAGE_")

    repo_root: str = Field(default="./repositories", description="Git仓库根目录路径")
    max_repo_size: int = Field(default=1073741824, ge=0, description="单个仓库最大大小（字节）")
    max_file_size: int = Field(default=104857600, ge=0, description="单个文件最大大小（字节）")


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


class RedisSettings(BaseSettings):
    """Redis 配置类"""
    model_config = SettingsConfigDict(env_prefix="PERSEUS_REDIS_", extra="ignore")

    url: str = Field(default="", description="Redis 连接 URL，为空时不使用 Redis。优先读 PERSEUS_REDIS_URL，回退到 REDIS_URL")

    @field_validator("url", mode="before")
    @classmethod
    def fallback_to_redis_url(cls, v: str) -> str:
        if not v:
            return os.environ.get("REDIS_URL", "")
        return v


class LoggingSettings(BaseSettings):
    """日志配置类"""
    audit_log_path: str = Field(default="logs/audit.log", description="审计日志文件路径")
    audit_log_max_size: int = Field(default=10485760, ge=1, description="审计日志文件最大大小（字节）")
    audit_log_backup_count: int = Field(default=5, ge=0, description="审计日志备份文件数量")
    audit_log_enabled: bool = Field(default=True, description="是否启用审计日志")


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
        valid_prefixes = ("sqlite://", "sqlite+aiosqlite://", "postgresql://", "postgres://", "postgresql+psycopg2://", "postgresql+asyncpg://")
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
        valid_prefixes = ("sqlite://", "sqlite+aiosqlite://", "postgresql://", "postgres://", "postgresql+psycopg2://", "postgresql+asyncpg://")
        if not any(url_lower.startswith(prefix) for prefix in valid_prefixes):
            return False, f"不支持的协议类型"

        return True, ""


class ConcurrencySettings(BaseSettings):
    """并发控制配置类（派生自数据库压力测试模式）"""
    max_concurrent: int = Field(default=100, description="最大并发请求数")
    max_wait_time: float = Field(default=5.0, description="最大等待时间（秒）")

    @classmethod
    def from_stress_test(cls, is_stress_test: bool) -> "ConcurrencySettings":
        """根据是否压力测试创建并发配置"""
        if is_stress_test:
            return cls(max_concurrent=200, max_wait_time=10.0)
        return cls()


class LFSSettings(BaseSettings):
    """LFS 配置"""
    model_config = SettingsConfigDict(env_prefix="PERSEUS_LFS_")

    enabled: bool = Field(default=True, description="是否启用 Git LFS")
    storage_backend: Literal["local", "s3"] = Field(default="local", description="LFS 存储后端 (local | s3)")
    local_path: str = Field(default="/data/lfs", description="本地 LFS 文件存储路径")
    s3_bucket: str = Field(default="perseus-lfs", description="S3 存储桶名称")
    s3_endpoint: str = Field(default="http://minio:9000", description="S3 端点地址")
    s3_access_key: str = Field(default="", description="S3 访问密钥")
    s3_secret_key: str = Field(default="", description="S3 密钥")
    s3_region: str = Field(default="us-east-1", description="S3 区域")
    max_upload_size: int = Field(default=5 * 1024 * 1024 * 1024, ge=0, description="最大上传文件大小（字节，默认 5GB）")


class SearchSettings(BaseSettings):
    """搜索配置"""
    model_config = SettingsConfigDict(env_prefix="PERSEUS_SEARCH_")

    enabled: bool = Field(default=True, description="是否启用搜索功能")
    max_results: int = Field(default=100, ge=1, description="最大搜索结果数")
    max_file_size: int = Field(default=10 * 1024 * 1024, ge=0, description="最大文件大小（字节，默认 10MB）")


class OAuthSettings(BaseSettings):
    """OAuth2 认证配置"""
    model_config = SettingsConfigDict(env_prefix="PERSEUS_OAUTH_")

    github_client_id: str = Field(default="", description="GitHub OAuth App Client ID")
    github_client_secret: str = Field(default="", description="GitHub OAuth App Client Secret")
    github_redirect_uri: str = Field(default="http://localhost:5173/auth/github/callback", description="GitHub OAuth 回调地址")
    gitlab_client_id: str = Field(default="", description="GitLab OAuth App Client ID")
    gitlab_client_secret: str = Field(default="", description="GitLab OAuth App Client Secret")
    gitlab_redirect_uri: str = Field(default="http://localhost:5173/auth/gitlab/callback", description="GitLab OAuth 回调地址")


class Config(BaseSettings):
    """配置主类"""
    server: ServerSettings = Field(default_factory=ServerSettings)
    gunicorn: GunicornSettings = Field(default_factory=GunicornSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    lfs: LFSSettings = Field(default_factory=LFSSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    oauth: OAuthSettings = Field(default_factory=OAuthSettings)

    @property
    def concurrency(self) -> ConcurrencySettings:
        """获取并发配置（根据压力测试模式自适应）"""
        return ConcurrencySettings.from_stress_test(self.database.is_stress_test)


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
        """
        加载配置（TOML 文件 + 环境变量合并）

        优先级（从低到高）:
        1. Pydantic Field 默认值
        2. TOML 配置文件中的值（仅当没有对应环境变量时生效）
        3. 环境变量（最高优先级）

        TOML 文件与 env_prefix 的对应关系:
        - TOML [server] → env SERVER_*（无前缀，一般不设环境变量）
        - TOML [app] → env PERSEUS_APP_*
        - TOML [database] → env PERSEUS_DATABASE_*（以及 DATABASE_URL / PERSEUS_STRESS_TEST 特殊项）
        - TOML [security] → env PERSEUS_SECURITY_*
        """
        # 1. 先创建基础配置（从环境变量和 Field 默认值读取）
        self._config = Config()

        # 2. 加载 TOML 配置文件，选择性合并
        if not os.path.exists(self._config_path):
            return

        toml_config = {}
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                toml_config = toml.load(f)
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}")
            return

        # 3. 逐节合并 TOML 值：仅当该节下没有对应环境变量时才应用
        for section, section_data in toml_config.items():
            if not isinstance(section_data, dict):
                continue

            sub_model = getattr(self._config, section, None)
            if sub_model is None:
                continue

            # 获取本节对应的 env_prefix（从 Pydantic model_config）
            sub_cls = sub_model.__class__
            env_prefix = ""
            if hasattr(sub_cls, 'model_config'):
                mc = sub_cls.model_config
                if isinstance(mc, dict):
                    env_prefix = mc.get('env_prefix', '') or ''
                elif hasattr(mc, 'get'):
                    env_prefix = mc.get('env_prefix', '') or ''

            # 特殊 env 检查：有些字段通过 field_validator 读取自定义环境变量
            extra_env_checks = self._get_extra_env_checks(section)

            # 收集在当前节中未设置环境变量的字段
            toml_updates: Dict[str, Any] = {}
            for key, value in section_data.items():
                # 跳过嵌套子模型（如 rate_limit.xxx，它们没有 env_prefix）
                if isinstance(value, dict):
                    self._merge_nested_sub_model(sub_model, key, value)
                    continue

                # 检查标准 env_prefix + 字段名
                env_name = f"{env_prefix}{key.upper()}"
                if os.environ.get(env_name) is not None:
                    continue

                # 检查特殊 env 名
                if key in extra_env_checks:
                    if os.environ.get(extra_env_checks[key]) is not None:
                        continue

                toml_updates[key] = value

            if toml_updates:
                updated = sub_model.model_copy(update=toml_updates)
                setattr(self._config, section, updated)

        logger.info(f"配置文件已加载: {self._config_path}")

    @staticmethod
    def _get_extra_env_checks(section: str) -> Dict[str, str]:
        """
        获取特殊字段的自定义环境变量名映射

        某些字段（如 database.url）通过 field_validator 读取非标准 env 名，
        需要额外检查这些环境变量。
        """
        extra = {
            "database": {
                "url": "DATABASE_URL",
                "is_stress_test": "PERSEUS_STRESS_TEST",
            },
        }
        return extra.get(section, {})

    @staticmethod
    def _merge_nested_sub_model(parent: Any, field: str, data: dict) -> None:
        """
        合并嵌套子模型（如 rate_limit 下的 default_limits、strict 等）

        Args:
            parent: 父模型实例
            field: 字段名
            data: TOML 中该字段的字典值
        """
        nested = getattr(parent, field, None)
        if nested is None:
            return
        try:
            updated = nested.model_copy(update=data)
            setattr(parent, field, updated)
        except Exception:
            logger.debug(f"跳过嵌套模型更新 {field}: 类型不匹配")

    @property
    def config(self) -> Config:
        """获取配置对象"""
        return self._config

    def reload(self):
        """重新加载配置"""
        self._load_config()


def get_config(config_path: str = "config.toml") -> Config:
    """获取配置对象的便捷函数

    Args:
        config_path: 配置文件路径，仅首次调用时生效（单例缓存）

    Returns:
        Config: 全局配置对象
    """
    return ConfigManager(config_path).config


def reset_module_config_manager():
    """重置配置管理器单例（用于测试）"""
    ConfigManager._instance = None
    ConfigManager._config = None


# =============================================================================
# F-009: 启动配置完整性校验
# =============================================================================


class ConfigValidationResult:
    """配置校验结果"""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def is_valid(self) -> bool:
        """是否全部通过（无错误）"""
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        """添加错误"""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """添加警告"""
        self.warnings.append(message)

    def merge(self, other: "ConfigValidationResult") -> None:
        """合并另一个校验结果"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

    def print_report(self) -> None:
        """打印校验报告"""
        if self.is_valid and not self.warnings:
            logger.info("✅ 配置校验全部通过")
            return

        if self.errors:
            logger.error("=" * 60)
            logger.error("❌ 配置校验失败")
            logger.error("=" * 60)
            for err in self.errors:
                logger.error(f"  • {err}")
            logger.error("=" * 60)

        if self.warnings:
            for warn in self.warnings:
                logger.warning(f"  ⚠ {warn}")


def _validate_database_config(config: Config, result: ConfigValidationResult) -> None:
    """校验数据库配置"""
    db = config.database

    # 1. URL 协议检查（Pydantic 层已做格式校验，这里补充运行时可达性提示）
    if db.is_sqlite:
        # SQLite 文件路径检查
        sqlite_path = db.url.replace("sqlite:///", "").replace("sqlite+aiosqlite:///", "")
        if sqlite_path:
            db_dir = os.path.dirname(os.path.abspath(sqlite_path))
            if not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, exist_ok=True)
                except (OSError, PermissionError) as e:
                    result.add_error(f"数据库目录不可创建: {db_dir} ({e})")

    # 2. 连接池配置合理性
    if db.pool_size < 1:
        result.add_error("连接池大小必须 >= 1")
    if db.max_overflow < 0:
        result.add_error("最大溢出连接数不能为负数")
    if db.pool_timeout < 1:
        result.add_error("连接超时时间必须 >= 1 秒")
    if db.pool_recycle < 0:
        result.add_error("连接回收时间不能为负数")

    # 3. PostgreSQL SSL 模式检查
    if db.is_postgresql:
        valid_ssl_modes = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}
        if db.pg_ssl_mode not in valid_ssl_modes:
            result.add_error(f"无效的 PostgreSQL SSL 模式: {db.pg_ssl_mode}")


def _validate_storage_config(config: Config, result: ConfigValidationResult) -> None:
    """校验存储配置"""
    storage = config.storage

    # 1. 仓库根目录可写性
    repo_root = os.path.abspath(storage.repo_root)
    if not os.path.exists(repo_root):
        try:
            os.makedirs(repo_root, exist_ok=True)
            logger.info(f"已创建仓库根目录: {repo_root}")
        except (OSError, PermissionError) as e:
            result.add_error(f"仓库根目录不可创建: {repo_root} ({e})")
    elif not os.access(repo_root, os.W_OK):
        result.add_error(f"仓库根目录不可写: {repo_root}")

    # 2. 仓库大小限制
    if storage.max_repo_size <= 0:
        result.add_warning("仓库大小限制未设置 (max_repo_size <= 0)")
    if storage.max_file_size <= 0:
        result.add_warning("文件大小限制未设置 (max_file_size <= 0)")
    if storage.max_file_size > storage.max_repo_size:
        result.add_warning("单文件大小限制大于仓库大小限制")

    # 3. LFS 存储路径
    lfs = config.lfs
    if lfs.enabled:
        if lfs.local_path:
            lfs_path = os.path.abspath(lfs.local_path)
            if not os.path.exists(lfs_path):
                try:
                    os.makedirs(lfs_path, exist_ok=True)
                except (OSError, PermissionError) as e:
                    result.add_warning(f"LFS 存储路径不可创建: {lfs_path} ({e})")
        else:
            result.add_warning("LFS 已启用但未设置存储路径，将使用默认位置")


def _validate_security_config(config: Config, result: ConfigValidationResult) -> None:
    """校验安全配置"""
    security = config.security

    # 1. Secret Key 检查（生产环境必须设置）
    if not security.secret_key:
        if config.app.debug:
            result.add_warning("JWT Secret Key 未设置，开发环境将使用 fallback 密钥")
        else:
            result.add_error("生产环境必须通过环境变量 PERSEUS_SECURITY_SECRET_KEY 设置 JWT 密钥")

    # 2. Token 过期时间合理性
    if security.access_token_expire_minutes < 5:
        result.add_warning(f"访问令牌过期时间过短 ({security.access_token_expire_minutes} 分钟)")
    if security.access_token_expire_minutes > 1440:
        result.add_warning(f"访问令牌过期时间过长 ({security.access_token_expire_minutes} 分钟 > 24 小时)")

    if security.refresh_token_expire_days < 1:
        result.add_warning(f"刷新令牌过期时间过短 ({security.refresh_token_expire_days} 天)")
    if security.refresh_token_expire_days > 90:
        result.add_warning(f"刷新令牌过期时间过长 ({security.refresh_token_expire_days} 天 > 90 天)")

    # 3. JWT 算法检查
    valid_algorithms = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512"}
    if security.algorithm not in valid_algorithms:
        result.add_error(f"不支持的 JWT 算法: {security.algorithm}")


def _validate_server_config(config: Config, result: ConfigValidationResult) -> None:
    """校验服务器配置"""
    server = config.server

    # 1. 端口权限检查
    if server.port < 1024:
        result.add_warning(f"使用特权端口 ({server.port}) 可能需要 root 权限")


def _validate_logging_config(config: Config, result: ConfigValidationResult) -> None:
    """校验日志配置"""
    logging_cfg = config.logging

    if logging_cfg.audit_log_enabled:
        log_path = logging_cfg.audit_log_path
        log_dir = os.path.dirname(os.path.abspath(log_path))
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except (OSError, PermissionError) as e:
                result.add_warning(f"审计日志目录不可创建: {log_dir} ({e})")


def validate_config(config: Optional[Config] = None, config_path: str = "config.toml") -> ConfigValidationResult:
    """
    执行完整的配置完整性校验

    检查项包括:
    1. 数据库配置（URL 协议、连接池参数、SSL 模式）
    2. 存储配置（仓库根目录可写性、大小限制、LFS 路径）
    3. 安全配置（JWT 密钥、Token 过期时间、签名算法）
    4. 服务器配置（端口权限）
    5. 日志配置（审计日志路径可写性）
    6. 配置文件存在性

    Args:
        config: 配置对象，为 None 时自动加载
        config_path: 配置文件路径（config 为 None 时使用）

    Returns:
        ConfigValidationResult: 校验结果，包含 errors 和 warnings
    """
    result = ConfigValidationResult()

    # 0. 配置文件存在性
    if config is None and not os.path.exists(config_path):
        result.add_error(f"配置文件不存在: {config_path}")
        return result

    # 加载配置
    if config is None:
        try:
            config = get_config(config_path)
        except Exception as e:
            result.add_error(f"配置加载失败: {e}")
            return result

    # 1. 数据库配置
    _validate_database_config(config, result)

    # 2. 存储配置
    _validate_storage_config(config, result)

    # 3. 安全配置
    _validate_security_config(config, result)

    # 4. 服务器配置
    _validate_server_config(config, result)

    # 5. 日志配置
    _validate_logging_config(config, result)

    return result
