"""
模型初始化模块

提供数据库引擎、会话工厂和基础模型类的配置驱动初始化
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
import logging

logger = logging.getLogger(__name__)

# 导入配置 - 环境变量检测由 init 模块统一负责
from core.config import get_config
from utils.db_validation import (
    validate_database_config,
    check_sqlite_stress_test_warning,
)

_config = get_config()
db_config = _config.database

# 验证数据库配置（验证失败不阻止启动，已回退到 SQLite）
validation_passed = validate_database_config(db_config.url, db_config.db_type)
if not validation_passed:
    logger.warning("数据库配置验证未通过，但应用仍将继续启动")

# 检查 SQLite + 压力测试警告
warning = check_sqlite_stress_test_warning(db_config.is_sqlite, db_config.is_stress_test)
if warning:
    logger.warning(warning)


def _get_sqlite_connect_args():
    """获取 SQLite 连接参数"""
    if db_config.is_stress_test:
        return {
            "check_same_thread": db_config.sqlite_check_same_thread,
            "timeout": db_config.stress_sqlite_timeout,
            "isolation_level": db_config.sqlite_isolation_level,
        }
    else:
        return {
            "check_same_thread": db_config.sqlite_check_same_thread,
            "timeout": db_config.sqlite_timeout,
            "isolation_level": db_config.sqlite_isolation_level,
        }


def _get_postgresql_connect_args():
    """获取 PostgreSQL 连接参数"""
    connect_args = {}

    # SSL 模式
    if db_config.pg_ssl_mode and db_config.pg_ssl_mode != "prefer":
        connect_args["sslmode"] = db_config.pg_ssl_mode

    # 连接超时
    connect_args["connect_timeout"] = db_config.pg_connect_timeout

    return connect_args


def _create_engine_with_config():
    """
    根据配置创建数据库引擎
    
    Returns:
        Engine: SQLAlchemy引擎实例
    """
    db_type = db_config.db_type
    
    if db_type == "sqlite":
        return _create_sqlite_engine()
    elif db_type == "postgresql":
        return _create_postgresql_engine()
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")


def _create_sqlite_engine():
    """创建 SQLite 引擎"""
    if db_config.is_stress_test:
        return create_engine(
            db_config.url,
            connect_args=_get_sqlite_connect_args(),
            poolclass=QueuePool,
            pool_size=db_config.stress_pool_size,
            max_overflow=db_config.stress_max_overflow,
            pool_timeout=db_config.stress_pool_timeout,
            pool_recycle=db_config.stress_pool_recycle,
            pool_pre_ping=True,
            echo=db_config.stress_echo,
        )
    elif _config.app.debug:
        return create_engine(
            db_config.url,
            connect_args=_get_sqlite_connect_args(),
            poolclass=QueuePool,
            pool_size=db_config.pool_size,
            max_overflow=db_config.max_overflow,
            pool_timeout=db_config.pool_timeout,
            pool_recycle=db_config.pool_recycle,
            pool_pre_ping=True,
            echo=db_config.echo,
        )
    else:
        return create_engine(
            db_config.url,
            connect_args=_get_sqlite_connect_args(),
            poolclass=QueuePool,
            pool_size=db_config.pool_size,
            max_overflow=db_config.max_overflow,
            pool_timeout=db_config.pool_timeout,
            pool_recycle=db_config.pool_recycle,
            pool_pre_ping=True,
            echo=db_config.echo,
        )


def _get_postgresql_url_with_driver(url: str) -> str:
    """
    将 PostgreSQL URL 转换为带 psycopg2 驱动的格式

    Args:
        url: 原始 PostgreSQL URL (如 postgresql://user:pass@host:port/dbname)

    Returns:
        str: 带驱动的 URL (如 postgresql+psycopg2://user:pass@host:port/dbname)
    """
    if url.lower().startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif url.lower().startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url


def _create_postgresql_engine():
    """创建 PostgreSQL 引擎"""
    url_with_driver = _get_postgresql_url_with_driver(db_config.url)
    
    if db_config.is_stress_test:
        return create_engine(
            url_with_driver,
            connect_args=_get_postgresql_connect_args(),
            poolclass=QueuePool,
            pool_size=db_config.stress_pool_size,
            max_overflow=db_config.stress_max_overflow,
            pool_timeout=db_config.stress_pool_timeout,
            pool_recycle=db_config.stress_pool_recycle,
            pool_pre_ping=True,
            echo=db_config.stress_echo,
        )
    elif _config.app.debug:
        return create_engine(
            url_with_driver,
            connect_args=_get_postgresql_connect_args(),
            poolclass=QueuePool,
            pool_size=db_config.pool_size,
            max_overflow=db_config.max_overflow,
            pool_timeout=db_config.pool_timeout,
            pool_recycle=db_config.pool_recycle,
            pool_pre_ping=True,
            echo=db_config.echo,
        )
    else:
        return create_engine(
            url_with_driver,
            connect_args=_get_postgresql_connect_args(),
            poolclass=QueuePool,
            pool_size=db_config.pool_size,
            max_overflow=db_config.max_overflow,
            pool_timeout=db_config.pool_timeout,
            pool_recycle=db_config.pool_recycle,
            pool_pre_ping=True,
            echo=db_config.echo,
        )


# 创建引擎
engine = _create_engine_with_config()


# 添加连接池事件监听，用于调试和监控
@event.listens_for(engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """新连接建立时的回调"""
    # 仅对 SQLite 启用 WAL 模式
    if db_config.is_sqlite and db_config.enable_wal:
        # 设置 SQLite 优化参数
        dbapi_conn.execute(f"PRAGMA journal_mode=WAL")  # 使用 WAL 模式提高并发性能
        dbapi_conn.execute(f"PRAGMA synchronous={db_config.wal_synchronous}")  # 平衡性能和安全性
        dbapi_conn.execute(f"PRAGMA cache_size={db_config.wal_cache_size}")  # 增加缓存大小
        dbapi_conn.execute(f"PRAGMA temp_store={db_config.wal_temp_store}")  # 临时表存储在内存


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_conn, connection_record, connection_proxy):
    """连接从池中取出时的回调"""
    pass


@event.listens_for(engine, "checkin")
def on_checkin(dbapi_conn, connection_record):
    """连接归还到池时的回调"""
    pass


# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

# 导入所有模型
from models.base import BaseModel
from models.user import User
from models.repository import Repository
from models.repository_member import RepositoryMember
from models.branch import Branch
from models.commit import Commit
from models.pull_request import PullRequest, PRComment, PRReview
from models.issue import Issue, Label, IssueComment
from models.release import Release, ReleaseAsset
from models.webhook import WebHook, WebHookDelivery

__all__ = [
    "Base", "SessionLocal", "engine", "BaseModel",
    "User", "Repository", "RepositoryMember", "Branch", "Commit",
    "PullRequest", "PRComment", "PRReview", "Issue", "Label", "IssueComment",
    "Release", "ReleaseAsset",
    "WebHook", "WebHookDelivery",
    # 导出配置相关
    "get_db_config"
]


def get_db_config():
    """
    获取当前数据库配置
    
    Returns:
        DatabaseSettings: 数据库配置对象
    """
    return db_config
