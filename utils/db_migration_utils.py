"""
数据库迁移核心工具模块

提供数据库连接、类型检测、表结构映射等核心功能
"""
import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse
from datetime import datetime

from sqlalchemy import create_engine, inspect, MetaData, Table, Column, Integer, String, DateTime, Text, Boolean, Float, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.dialects import postgresql, mysql, sqlite

from config import get_config

logger = logging.getLogger(__name__)


def create_database_if_not_exists(url: str, db_type: str) -> Tuple[bool, Optional[str]]:
    """
    如果数据库不存在，则自动创建数据库

    Args:
        url: 数据库连接 URL
        db_type: 数据库类型 (mysql, postgresql, sqlite)

    Returns:
        Tuple[bool, Optional[str]]: (是否成功, 错误信息)
    """
    if db_type == "sqlite":
        # SQLite 数据库文件会在连接时自动创建
        return True, None

    try:
        parsed = urlparse(url)
        database_name = parsed.path.lstrip("/") if parsed.path else None

        if not database_name:
            return False, "无法从 URL 中解析数据库名称"

        if db_type == "mysql":
            # 构建连接到 MySQL 服务器（不指定数据库）的 URL
            # 将 URL 中的数据库名去掉，连接到 mysql 系统数据库或直接使用服务器地址
            server_url = url.replace(f"/{database_name}", "", 1) if f"/{database_name}" in url else url
            # 确保使用 pymysql 驱动
            if server_url.lower().startswith("mysql://"):
                server_url = server_url.replace("mysql://", "mysql+pymysql://", 1)

            engine = create_engine(server_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            engine.dispose()
            logger.info(f"MySQL 数据库 '{database_name}' 已创建或已存在")
            return True, None

        elif db_type == "postgresql":
            # 构建连接到 PostgreSQL 服务器（postgres 数据库）的 URL
            # 将 URL 中的数据库名替换为 postgres
            server_url = url.replace(f"/{database_name}", "/postgres", 1) if f"/{database_name}" in url else url
            # 确保使用 pg8000 驱动
            if server_url.lower().startswith("postgresql://"):
                server_url = server_url.replace("postgresql://", "postgresql+pg8000://", 1)
            elif server_url.lower().startswith("postgres://"):
                server_url = server_url.replace("postgres://", "postgresql+pg8000://", 1)

            engine = create_engine(server_url, pool_pre_ping=True)
            with engine.connect() as conn:
                # PostgreSQL 不支持 CREATE DATABASE IF NOT EXISTS，需要手动检查
                result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{database_name}'"))
                if not result.fetchone():
                    conn.execute(text(f"CREATE DATABASE \"{database_name}\""))
                    logger.info(f"PostgreSQL 数据库 '{database_name}' 已创建")
                else:
                    logger.info(f"PostgreSQL 数据库 '{database_name}' 已存在")
            engine.dispose()
            return True, None

        return False, f"不支持的数据库类型: {db_type}"

    except Exception as e:
        error_msg = str(e)
        logger.error(f"创建数据库失败: {error_msg}")
        return False, error_msg


class DatabaseType:
    """数据库类型枚举"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    UNKNOWN = "unknown"

    @staticmethod
    def detect(url: str) -> str:
        """从URL检测数据库类型"""
        parsed = urlparse(url.lower())
        scheme = parsed.scheme
        if scheme.startswith("sqlite"):
            return DatabaseType.SQLITE
        elif scheme.startswith("postgresql") or scheme.startswith("postgres"):
            return DatabaseType.POSTGRESQL
        elif scheme.startswith("mysql"):
            return DatabaseType.MYSQL
        return DatabaseType.UNKNOWN

    @staticmethod
    def convert_to_async_url(url: str) -> str:
        """将同步URL转换为异步URL (SQLAlchemy async)"""
        url_lower = url.lower()
        
        if url_lower.startswith("sqlite"):
            return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        elif url_lower.startswith("postgresql+psycopg2://"):
            return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        elif url_lower.startswith("postgresql+pg8000://"):
            return url.replace("postgresql+pg8000://", "postgresql+asyncpg://", 1)
        elif url_lower.startswith("postgresql://") or url_lower.startswith("postgres://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1).replace("postgres://", "postgresql+asyncpg://", 1)
        elif url_lower.startswith("mysql+pymysql://"):
            return url.replace("mysql+pymysql://", "mysql+aiomysql://", 1)
        elif url_lower.startswith("mysql://"):
            return url.replace("mysql://", "mysql+aiomysql://", 1)
        return url


class MigrationConnection:
    """
    数据库迁移连接管理器
    
    管理源数据库和目标数据库的连接，支持同步/异步操作
    """
    
    def __init__(self, url: str, is_async: bool = False):
        self.url = url
        self.is_async = is_async
        self.db_type = DatabaseType.detect(url)
        self._engine = None
        self._async_engine = None
        self._session_factory = None
        self._async_session_factory = None
    
    def _get_sync_url_with_driver(self, url: str) -> str:
        """将 URL 转换为带驱动的格式（同步）"""
        url_lower = url.lower()
        if url_lower.startswith("mysql://"):
            return url.replace("mysql://", "mysql+pymysql://", 1)
        elif url_lower.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+pg8000://", 1)
        elif url_lower.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+pg8000://", 1)
        return url

    @property
    def engine(self):
        """获取同步引擎"""
        if self._engine is None:
            sync_url = self._get_sync_url_with_driver(self.url)
            self._engine = create_engine(
                sync_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True
            )
        return self._engine
    
    @property
    def async_engine(self):
        """获取异步引擎"""
        if self._async_engine is None:
            async_url = DatabaseType.convert_to_async_url(self.url)
            self._async_engine = create_async_engine(
                async_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True
            )
        return self._async_engine
    
    @property
    def session_factory(self):
        """获取同步会话工厂"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory
    
    @property
    def async_session_factory(self):
        """获取异步会话工厂"""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        return self._async_session_factory
    
    def get_session(self):
        """获取同步会话"""
        return self.session_factory()
    
    async def get_async_session(self) -> AsyncSession:
        """获取异步会话"""
        return self.async_session_factory()
    
    def get_inspector(self):
        """获取表检查器"""
        return inspect(self.engine)
    
    def get_metadata(self) -> MetaData:
        """获取数据库元数据"""
        return MetaData(bind=self.engine)
    
    def close(self):
        """关闭所有连接"""
        if self._engine:
            self._engine.dispose()
        if self._async_engine:
            self._async_engine.dispose()
    
    def test_connection(self, auto_create_db: bool = True) -> Tuple[bool, Optional[str]]:
        """
        测试数据库连接

        Args:
            auto_create_db: 如果数据库不存在，是否自动创建（仅对 MySQL/PostgreSQL 有效）

        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误信息)
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, None
        except Exception as e:
            error_msg = str(e)

            # 检查是否是数据库不存在的错误
            if auto_create_db and self.db_type in ("mysql", "postgresql"):
                db_not_exist_keywords = [
                    "unknown database",
                    "database.*does not exist",
                    "1049",  # MySQL error code for unknown database
                ]
                import re
                if any(re.search(keyword, error_msg, re.IGNORECASE) for keyword in db_not_exist_keywords):
                    logger.info(f"数据库不存在，尝试自动创建: {self.url}")
                    created, create_error = create_database_if_not_exists(self.url, self.db_type)
                    if created:
                        # 重新尝试连接
                        try:
                            with self.engine.connect() as conn:
                                conn.execute(text("SELECT 1"))
                            return True, None
                        except Exception as e2:
                            return False, f"数据库已创建但连接失败: {str(e2)}"
                    else:
                        return False, f"数据库不存在且自动创建失败: {create_error}"

            return False, error_msg


class TableSchemaExtractor:
    """
    表结构提取器
    
    从源数据库提取表结构信息，用于生成目标数据库的建表语句
    """
    
    def __init__(self, connection: MigrationConnection):
        self.connection = connection
        self.inspector = connection.get_inspector()
    
    def get_all_tables(self) -> List[str]:
        """获取所有表名"""
        return self.inspector.get_table_names()
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        columns = self.inspector.get_columns(table_name)
        return [
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "default": str(col.get("default")) if col.get("default") else None,
                "autoincrement": col.get("autoincrement", False)
            }
            for col in columns
        ]
    
    def get_table_primary_keys(self, table_name: str) -> List[str]:
        """获取表的主键列"""
        return self.inspector.get_pk_constraint(table_name).get("constrained_columns", [])
    
    def get_table_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的外键信息"""
        fks = self.inspector.get_foreign_keys(table_name)
        return [
            {
                "name": fk.get("name"),
                "constrained_columns": fk.get("constrained_columns", []),
                "referred_table": fk.get("referred_table"),
                "referred_columns": fk.get("referred_columns", [])
            }
            for fk in fks
        ]
    
    def get_table_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的索引信息"""
        indexes = self.inspector.get_indexes(table_name)
        return [
            {
                "name": idx.get("name"),
                "columns": idx.get("column_names", []),
                "unique": idx.get("unique", False)
            }
            for idx in indexes
        ]
    
    def get_table_schema_info(self, table_name: str) -> Dict[str, Any]:
        """获取表的完整结构信息"""
        return {
            "columns": self.get_table_columns(table_name),
            "primary_keys": self.get_table_primary_keys(table_name),
            "foreign_keys": self.get_table_foreign_keys(table_name),
            "indexes": self.get_table_indexes(table_name)
        }
    
    def get_all_tables_schema(self) -> Dict[str, Any]:
        """获取所有表的结构信息"""
        tables = self.get_all_tables()
        return {table: self.get_table_schema_info(table) for table in tables}


class TypeMapper:
    """
    数据库类型映射器
    
    处理不同数据库之间的数据类型转换
    """
    
    # PostgreSQL 类型映射
    POSTGRESQL_TYPE_MAP = {
        "INTEGER": "INTEGER",
        "BIGINT": "BIGINT",
        "SMALLINT": "SMALLINT",
        "VARCHAR": "VARCHAR",
        "TEXT": "TEXT",
        "BOOLEAN": "BOOLEAN",
        "DATE": "DATE",
        "TIME": "TIME",
        "TIMESTAMP": "TIMESTAMP",
        "DATETIME": "TIMESTAMP",
        "FLOAT": "REAL",
        "DOUBLE": "DOUBLE PRECISION",
        "DECIMAL": "DECIMAL",
        "BLOB": "BYTEA",
        "JSON": "JSONB",
        "JSONB": "JSONB"
    }
    
    # MySQL 类型映射
    MYSQL_TYPE_MAP = {
        "INTEGER": "INT",
        "BIGINT": "BIGINT",
        "SMALLINT": "SMALLINT",
        "VARCHAR": "VARCHAR(255)",
        "TEXT": "TEXT",
        "BOOLEAN": "TINYINT(1)",
        "DATE": "DATE",
        "TIME": "TIME",
        "TIMESTAMP": "TIMESTAMP",
        "DATETIME": "DATETIME",
        "FLOAT": "FLOAT",
        "DOUBLE": "DOUBLE",
        "DECIMAL": "DECIMAL(10,2)",
        "BLOB": "BLOB",
        "JSON": "JSON",
        "JSONB": "JSON"
    }
    
    # SQLite 类型映射
    SQLITE_TYPE_MAP = {
        "INTEGER": "INTEGER",
        "BIGINT": "INTEGER",
        "SMALLINT": "INTEGER",
        "VARCHAR": "TEXT",
        "TEXT": "TEXT",
        "BOOLEAN": "INTEGER",
        "DATE": "TEXT",
        "TIME": "TEXT",
        "TIMESTAMP": "TEXT",
        "DATETIME": "TEXT",
        "FLOAT": "REAL",
        "DOUBLE": "REAL",
        "DECIMAL": "REAL",
        "BLOB": "BLOB",
        "JSON": "TEXT",
        "JSONB": "TEXT"
    }
    
    @classmethod
    def map_type(cls, source_type: str, target_db_type: str) -> str:
        """将源数据库类型映射到目标数据库类型"""
        source_type_upper = source_type.upper()
        
        if target_db_type == DatabaseType.POSTGRESQL:
            return cls.POSTGRESQL_TYPE_MAP.get(source_type_upper, "TEXT")
        elif target_db_type == DatabaseType.MYSQL:
            return cls.MYSQL_TYPE_MAP.get(source_type_upper, "TEXT")
        elif target_db_type == DatabaseType.SQLITE:
            return cls.SQLITE_TYPE_MAP.get(source_type_upper, "TEXT")
        
        return "TEXT"
    
    @classmethod
    def normalize_type(cls, db_type: str, col_type: str) -> str:
        """
        标准化数据库类型为通用类型

        处理 SQLAlchemy 类型字符串，如 VARCHAR(length=255), INTEGER(), etc.
        """
        import re

        # 提取类型名称（去掉括号及其内容）
        # 例如: VARCHAR(length=255) -> VARCHAR, INTEGER() -> INTEGER
        match = re.match(r'(\w+)', col_type.upper())
        if not match:
            return "TEXT"

        type_name = match.group(1)

        if type_name in ("INT", "INTEGER"):
            if "BIGINT" in col_type.upper():
                return "BIGINT"
            elif "SMALLINT" in col_type.upper():
                return "SMALLINT"
            return "INTEGER"
        elif type_name in ("VARCHAR", "CHAR", "NVARCHAR", "NCHAR"):
            return "VARCHAR"
        elif type_name == "TEXT":
            return "TEXT"
        elif type_name in ("BOOL", "BOOLEAN"):
            return "BOOLEAN"
        elif type_name == "DATE" and "TIME" not in col_type.upper():
            return "DATE"
        elif type_name == "TIME" and "DATE" not in col_type.upper():
            return "TIME"
        elif type_name in ("TIMESTAMP", "DATETIME"):
            return "DATETIME"
        elif type_name in ("FLOAT", "REAL"):
            return "FLOAT"
        elif type_name == "DOUBLE":
            return "DOUBLE"
        elif type_name in ("DECIMAL", "NUMERIC"):
            return "DECIMAL"
        elif type_name in ("BLOB", "BYTEA", "BINARY", "VARBINARY"):
            return "BLOB"
        elif type_name in ("JSON", "JSONB"):
            return "JSON"

        return "TEXT"


def get_source_connection() -> MigrationConnection:
    """获取源数据库连接（当前应用的数据库）"""
    config = get_config()
    source_url = config.database.url
    return MigrationConnection(source_url)


def create_target_connection(target_url: str) -> MigrationConnection:
    """创建目标数据库连接"""
    return MigrationConnection(target_url)
