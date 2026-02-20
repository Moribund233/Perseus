"""
Database configuration validation module

Provides database driver detection and connection testing functionality
"""
import importlib.util
import logging
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


def check_driver_installed(db_type: str) -> Tuple[bool, Optional[str]]:
    """
    Check if the database driver is installed
    
    Args:
        db_type: Database type (sqlite, postgresql, mysql)
        
    Returns:
        Tuple[bool, Optional[str]]: (is_installed, error_message)
    """
    driver_modules = {
        "sqlite": ("sqlite3", "SQLite support is built into Python"),
        "postgresql": ("psycopg2", "Please install: pip install psycopg2-binary"),
        "mysql": ("pymysql", "Please install: pip install pymysql cryptography"),
    }
    
    if db_type not in driver_modules:
        return False, f"Unknown database type: {db_type}"
    
    module_name, install_hint = driver_modules[db_type]
    
    # SQLite is built into Python
    if db_type == "sqlite":
        return True, None
    
    # Check if module is available
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return False, f"Driver '{module_name}' not installed. {install_hint}"
    
    return True, None


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
        supported_schemes = ["sqlite", "postgresql", "postgres", "mysql", "mysql+pymysql"]
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


def test_database_connection(url: str, db_type: str, timeout: int = 10) -> Tuple[bool, Optional[str]]:
    """
    Test database connection
    
    Args:
        url: Database connection URL
        db_type: Database type
        timeout: Connection timeout in seconds
        
    Returns:
        Tuple[bool, Optional[str]]: (is_connected, error_message)
    """
    try:
        # Create engine with short timeout for testing
        if db_type == "sqlite":
            engine = create_engine(url, connect_args={"timeout": timeout})
        elif db_type == "postgresql":
            engine = create_engine(url, connect_args={"connect_timeout": timeout})
        elif db_type == "mysql":
            engine = create_engine(url, connect_args={"connect_timeout": timeout * 1000})  # MySQL uses milliseconds
        else:
            engine = create_engine(url)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        engine.dispose()
        return True, None
        
    except SQLAlchemyError as e:
        error_msg = str(e)
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


def validate_database_config(url: str, db_type: str) -> None:
    """
    Validate database configuration comprehensively
    
    Args:
        url: Database connection URL
        db_type: Database type
        
    Raises:
        DatabaseValidationError: When validation fails
    """
    logger.info(f"Validating database configuration: {db_type}")
    
    # 1. Validate URL format
    is_valid, error = validate_database_url(url)
    if not is_valid:
        raise DatabaseValidationError(f"Invalid database URL: {error}")
    
    # 2. Check driver installation
    is_installed, error = check_driver_installed(db_type)
    if not is_installed:
        raise DatabaseDriverNotFoundError(f"Driver not found: {error}")
    
    # 3. Test connection
    is_connected, error = test_database_connection(url, db_type)
    if not is_connected:
        raise DatabaseConnectionError(f"Connection failed: {error}")
    
    logger.info(f"Database validation passed: {db_type}")


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
stress test results. Consider using PostgreSQL or MySQL for stress testing:

  DATABASE_URL=postgresql://user:pass@localhost/dbname
  DATABASE_URL=mysql+pymysql://user:pass@localhost/dbname

If you still want to use SQLite for stress testing, you can ignore this warning.
================================================================================
"""
    return None
