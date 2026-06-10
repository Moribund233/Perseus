"""
Database configuration validation module

Provides database driver detection and connection testing functionality
"""
import importlib.util
import logging
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class DatabaseValidationError(Exception):
    """Database configuration validation error"""
    pass


class DatabaseDriverNotFoundError(DatabaseValidationError):
    """Database driver not installed error"""
    pass


class DatabaseConnectionError(DatabaseValidationError):
    """Database connection failed error"""
    pass


def check_driver_installed(db_type: str, url: str = None) -> Tuple[bool, Optional[str]]:
    """
    Check if the database driver is installed
    
    Args:
        db_type: Database type (sqlite, postgresql)
        url: Database URL (optional,用于检测具体的驱动类型)
        
    Returns:
        Tuple[bool, Optional[str]]: (is_installed, error_message)
    """
    # SQLite is built into Python
    if db_type == "sqlite":
        return True, None
    
    # PostgreSQL: 使用 psycopg2
    if db_type == "postgresql":
        spec = importlib.util.find_spec("psycopg2")
        if spec is None:
            return False, "Driver 'psycopg2' not installed. Please install: pip install psycopg2-binary"
        return True, None
    
    return False, f"Unknown database type: {db_type}"


def validate_database_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate database URL format
    
    Args:
        url: Database connection URL
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not url or not url.strip():
        return False, "Database URL is empty"
    
    try:
        parsed = urlparse(url)
        
        if not parsed.scheme:
            return False, "Database URL missing scheme (e.g., sqlite://, postgresql://)"
        
        # Check supported schemes
        supported_schemes = ["sqlite", "postgresql", "postgres", "postgresql+psycopg2"]
        scheme = parsed.scheme.lower()
        
        if scheme not in supported_schemes:
            return False, f"Unsupported database scheme: {scheme}. Supported: {', '.join(supported_schemes)}"
        
        # For non-SQLite databases, check required components
        if not scheme.startswith("sqlite"):
            if not parsed.hostname:
                return False, "Database URL missing hostname"
            if not parsed.path or parsed.path == "/":
                return False, "Database URL missing database name"
        
        return True, None
        
    except Exception as e:
        return False, f"Invalid database URL format: {str(e)}"


def _get_url_with_driver(url: str, db_type: str) -> str:
    """
    将数据库 URL 转换为带驱动的格式

    Args:
        url: 原始数据库 URL
        db_type: 数据库类型

    Returns:
        str: 带驱动的 URL
    """
    url_lower = url.lower()
    if db_type == "postgresql" and url_lower.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif db_type == "postgresql" and url_lower.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url


def test_database_connection(url: str, db_type: str, timeout: int = 10, auto_create_db: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Test database connection

    Args:
        url: Database connection URL
        db_type: Database type
        timeout: Connection timeout in seconds
        auto_create_db: 如果数据库不存在，是否自动创建（仅对 PostgreSQL 有效）

    Returns:
        Tuple[bool, Optional[str]]: (is_connected, error_message)
    """
    try:
        # 转换 URL 为带驱动的格式
        test_url = _get_url_with_driver(url, db_type)

        # Create engine with short timeout for testing
        if db_type == "sqlite":
            engine = create_engine(test_url, connect_args={"timeout": timeout})
        elif db_type == "postgresql":
            engine = create_engine(test_url, connect_args={"connect_timeout": timeout}, pool_pre_ping=True)
        else:
            engine = create_engine(test_url)

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        engine.dispose()
        return True, None

    except SQLAlchemyError as e:
        error_msg = str(e)

        # 检查是否是数据库不存在的错误
        if auto_create_db and db_type == "postgresql":
            db_not_exist_keywords = [
                "unknown database",
                "database.*does not exist",
            ]
            if any(re.search(keyword, error_msg, re.IGNORECASE) for keyword in db_not_exist_keywords):
                # 注意：自动创建数据库功能已移除，请手动创建数据库
                logger.warning(f"数据库不存在，请手动创建: {url}")
                return False, f"数据库不存在，请手动创建: {error_msg}"

        if "password" in error_msg.lower() or "authentication" in error_msg.lower():
            return False, f"Authentication failed: {error_msg}"
        elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
            return False, f"Database does not exist: {error_msg}"
        elif "connection" in error_msg.lower():
            return False, f"Connection failed: {error_msg}"
        else:
            return False, f"Database error: {error_msg}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def validate_database_config(url: str, db_type: str) -> bool:
    """
    Validate database configuration comprehensively
    
    Args:
        url: Database connection URL
        db_type: Database type
        
    Returns:
        bool: 验证是否通过，失败时记录警告但不抛出异常
    """
    is_valid, error = validate_database_url(url)
    if not is_valid:
        logger.warning(f"Database URL validation failed: {error}")
        return False
    
    is_installed, error = check_driver_installed(db_type, url)
    if not is_installed:
        logger.warning(f"Database driver not found: {error}")
        return False
    
    is_connected, error = test_database_connection(url, db_type)
    if not is_connected:
        logger.warning(f"Database connection test failed: {error}")
    
    return True


def check_sqlite_stress_test_warning(is_sqlite: bool, is_stress_test: bool) -> Optional[str]:
    """
    Check if SQLite + stress test combination should show warning
    
    Args:
        is_sqlite: Whether using SQLite
        is_stress_test: Whether stress test mode is enabled
        
    Returns:
        Optional[str]: Warning message if applicable, None otherwise
    """
    if is_sqlite and is_stress_test:
        return """
================================================================================
WARNING: SQLite is not recommended for stress testing
================================================================================
SQLite has limited concurrency capabilities and may not provide accurate
stress test results. Consider using PostgreSQL for stress testing:

  DATABASE_URL=postgresql://user:pass@localhost/dbname

If you still want to use SQLite for stress testing, you can ignore this warning.
================================================================================
"""
    return None
