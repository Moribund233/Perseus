"""
SQL 方言适配器

统一处理不同数据库的 SQL 语法差异
"""
import re
from enum import Enum
from typing import Optional, List
from urllib.parse import urlparse


class DbType(str, Enum):
    """数据库类型枚举"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"

    @classmethod
    def detect(cls, url: str) -> "DbType":
        """从 URL 检测数据库类型"""
        scheme = urlparse(url.lower()).scheme
        if scheme.startswith("sqlite"):
            return cls.SQLITE
        elif scheme.startswith("postgresql") or scheme.startswith("postgres"):
            return cls.POSTGRESQL
        elif scheme.startswith("mysql"):
            return cls.MYSQL
        return cls.SQLITE


detect_db_type = DbType.detect


class Dialect:
    """
    SQL 方言适配器
    
    封装不同数据库的 SQL 语法差异
    """
    
    TYPE_MAPS = {
        DbType.SQLITE: {
            "INTEGER": "INTEGER", "BIGINT": "INTEGER", "SMALLINT": "INTEGER",
            "VARCHAR": "TEXT", "TEXT": "TEXT", "BOOLEAN": "INTEGER",
            "DATE": "TEXT", "TIME": "TEXT", "TIMESTAMP": "TEXT", "DATETIME": "TEXT",
            "FLOAT": "REAL", "DOUBLE": "REAL", "DECIMAL": "REAL",
            "BLOB": "BLOB", "JSON": "TEXT", "JSONB": "TEXT",
        },
        DbType.POSTGRESQL: {
            "INTEGER": "INTEGER", "BIGINT": "BIGINT", "SMALLINT": "SMALLINT",
            "VARCHAR": "VARCHAR", "TEXT": "TEXT", "BOOLEAN": "BOOLEAN",
            "DATE": "DATE", "TIME": "TIME", "TIMESTAMP": "TIMESTAMP", "DATETIME": "TIMESTAMP",
            "FLOAT": "REAL", "DOUBLE": "DOUBLE PRECISION", "DECIMAL": "DECIMAL",
            "BLOB": "BYTEA", "JSON": "JSONB", "JSONB": "JSONB",
        },
        DbType.MYSQL: {
            "INTEGER": "INT", "BIGINT": "BIGINT", "SMALLINT": "SMALLINT",
            "VARCHAR": "VARCHAR(255)", "TEXT": "TEXT", "BOOLEAN": "TINYINT(1)",
            "DATE": "DATE", "TIME": "TIME", "TIMESTAMP": "TIMESTAMP", "DATETIME": "DATETIME",
            "FLOAT": "FLOAT", "DOUBLE": "DOUBLE", "DECIMAL": "DECIMAL(10,2)",
            "BLOB": "BLOB", "JSON": "JSON", "JSONB": "JSON",
        },
    }
    
    def __init__(self, db_type: DbType):
        self.db_type = db_type
        self._is_mysql = db_type == DbType.MYSQL
        self._is_pg = db_type == DbType.POSTGRESQL
        self._is_sqlite = db_type == DbType.SQLITE
    
    @property
    def quote(self) -> str:
        """标识符引号"""
        return "`" if self._is_mysql else '"'
    
    def quote_ident(self, name: str) -> str:
        """引用标识符"""
        return f"{self.quote}{name}{self.quote}"
    
    def map_type(self, source_type: str) -> str:
        """将标准化类型映射到目标数据库类型"""
        type_map = self.TYPE_MAPS.get(self.db_type, {})
        normalized = self._normalize_type(source_type)
        return type_map.get(normalized, "TEXT")
    
    def _normalize_type(self, col_type: str) -> str:
        """标准化数据库类型"""
        match = re.match(r"(\w+)", col_type.upper())
        if not match:
            return "TEXT"
        
        name = match.group(1)
        upper = col_type.upper()
        
        if name in ("INT", "INTEGER"):
            if "BIGINT" in upper: return "BIGINT"
            if "SMALLINT" in upper: return "SMALLINT"
            return "INTEGER"
        if name in ("VARCHAR", "CHAR", "NVARCHAR", "NCHAR"): return "VARCHAR"
        if name == "TEXT": return "TEXT"
        if name in ("BOOL", "BOOLEAN"): return "BOOLEAN"
        if name == "DATE" and "TIME" not in upper: return "DATE"
        if name == "TIME" and "DATE" not in upper: return "TIME"
        if name in ("TIMESTAMP", "DATETIME"): return "DATETIME"
        if name in ("FLOAT", "REAL"): return "FLOAT"
        if name == "DOUBLE": return "DOUBLE"
        if name in ("DECIMAL", "NUMERIC"): return "DECIMAL"
        if name in ("BLOB", "BYTEA", "BINARY", "VARBINARY"): return "BLOB"
        if name in ("JSON", "JSONB"): return "JSON"
        return "TEXT"
    
    def insert_on_conflict(self, table: str, columns: List[str]) -> str:
        """生成 INSERT ON CONFLICT 语句"""
        cols = ", ".join(columns)
        placeholders = ", ".join(f":{c}" for c in columns)
        table_q = self.quote_ident(table)
        
        if self._is_pg:
            return f"INSERT INTO {table_q} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        if self._is_mysql:
            return f"INSERT IGNORE INTO {table_q} ({cols}) VALUES ({placeholders})"
        return f"INSERT OR IGNORE INTO {table_q} ({cols}) VALUES ({placeholders})"
    
    def create_table(
        self,
        table: str,
        columns: List[dict],
        primary_keys: List[str] = None,
        foreign_keys: List[dict] = None,
    ) -> str:
        """
        生成 CREATE TABLE 语句
        
        Args:
            table: 表名
            columns: 列定义列表 [{"name": str, "type": str, "nullable": bool, "default": str, "autoincrement": bool}]
            primary_keys: 主键列名列表
            foreign_keys: 外键定义列表
        """
        defs = []
        pk_cols = set(primary_keys or [])
        
        for col in columns:
            col_def = self._build_column_def(col, pk_cols)
            defs.append(col_def)
        
        if pk_cols and not (self._is_sqlite and len(pk_cols) == 1):
            pk_str = ", ".join(self.quote_ident(pk) for pk in primary_keys)
            defs.append(f"PRIMARY KEY ({pk_str})")
        
        for fk in foreign_keys or []:
            fk_def = self._build_foreign_key_def(table, fk)
            if fk_def:
                defs.append(fk_def)
        
        return f"CREATE TABLE {self.quote_ident(table)} ({', '.join(defs)})"
    
    def _build_column_def(self, col: dict, pk_cols: set) -> str:
        """构建列定义"""
        name = col["name"]
        col_type = self.map_type(col["type"])
        nullable = col.get("nullable", True)
        default = col.get("default")
        autoincrement = col.get("autoincrement", False)
        is_pk = name in pk_cols
        
        if self._is_sqlite and is_pk and autoincrement:
            return f'{self.quote_ident(name)} INTEGER PRIMARY KEY AUTOINCREMENT'
        
        parts = [self.quote_ident(name), col_type]
        
        if autoincrement and not self._is_sqlite:
            if self._is_mysql:
                parts.append("AUTO_INCREMENT")
            elif self._is_pg:
                pass
        elif not nullable:
            parts.append("NOT NULL")
        
        if default and not autoincrement:
            converted = self._convert_default(default)
            if converted:
                parts.append(f"DEFAULT {converted}")
        
        return " ".join(parts)
    
    def _convert_default(self, default: str) -> Optional[str]:
        """转换默认值"""
        if not default or default == "None":
            return None
        
        lower = default.lower()
        
        if "nextval" in lower:
            return None if not self._is_pg else default
        
        if "now()" in lower or "current_timestamp" in lower:
            return "NOW()" if self._is_pg else "CURRENT_TIMESTAMP"
        
        return default
    
    def _build_foreign_key_def(self, table: str, fk: dict) -> Optional[str]:
        """构建外键定义"""
        constrained = fk.get("constrained_columns", [])
        referred_table = fk.get("referred_table")
        referred_cols = fk.get("referred_columns", [])
        
        if not (constrained and referred_table and referred_cols):
            return None
        
        fk_name = fk.get("name") or f"fk_{table}_{referred_table}"
        cols = ", ".join(self.quote_ident(c) for c in constrained)
        ref_cols = ", ".join(self.quote_ident(c) for c in referred_cols)
        
        if self._is_sqlite:
            return f"FOREIGN KEY ({cols}) REFERENCES {self.quote_ident(referred_table)} ({ref_cols})"
        
        return (
            f"CONSTRAINT {self.quote_ident(fk_name)} "
            f"FOREIGN KEY ({cols}) REFERENCES {self.quote_ident(referred_table)} ({ref_cols})"
        )
    
    def create_index(
        self,
        table: str,
        index_name: str,
        columns: List[str],
        unique: bool = False,
    ) -> str:
        """生成 CREATE INDEX 语句"""
        unique_str = "UNIQUE " if unique else ""
        cols = ", ".join(self.quote_ident(c) for c in columns)
        return f"CREATE {unique_str}INDEX {self.quote_ident(index_name)} ON {self.quote_ident(table)} ({cols})"
    
    def add_foreign_key(self, table: str, fk: dict) -> Optional[str]:
        """生成 ALTER TABLE ADD FOREIGN KEY 语句"""
        if self._is_sqlite:
            return None
        
        fk_def = self._build_foreign_key_def(table, fk)
        if not fk_def:
            return None
        
        return f"ALTER TABLE {self.quote_ident(table)} ADD {fk_def}"
    
    def to_sync_url(self, url: str) -> str:
        """转换为同步驱动 URL"""
        lower = url.lower()
        if lower.startswith("mysql://"):
            return url.replace("mysql://", "mysql+pymysql://", 1)
        if lower.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+pg8000://", 1)
        if lower.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+pg8000://", 1)
        return url
    
    def to_async_url(self, url: str) -> str:
        """转换为异步驱动 URL"""
        lower = url.lower()
        if lower.startswith("sqlite"):
            return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        if lower.startswith(("postgresql+psycopg2://", "postgresql+pg8000://", "postgresql://", "postgres://")):
            for prefix in ["postgresql+psycopg2://", "postgresql+pg8000://", "postgresql://", "postgres://"]:
                if lower.startswith(prefix):
                    return url.replace(prefix, "postgresql+asyncpg://", 1)
        if lower.startswith("mysql+pymysql://"):
            return url.replace("mysql+pymysql://", "mysql+aiomysql://", 1)
        if lower.startswith("mysql://"):
            return url.replace("mysql://", "mysql+aiomysql://", 1)
        return url
