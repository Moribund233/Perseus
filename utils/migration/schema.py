"""
表结构模块

提供表结构提取、比较和迁移功能
"""
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from sqlalchemy import text

from utils.logging import get_named_logger
from utils.migration.connection import Connection
from utils.migration.dialect import DbType, Dialect

logger = get_named_logger("migration")


@dataclass
class ColumnInfo:
    """列信息"""
    name: str
    type: str
    nullable: bool = True
    default: Optional[str] = None
    autoincrement: bool = False
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "nullable": self.nullable,
            "default": self.default,
            "autoincrement": self.autoincrement
        }


@dataclass
class ForeignKeyInfo:
    """外键信息"""
    name: Optional[str] = None
    constrained_columns: List[str] = field(default_factory=list)
    referred_table: Optional[str] = None
    referred_columns: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "constrained_columns": self.constrained_columns,
            "referred_table": self.referred_table,
            "referred_columns": self.referred_columns
        }


@dataclass
class IndexInfo:
    """索引信息"""
    name: Optional[str] = None
    columns: List[str] = field(default_factory=list)
    unique: bool = False
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "columns": self.columns,
            "unique": self.unique
        }


@dataclass
class TableSchema:
    """表结构信息"""
    name: str
    columns: List[ColumnInfo] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[ForeignKeyInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "columns": [c.to_dict() for c in self.columns],
            "primary_keys": self.primary_keys,
            "foreign_keys": [fk.to_dict() for fk in self.foreign_keys],
            "indexes": [idx.to_dict() for idx in self.indexes]
        }


class TypeMapper:
    """类型映射工具类（保持向后兼容）"""
    
    @classmethod
    def normalize_type(cls, db_type: str, col_type: str) -> str:
        """标准化数据库类型为通用类型"""
        dialect = Dialect(DbType.detect(f"{db_type}://"))
        return dialect._normalize_type(col_type)
    
    @classmethod
    def map_type(cls, source_type: str, target_db_type: str) -> str:
        """将源数据库类型映射到目标数据库类型"""
        db_type = DbType(target_db_type) if isinstance(target_db_type, str) else target_db_type
        dialect = Dialect(db_type)
        return dialect.map_type(source_type)


class SchemaReader:
    """
    表结构读取器
    
    从数据库提取表结构信息
    """
    
    def __init__(self, connection: Connection):
        self.connection = connection
        self.inspector = connection.inspector
    
    def get_all_tables(self) -> List[str]:
        """获取所有表名"""
        return self.inspector.get_table_names()
    
    def get_table_schema(self, table_name: str) -> TableSchema:
        """获取表的完整结构信息"""
        columns = self._get_columns(table_name)
        primary_keys = self._get_primary_keys(table_name)
        foreign_keys = self._get_foreign_keys(table_name)
        indexes = self._get_indexes(table_name)
        
        return TableSchema(
            name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            indexes=indexes
        )
    
    def _get_columns(self, table_name: str) -> List[ColumnInfo]:
        """获取表的列信息"""
        cols = self.inspector.get_columns(table_name)
        return [
            ColumnInfo(
                name=col["name"],
                type=str(col["type"]),
                nullable=col.get("nullable", True),
                default=str(col.get("default")) if col.get("default") else None,
                autoincrement=col.get("autoincrement", False)
            )
            for col in cols
        ]
    
    def _get_primary_keys(self, table_name: str) -> List[str]:
        """获取表的主键列"""
        pk_constraint = self.inspector.get_pk_constraint(table_name)
        return pk_constraint.get("constrained_columns", [])
    
    def _get_foreign_keys(self, table_name: str) -> List[ForeignKeyInfo]:
        """获取表的外键信息"""
        fks = self.inspector.get_foreign_keys(table_name)
        return [
            ForeignKeyInfo(
                name=fk.get("name"),
                constrained_columns=list(fk.get("constrained_columns", [])),
                referred_table=fk.get("referred_table"),
                referred_columns=list(fk.get("referred_columns", []))
            )
            for fk in fks
        ]
    
    def _get_indexes(self, table_name: str) -> List[IndexInfo]:
        """获取表的索引信息"""
        idxs = self.inspector.get_indexes(table_name)
        return [
            IndexInfo(
                name=idx.get("name"),
                columns=list(idx.get("column_names", [])),
                unique=idx.get("unique", False)
            )
            for idx in idxs
        ]
    
    def get_all_schemas(self) -> Dict[str, TableSchema]:
        """获取所有表的结构信息"""
        return {table: self.get_table_schema(table) for table in self.get_all_tables()}


