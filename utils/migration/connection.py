"""
数据库连接管理器

简化数据库连接和测试逻辑
"""
import re
from typing import Tuple, Optional
from urllib.parse import urlparse

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from utils.logging import get_named_logger
from utils.migration.dialect import DbType, Dialect

logger = get_named_logger("migration")


def create_database_if_not_exists(url: str, db_type: DbType) -> Tuple[bool, Optional[str]]:
    """
    如果数据库不存在，则自动创建数据库

    Args:
        url: 数据库连接 URL
        db_type: 数据库类型

    Returns:
        Tuple[bool, Optional[str]]: (是否成功, 错误信息)
    """
    if db_type == DbType.SQLITE:
        return True, None

    try:
        parsed = urlparse(url)
        database_name = parsed.path.lstrip("/") if parsed.path else None

        if not database_name:
            return False, "无法从 URL 中解析数据库名称"

        dialect = Dialect(db_type)

        if db_type == DbType.MYSQL:
            server_url = url.replace(f"/{database_name}", "", 1) if f"/{database_name}" in url else url
            server_url = dialect.to_sync_url(server_url)
            engine = create_engine(server_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            engine.dispose()
            logger.info(f"MySQL 数据库 '{database_name}' 已创建或已存在")
            return True, None

        if db_type == DbType.POSTGRESQL:
            server_url = url.replace(f"/{database_name}", "/postgres", 1) if f"/{database_name}" in url else url
            server_url = dialect.to_sync_url(server_url)
            engine = create_engine(server_url, pool_pre_ping=True)
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{database_name}'"))
                if not result.fetchone():
                    conn.commit()
                    conn.close()
                    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as autocommit_conn:
                        autocommit_conn.execute(text(f'CREATE DATABASE "{database_name}"'))
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


class Connection:
    """
    数据库连接管理器
    
    封装 SQLAlchemy 引擎和会话管理
    """
    
    def __init__(self, url: str):
        self.url = url
        self.db_type = DbType.detect(url)
        self.dialect = Dialect(self.db_type)
        self._engine = None
        self._inspector = None
    
    @property
    def engine(self):
        """获取同步引擎（延迟初始化）"""
        if self._engine is None:
            sync_url = self.dialect.to_sync_url(self.url)
            self._engine = create_engine(
                sync_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True
            )
        return self._engine
    
    @property
    def inspector(self):
        """获取数据库检查器"""
        if self._inspector is None:
            self._inspector = inspect(self.engine)
        return self._inspector
    
    def get_session(self):
        """获取数据库会话"""
        return sessionmaker(bind=self.engine)()
    
    def test_connection(self, auto_create_db: bool = True) -> Tuple[bool, Optional[str]]:
        """
        测试数据库连接

        Args:
            auto_create_db: 如果数据库不存在，是否自动创建

        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误信息)
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, None
        except Exception as e:
            error_msg = str(e)

            if auto_create_db and self.db_type in (DbType.MYSQL, DbType.POSTGRESQL):
                keywords = ["unknown database", "database.*does not exist", "1049"]
                if any(re.search(k, error_msg, re.IGNORECASE) for k in keywords):
                    logger.info(f"数据库不存在，尝试自动创建: {self.url}")
                    created, create_error = create_database_if_not_exists(self.url, self.db_type)
                    if created:
                        try:
                            with self.engine.connect() as conn:
                                conn.execute(text("SELECT 1"))
                            return True, None
                        except Exception as e2:
                            return False, f"数据库已创建但连接失败: {str(e2)}"
                    else:
                        return False, f"数据库不存在且自动创建失败: {create_error}"

            return False, error_msg
    
    def close(self):
        """关闭连接"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._inspector = None
    
    def execute(self, sql, params=None):
        """执行 SQL 语句"""
        if isinstance(sql, str):
            sql = text(sql)
        with self.engine.connect() as conn:
            if isinstance(params, list):
                conn.execute(sql, params)
            else:
                conn.execute(sql, params or {})
            conn.commit()
    
    def fetch_all(self, sql, params=None) -> list:
        """执行查询并返回所有结果"""
        if isinstance(sql, str):
            sql = text(sql)
        with self.engine.connect() as conn:
            result = conn.execute(sql, params or {})
            return result.fetchall()
    
    def fetch_one(self, sql, params=None):
        """执行查询并返回单条结果"""
        if isinstance(sql, str):
            sql = text(sql)
        with self.engine.connect() as conn:
            result = conn.execute(sql, params or {})
            return result.fetchone()
    
    def fetch_scalar(self, sql, params=None):
        """执行查询并返回标量值"""
        if isinstance(sql, str):
            sql = text(sql)
        with self.engine.connect() as conn:
            result = conn.execute(sql, params or {})
            return result.scalar()
