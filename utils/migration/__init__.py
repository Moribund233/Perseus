"""
数据库迁移模块

提供跨数据库迁移功能，支持 SQLite、MySQL、PostgreSQL
"""
from utils.migration.dialect import Dialect, DbType, detect_db_type
from utils.migration.connection import Connection, create_database_if_not_exists
from utils.migration.schema import SchemaReader, SchemaComparator, SchemaMigrator, TypeMapper

__all__ = [
    "Dialect",
    "DbType",
    "detect_db_type",
    "Connection",
    "create_database_if_not_exists",
    "SchemaReader",
    "SchemaComparator",
    "SchemaMigrator",
    "TypeMapper",
]