class SchemaComparator:
    """
    表结构比较器
    
    比较两个数据库的表结构差异
    """
    
    def __init__(self, source_reader: SchemaReader, target_reader: SchemaReader):
        self.source_reader = source_reader
        self.target_reader = target_reader
    
    def compare(self) -> Dict[str, Any]:
        """
        比较源数据库和目标数据库的表结构
        
        Returns:
            包含比较结果的字典
        """
        source_tables = set(self.source_reader.get_all_tables())
        target_tables = set(self.target_reader.get_all_tables())
        
        return {
            "source_tables": source_tables,
            "target_tables": target_tables,
            "missing_in_target": source_tables - target_tables,
            "missing_in_source": target_tables - source_tables,
            "common_tables": source_tables & target_tables,
            "source_empty": len(source_tables) == 0,
            "target_empty": len(target_tables) == 0
        }
    
    def compare_table(self, table_name: str) -> Dict[str, Any]:
        """比较单个表的结构差异"""
        source_schema = self.source_reader.get_table_schema(table_name)
        
        try:
            target_schema = self.target_reader.get_table_schema(table_name)
        except Exception:
            target_schema = None
        
        if not target_schema:
            return {
                "exists_in_target": False,
                "source_columns": {c.name: c.to_dict() for c in source_schema.columns}
            }
        
        source_cols = {c.name: c for c in source_schema.columns}
        target_cols = {c.name: c for c in target_schema.columns}
        
        return {
            "exists_in_target": True,
            "missing_columns": set(source_cols.keys()) - set(target_cols.keys()),
            "extra_columns": set(target_cols.keys()) - set(source_cols.keys()),
            "common_columns": set(source_cols.keys()) & set(target_cols.keys()),
            "source_columns": {k: v.to_dict() for k, v in source_cols.items()},
            "target_columns": {k: v.to_dict() for k, v in target_cols.items()}
        }


class SchemaMigrator:
    """
    表结构迁移器
    
    负责创建目标数据库的表结构
    """
    
    def __init__(self, source_conn: Connection, target_conn: Connection):
        self.source_conn = source_conn
        self.target_conn = target_conn
        self.source_reader = SchemaReader(source_conn)
        self.target_reader = SchemaReader(target_conn)
    
    def migrate(self, tables: Optional[List[str]] = None) -> Dict[str, tuple]:
        """
        迁移表结构
        
        Args:
            tables: 要迁移的表名列表，None 表示迁移所有表
        
        Returns:
            Dict[str, Tuple[bool, Optional[str]]]: 表名 -> (是否成功, 错误信息)
        """
        if tables is None:
            tables = self.source_reader.get_all_tables()
        
        results = {}
        target_tables = set(self.target_reader.get_all_tables())
        
        for table_name in tables:
            try:
                if table_name in target_tables:
                    logger.info(f"表 {table_name} 已存在，跳过创建")
                    results[table_name] = (True, None)
                    continue
                
                self._create_table(table_name)
                results[table_name] = (True, None)
                logger.info(f"表 {table_name} 创建成功")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"表 {table_name} 创建失败: {error_msg}")
                results[table_name] = (False, error_msg)
        
        self._add_foreign_keys(tables, results)
        self._create_indexes(tables, results)
        
        return results
    
    def _create_table(self, table_name: str):
        """创建表"""
        schema = self.source_reader.get_table_schema(table_name)
        dialect = self.target_conn.dialect
        
        sql = dialect.create_table(
            table=table_name,
            columns=[c.to_dict() for c in schema.columns],
            primary_keys=schema.primary_keys,
            foreign_keys=[]
        )
        
        logger.debug(f"执行建表 SQL: {sql}")
        self.target_conn.execute(sql)
    
    def _add_foreign_keys(self, tables: List[str], results: Dict[str, tuple]):
        """添加外键约束"""
        dialect = self.target_conn.dialect
        
        for table_name in tables:
            if not results.get(table_name, (False, None))[0]:
                continue
            
            schema = self.source_reader.get_table_schema(table_name)
            
            for fk in schema.foreign_keys:
                try:
                    sql = dialect.add_foreign_key(table_name, fk.to_dict())
                    if sql:
                        self.target_conn.execute(sql)
                        logger.info(f"外键 {fk.name} 添加成功")
                except Exception as e:
                    logger.warning(f"外键 {fk.name} 添加失败: {e}")
    
    def _create_indexes(self, tables: List[str], results: Dict[str, tuple]):
        """创建索引"""
        dialect = self.target_conn.dialect
        
        for table_name in tables:
            if not results.get(table_name, (False, None))[0]:
                continue
            
            schema = self.source_reader.get_table_schema(table_name)
            
            for idx in schema.indexes:
                if not idx.columns:
                    continue
                
                try:
                    idx_name = idx.name or f"idx_{table_name}_{'_'.join(idx.columns)}"
                    sql = dialect.create_index(table_name, idx_name, idx.columns, idx.unique)
                    self.target_conn.execute(sql)
                    logger.info(f"索引 {idx_name} 创建成功")
                except Exception as e:
                    logger.warning(f"索引 {idx.name} 创建失败: {e}")
