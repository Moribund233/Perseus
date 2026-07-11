"""
Schema drift 检测测试

验证 SQLAlchemy 模型定义 vs 实际数据库 schema 一致。
对比所有模型列与实际表，发现缺失列即测试失败。

这能捕获类似 `star_count` 列在 PostgreSQL 中缺失的问题
（SQLite 的 create_all 会补列，PG 不会，导致 schema drift）。
"""
import pytest
from sqlalchemy import inspect

from models import Base


def get_model_columns(test_engine) -> dict:
    """返回 {table_name: {column_name}}"""
    inspector = inspect(test_engine)
    result = {}
    for table_name, table in Base.metadata.tables.items():
        result[table_name] = {col.name for col in table.columns}
    return result


def get_db_columns(test_engine) -> dict:
    """返回 {table_name: {column_name}} 从实际数据库"""
    inspector = inspect(test_engine)
    return {
        name: {col["name"] for col in inspector.get_columns(name)}
        for name in inspector.get_table_names()
    }


def test_all_models_match_database(test_engine):
    """所有 SQLAlchemy 模型表都存在于数据库中"""
    model_tables = set(Base.metadata.tables.keys())
    db_tables = set(inspect(test_engine).get_table_names())

    missing = model_tables - db_tables
    assert not missing, f"数据库中缺少表: {missing}"


def test_no_missing_columns(test_engine):
    """每个模型的所有列都存在于实际数据库表中"""
    model_data = get_model_columns(test_engine)
    db_data = get_db_columns(test_engine)

    errors = []
    for table_name, model_cols in model_data.items():
        if table_name not in db_data:
            continue
        db_cols = db_data[table_name]
        missing = model_cols - db_cols
        if missing:
            errors.append(f"  表 '{table_name}' 缺少列: {missing}")

    assert not errors, f"Schema drift 检测到缺失列:\n" + "\n".join(errors)


def test_no_extra_columns(test_engine):
    """数据库中无模型未定义的列（warning 级别，容忍迁移中间状态）"""
    model_data = get_model_columns(test_engine)
    db_data = get_db_columns(test_engine)

    for table_name, db_cols in db_data.items():
        if table_name not in model_data:
            continue
        extra = db_cols - model_data[table_name]
        if extra:
            import warnings
            warnings.warn(
                f"表 '{table_name}' 有多余列: {extra}. "
                "如非 Alembic 迁移中间状态，建议清理。"
            )
