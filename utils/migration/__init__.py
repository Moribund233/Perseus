"""
数据库迁移模块

提供跨数据库迁移功能，支持 SQLite、MySQL、PostgreSQL
"""
from utils.migration.dialect import Dialect, DbType, detect_db_type
from utils.migration.connection import Connection, create_database_if_not_exists
from utils.migration.schema import SchemaReader, SchemaComparator, SchemaMigrator, TypeMapper
from utils.migration.auto_dependency import DependencyResolver, get_table_dependencies, sort_tables_by_dependency

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
    "DependencyResolver",
    "get_table_dependencies",
    "sort_tables_by_dependency",
]
