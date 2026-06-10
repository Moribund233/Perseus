"""
模型初始化模块

提供数据库引擎、会话工厂和基础模型类的配置驱动初始化
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 导入配置
from core.config import get_config
from utils.db_validation import (
    validate_database_config,
    check_sqlite_stress_test_warning,
)

# 延迟初始化的全局变量
_engine: Optional[Engine] = None
SessionLocal = None
Base = declarative_base()


def _get_sqlite_connect_args(db_config):
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


def _get_postgresql_connect_args(db_config):
    """获取 PostgreSQL 连接参数"""
    connect_args = {}

    # SSL 模式
    if db_config.pg_ssl_mode and db_config.pg_ssl_mode != "prefer":
        connect_args["sslmode"] = db_config.pg_ssl_mode

    # 连接超时
    connect_args["connect_timeout"] = db_config.pg_connect_timeout

    return connect_args


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


def _create_sqlite_engine(db_config, app_config):
    """创建 SQLite 引擎"""
    if db_config.is_stress_test:
        return create_engine(
            db_config.url,
            connect_args=_get_sqlite_connect_args(db_config),
            poolclass=QueuePool,
            pool_size=db_config.stress_pool_size,
            max_overflow=db_config.stress_max_overflow,
            pool_timeout=db_config.stress_pool_timeout,
            pool_recycle=db_config.stress_pool_recycle,
            pool_pre_ping=True,
            echo=db_config.stress_echo,
        )
    elif app_config.debug:
        return create_engine(
            db_config.url,
            connect_args=_get_sqlite_connect_args(db_config),
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
            connect_args=_get_sqlite_connect_args(db_config),
            poolclass=QueuePool,
            pool_size=db_config.pool_size,
            max_overflow=db_config.max_overflow,
            pool_timeout=db_config.pool_timeout,
            pool_recycle=db_config.pool_recycle,
            pool_pre_ping=True,
            echo=db_config.echo,
        )


def _create_postgresql_engine(db_config, app_config):
    """创建 PostgreSQL 引擎"""
    url_with_driver = _get_postgresql_url_with_driver(db_config.url)

    if db_config.is_stress_test:
        return create_engine(
            url_with_driver,
            connect_args=_get_postgresql_connect_args(db_config),
            poolclass=QueuePool,
            pool_size=db_config.stress_pool_size,
            max_overflow=db_config.stress_max_overflow,
            pool_timeout=db_config.stress_pool_timeout,
            pool_recycle=db_config.stress_pool_recycle,
            pool_pre_ping=True,
            echo=db_config.stress_echo,
        )
    elif app_config.debug:
        return create_engine(
            url_with_driver,
            connect_args=_get_postgresql_connect_args(db_config),
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
            connect_args=_get_postgresql_connect_args(db_config),
            poolclass=QueuePool,
            pool_size=db_config.pool_size,
            max_overflow=db_config.max_overflow,
            pool_timeout=db_config.pool_timeout,
            pool_recycle=db_config.pool_recycle,
            pool_pre_ping=True,
            echo=db_config.echo,
        )


def _create_engine_with_config(db_config, app_config):
    """
    根据配置创建数据库引擎

    Args:
        db_config: 数据库配置
        app_config: 应用配置

    Returns:
        Engine: SQLAlchemy引擎实例
    """
    db_type = db_config.db_type

    if db_type == "sqlite":
        return _create_sqlite_engine(db_config, app_config)
    elif db_type == "postgresql":
        return _create_postgresql_engine(db_config, app_config)
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")


def _setup_engine_events(engine, db_config):
    """设置引擎事件监听"""

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

def init_engine():
    """
    初始化数据库引擎

    在应用启动时调用，替代原来的模块级初始化
    """
    global _engine, SessionLocal

    if _engine is not None:
        return _engine

    config = get_config()
    db_config = config.database
    app_config = config.app

    # 验证数据库配置
    validation_passed = validate_database_config(db_config.url, db_config.db_type)
    if not validation_passed:
        logger.warning("数据库配置验证未通过，但应用仍将继续启动")

    # 检查 SQLite + 压力测试警告
    warning = check_sqlite_stress_test_warning(db_config.is_sqlite, db_config.is_stress_test)
    if warning:
        logger.warning(warning)

    # 创建引擎
    _engine = _create_engine_with_config(db_config, app_config)

    # 设置事件监听
    _setup_engine_events(_engine, db_config)

    # 创建会话工厂
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

    logger.info(f"数据库引擎初始化完成: {db_config.db_type}")
    return _engine


def get_engine() -> Engine:
    """
    获取数据库引擎实例

    Returns:
        Engine: SQLAlchemy引擎实例

    Raises:
        RuntimeError: 引擎未初始化时抛出
    """
    if _engine is None:
        raise RuntimeError("数据库引擎未初始化，请先调用 init_engine()")
    return _engine


def get_db_config():
    """
    获取当前数据库配置

    Returns:
        DatabaseSettings: 数据库配置对象
    """
    config = get_config()
    return config.database


# 导入所有模型（必须在 Base 定义之后）
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
    "Base", "SessionLocal", "BaseModel",
    "init_engine", "get_engine", "get_db_config",
    "User", "Repository", "RepositoryMember", "Branch", "Commit",
    "PullRequest", "PRComment", "PRReview", "Issue", "Label", "IssueComment",
    "Release", "ReleaseAsset",
    "WebHook", "WebHookDelivery",
]
