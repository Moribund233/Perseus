"""
数据库迁移服务

提供数据迁移功能，支持批量迁移、分批提交、断点续传
"""
import logging
import time
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from utils.db_migration_utils import (
    DatabaseType,
    MigrationConnection,
    TableSchemaExtractor,
    TypeMapper,
    get_source_connection,
    create_target_connection
)
from utils.logging import get_named_logger

logger = get_named_logger("migration_service")


@dataclass
class MigrationProgress:
    """迁移进度"""
    table_name: str
    total_rows: int
    migrated_rows: int
    status: str  # "pending", "in_progress", "completed", "failed"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class MigrationResult:
    """迁移结果"""
    success: bool
    tables_migrated: int
    tables_failed: int
    total_rows_migrated: int
    total_rows_failed: int
    duration_seconds: float
    table_progress: List[MigrationProgress] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    skipped: bool = False  # 是否被跳过
    skip_reason: Optional[str] = None  # 跳过原因


class TableMigrator:
    """
    单表迁移器
    
    负责单个表的数据迁移，支持批量插入和断点续传
    """
    
    def __init__(
        self,
        source_conn: MigrationConnection,
        target_conn: MigrationConnection,
        batch_size: int = 1000
    ):
        self.source_conn = source_conn
        self.target_conn = target_conn
        self.batch_size = batch_size
    
    def migrate_table(
        self,
        table_name: str,
        progress_callback: Optional[Callable] = None
    ) -> MigrationProgress:
        """迁移单个表的数据"""
        progress = MigrationProgress(
            table_name=table_name,
            total_rows=0,
            migrated_rows=0,
            status="in_progress",
            started_at=datetime.now()
        )
        
        try:
            total_rows = self._get_source_row_count(table_name)
            progress.total_rows = total_rows
            
            if total_rows == 0:
                progress.status = "completed"
                progress.completed_at = datetime.now()
                return progress
            
            migrated = self._migrate_data(table_name, progress_callback)
            progress.migrated_rows = migrated
            progress.status = "completed"
            progress.completed_at = datetime.now()
            
        except Exception as e:
            progress.status = "failed"
            progress.error_message = str(e)
            progress.completed_at = datetime.now()
            logger.error(f"表 {table_name} 迁移失败: {e}")
        
        return progress
    
    def _get_source_row_count(self, table_name: str) -> int:
        """获取源表行数"""
        with self.source_conn.engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar()
    
    def _migrate_data(
        self,
        table_name: str,
        progress_callback: Optional[Callable] = None
    ) -> int:
        """迁移数据"""
        inspector = self.target_conn.get_inspector()
        target_columns_info = inspector.get_columns(table_name)
        target_columns = [col["name"] for col in target_columns_info]

        source_columns = self._get_source_columns(table_name)
        common_columns = [col for col in source_columns if col in target_columns]

        if not common_columns:
            raise ValueError(f"表 {table_name} 没有可迁移的公共列")

        # 获取目标数据库的列类型信息，用于类型转换
        target_column_types = {col["name"]: col["type"] for col in target_columns_info}

        column_list = ", ".join(common_columns)
        placeholders = ", ".join([f":{col}" for col in common_columns])

        # 根据目标数据库类型选择不同的冲突处理语法
        target_db_type = self.target_conn.db_type
        if target_db_type == DatabaseType.POSTGRESQL:
            insert_sql = text(f"""
                INSERT INTO {table_name} ({column_list})
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """)
        elif target_db_type == DatabaseType.MYSQL:
            insert_sql = text(f"""
                INSERT IGNORE INTO {table_name} ({column_list})
                VALUES ({placeholders})
            """)
        else:
            # SQLite 和其他数据库使用标准 INSERT OR IGNORE
            insert_sql = text(f"""
                INSERT OR IGNORE INTO {table_name} ({column_list})
                VALUES ({placeholders})
            """)

        offset = 0
        migrated = 0

        while True:
            select_sql = text(f"""
                SELECT {column_list}
                FROM {table_name}
                LIMIT :limit OFFSET :offset
            """)

            with self.source_conn.engine.connect() as conn:
                result = conn.execute(select_sql, {"limit": self.batch_size, "offset": offset})
                rows = result.fetchall()

            if not rows:
                break

            # 转换数据类型
            batch_data = []
            for row in rows:
                row_dict = dict(zip(common_columns, row))
                # 根据目标列类型进行转换
                for col in common_columns:
                    if col in target_column_types:
                        target_type = str(target_column_types[col]).lower()
                        value = row_dict[col]
                        # 布尔类型转换：整数 0/1 转换为布尔值
                        if 'bool' in target_type and isinstance(value, int):
                            row_dict[col] = bool(value)
                        # 处理 None 值
                        elif value is None:
                            continue
                batch_data.append(row_dict)

            with self.target_conn.engine.connect() as conn:
                conn.execute(insert_sql, batch_data)
                conn.commit()

            migrated += len(batch_data)
            offset += self.batch_size

            if progress_callback:
                progress_callback(table_name, migrated)

        return migrated
    
    def _get_source_columns(self, table_name: str) -> List[str]:
        """获取源表列名"""
        inspector = self.source_conn.get_inspector()
        return [col["name"] for col in inspector.get_columns(table_name)]


class SchemaMigrator:
    """
    表结构迁移器
    
    负责创建目标数据库的表结构
    """
    
    def __init__(self, source_conn: MigrationConnection, target_conn: MigrationConnection):
        self.source_conn = source_conn
        self.target_conn = target_conn
        self.source_extractor = TableSchemaExtractor(source_conn)
        self.target_extractor = TableSchemaExtractor(target_conn)
    
    def migrate_schema(self, tables: Optional[List[str]] = None) -> Dict[str, Tuple[bool, Optional[str]]]:
        """
        迁移表结构

        Args:
            tables: 要迁移的表名列表，None表示迁移所有表

        Returns:
            Dict[str, Tuple[bool, Optional[str]]]: 表名 -> (是否成功, 错误信息)
        """
        if tables is None:
            tables = self.source_extractor.get_all_tables()

        results = {}

        # 第一阶段：创建所有表（不包含外键，避免循环依赖）
        for table_name in tables:
            try:
                self._create_table(table_name, include_foreign_keys=False)
                results[table_name] = (True, None)
                logger.info(f"表 {table_name} 创建成功")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"表 {table_name} 创建失败: {error_msg}")
                results[table_name] = (False, error_msg)

        # 第二阶段：添加外键约束
        for table_name in tables:
            if results.get(table_name, (False, None))[0]:
                try:
                    self._add_foreign_keys(table_name)
                    logger.info(f"表 {table_name} 外键添加成功")
                except Exception as e:
                    logger.warning(f"表 {table_name} 外键添加失败: {e}")
                    # 外键失败不阻止整体成功

        # 第三阶段：创建索引
        for table_name in tables:
            if results.get(table_name, (False, None))[0]:
                try:
                    self._create_indexes(table_name)
                    logger.info(f"表 {table_name} 索引创建成功")
                except Exception as e:
                    logger.warning(f"表 {table_name} 索引创建失败: {e}")
                    # 索引失败不阻止整体成功

        return results
    
    def _convert_default_value(self, default_value: str, target_db_type: str, is_auto_increment: bool = False) -> Optional[str]:
        """
        转换默认值表达式为目标数据库兼容的格式

        Args:
            default_value: 原始默认值
            target_db_type: 目标数据库类型
            is_auto_increment: 是否是自增列

        Returns:
            转换后的默认值，如果不需要默认值则返回 None
        """
        if not default_value or default_value == "None":
            return None

        # PostgreSQL nextval 序列转换为 MySQL AUTO_INCREMENT
        if "nextval" in default_value.lower():
            if target_db_type == DatabaseType.MYSQL:
                # MySQL 使用 AUTO_INCREMENT，不需要 DEFAULT 值
                return None
            elif target_db_type == DatabaseType.POSTGRESQL:
                return default_value
            elif target_db_type == DatabaseType.SQLITE:
                return None  # SQLite 使用 AUTOINCREMENT

        # 时间函数转换
        if "now()" in default_value.lower() or "current_timestamp" in default_value.lower():
            if target_db_type == DatabaseType.MYSQL:
                return "CURRENT_TIMESTAMP"
            elif target_db_type == DatabaseType.POSTGRESQL:
                return "NOW()"
            elif target_db_type == DatabaseType.SQLITE:
                return "CURRENT_TIMESTAMP"

        # 字符串默认值处理
        if default_value.startswith("'") and default_value.endswith("'"):
            return default_value

        return default_value

    def _create_table(self, table_name: str, include_foreign_keys: bool = True):
        """
        创建表

        Args:
            table_name: 表名
            include_foreign_keys: 是否包含外键约束（用于分阶段创建避免循环依赖）
        """
        target_tables = self.target_extractor.get_all_tables()

        if table_name in target_tables:
            logger.info(f"表 {table_name} 已存在，跳过创建")
            return

        source_schema = self.source_extractor.get_table_schema_info(table_name)
        target_db_type = self.target_conn.db_type
        source_db_type = self.source_conn.db_type

        logger.debug(f"表 {table_name} 源结构: {source_schema}")

        # 根据目标数据库类型选择引号
        if target_db_type == DatabaseType.MYSQL:
            quote = "`"
        else:
            quote = '"'

        columns_def = []
        pk_columns = source_schema.get("primary_keys", [])

        for col in source_schema["columns"]:
            col_type = col["type"]
            normalized_type = TypeMapper.normalize_type(source_db_type, col_type)
            mapped_type = TypeMapper.map_type(normalized_type, target_db_type)

            # 检查是否是自增列（主键且类型为整数且有默认值包含 nextval）
            is_auto_increment = (
                col["name"] in pk_columns and
                normalized_type in ("INTEGER", "BIGINT") and
                col.get("autoincrement", False)
            )

            # 检查原始默认值是否包含 nextval
            has_nextval_default = col.get("default") and "nextval" in str(col.get("default")).lower()
            if has_nextval_default:
                is_auto_increment = True

            logger.debug(f"列 {col['name']}: 原始类型={col_type}, 标准化={normalized_type}, 映射后={mapped_type}, 自增={is_auto_increment}")

            col_def = f'{quote}{col["name"]}{quote} {mapped_type}'

            # 处理自增列
            if is_auto_increment:
                if target_db_type == DatabaseType.MYSQL:
                    col_def += " AUTO_INCREMENT"
                elif target_db_type == DatabaseType.POSTGRESQL:
                    # PostgreSQL 保持 DEFAULT nextval(...)
                    pass
                elif target_db_type == DatabaseType.SQLITE:
                    col_def = f'{quote}{col["name"]}{quote} INTEGER PRIMARY KEY AUTOINCREMENT'

            if not col["nullable"]:
                col_def += " NOT NULL"

            # 处理默认值
            if col.get("default"):
                converted_default = self._convert_default_value(
                    str(col["default"]),
                    target_db_type,
                    is_auto_increment
                )
                if converted_default and not is_auto_increment:
                    col_def += f" DEFAULT {converted_default}"

            columns_def.append(col_def)

        if pk_columns:
            # SQLite 的自增主键已经在列定义中处理
            if not (target_db_type == DatabaseType.SQLITE and len(pk_columns) == 1):
                pk_cols_str = ", ".join([f'{quote}{col}{quote}' for col in pk_columns])
                columns_def.append(f"PRIMARY KEY ({pk_cols_str})")

        # 添加外键约束（仅在 include_foreign_keys=True 时）
        if include_foreign_keys:
            foreign_keys = source_schema.get("foreign_keys", [])
            for fk in foreign_keys:
                if fk.get("constrained_columns") and fk.get("referred_table") and fk.get("referred_columns"):
                    constrained_cols = ", ".join([f'{quote}{col}{quote}' for col in fk["constrained_columns"]])
                    referred_cols = ", ".join([f'{quote}{col}{quote}' for col in fk["referred_columns"]])
                    referred_table = fk["referred_table"]

                    # 外键约束名
                    fk_name = fk.get("name") or f"fk_{table_name}_{referred_table}"

                    if target_db_type == DatabaseType.MYSQL:
                        columns_def.append(f"CONSTRAINT `{fk_name}` FOREIGN KEY ({constrained_cols}) REFERENCES `{referred_table}` ({referred_cols})")
                    elif target_db_type == DatabaseType.POSTGRESQL:
                        columns_def.append(f'CONSTRAINT "{fk_name}" FOREIGN KEY ({constrained_cols}) REFERENCES "{referred_table}" ({referred_cols})')
                    elif target_db_type == DatabaseType.SQLITE:
                        columns_def.append(f'FOREIGN KEY ({constrained_cols}) REFERENCES "{referred_table}" ({referred_cols})')

        create_sql = f'CREATE TABLE {quote}{table_name}{quote} ({', '.join(columns_def)});'

        logger.info(f"执行建表 SQL: {create_sql}")

        try:
            with self.target_conn.engine.connect() as conn:
                conn.execute(text(create_sql))
                conn.commit()
            logger.info(f"表 {table_name} 创建成功")
        except Exception as e:
            logger.error(f"创建表 {table_name} 失败: {e}")
            logger.error(f"SQL: {create_sql}")
            raise

    def _add_foreign_keys(self, table_name: str):
        """
        为已存在的表添加外键约束

        Args:
            table_name: 表名
        """
        source_schema = self.source_extractor.get_table_schema_info(table_name)
        target_db_type = self.target_conn.db_type

        # 根据目标数据库类型选择引号
        if target_db_type == DatabaseType.MYSQL:
            quote = "`"
        else:
            quote = '"'

        foreign_keys = source_schema.get("foreign_keys", [])
        if not foreign_keys:
            return

        for fk in foreign_keys:
            if not (fk.get("constrained_columns") and fk.get("referred_table") and fk.get("referred_columns")):
                continue

            constrained_cols = ", ".join([f'{quote}{col}{quote}' for col in fk["constrained_columns"]])
            referred_cols = ", ".join([f'{quote}{col}{quote}' for col in fk["referred_columns"]])
            referred_table = fk["referred_table"]
            fk_name = fk.get("name") or f"fk_{table_name}_{referred_table}"

            try:
                if target_db_type == DatabaseType.MYSQL:
                    alter_sql = f"ALTER TABLE `{table_name}` ADD CONSTRAINT `{fk_name}` FOREIGN KEY ({constrained_cols}) REFERENCES `{referred_table}` ({referred_cols})"
                elif target_db_type == DatabaseType.POSTGRESQL:
                    alter_sql = f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{fk_name}" FOREIGN KEY ({constrained_cols}) REFERENCES "{referred_table}" ({referred_cols})'
                elif target_db_type == DatabaseType.SQLITE:
                    # SQLite 不支持添加外键约束到已存在的表
                    logger.warning(f"SQLite 不支持向已存在的表添加外键约束: {table_name}")
                    continue
                else:
                    continue

                with self.target_conn.engine.connect() as conn:
                    conn.execute(text(alter_sql))
                    conn.commit()
                logger.info(f"外键 {fk_name} 添加成功")
            except Exception as e:
                logger.warning(f"外键 {fk_name} 添加失败: {e}")
                # 外键失败不阻止整体成功

    def _create_indexes(self, table_name: str):
        """
        为表创建索引

        Args:
            table_name: 表名
        """
        source_schema = self.source_extractor.get_table_schema_info(table_name)
        target_db_type = self.target_conn.db_type

        # 根据目标数据库类型选择引号
        if target_db_type == DatabaseType.MYSQL:
            quote = "`"
        else:
            quote = '"'

        indexes = source_schema.get("indexes", [])
        if not indexes:
            return

        for idx in indexes:
            if not idx.get("columns"):
                continue

            idx_name = idx.get("name") or f"idx_{table_name}_{'_'.join(idx['columns'])}"
            columns = ", ".join([f'{quote}{col}{quote}' for col in idx["columns"]])
            unique = idx.get("unique", False)

            try:
                if target_db_type == DatabaseType.MYSQL:
                    unique_str = "UNIQUE " if unique else ""
                    create_sql = f"CREATE {unique_str}INDEX `{idx_name}` ON `{table_name}` ({columns})"
                elif target_db_type == DatabaseType.POSTGRESQL:
                    unique_str = "UNIQUE " if unique else ""
                    create_sql = f'CREATE {unique_str}INDEX "{idx_name}" ON "{table_name}" ({columns})'
                elif target_db_type == DatabaseType.SQLITE:
                    unique_str = "UNIQUE " if unique else ""
                    create_sql = f'CREATE {unique_str}INDEX "{idx_name}" ON "{table_name}" ({columns})'
                else:
                    continue

                with self.target_conn.engine.connect() as conn:
                    conn.execute(text(create_sql))
                    conn.commit()
                logger.info(f"索引 {idx_name} 创建成功")
            except Exception as e:
                logger.warning(f"索引 {idx_name} 创建失败: {e}")
                # 索引失败不阻止整体成功


class DatabaseMigrationService:
    """
    数据库迁移服务
    
    协调表结构迁移和数据迁移，支持分批处理和进度跟踪
    """
    
    def __init__(
        self,
        source_url: str,
        target_url: str,
        batch_size: int = 1000,
        max_workers: int = 2
    ):
        self.source_url = source_url
        self.target_url = target_url
        self.batch_size = batch_size
        self.max_workers = max_workers
        
        self.source_conn = MigrationConnection(source_url)
        self.target_conn = MigrationConnection(target_url)
        
        self.progress: Dict[str, MigrationProgress] = {}
        self._is_running = False
    
    def migrate(
        self,
        tables: Optional[List[str]] = None,
        migrate_schema: bool = True,
        progress_callback: Optional[Callable] = None,
        skip_if_synced: bool = True
    ) -> MigrationResult:
        """
        执行数据库迁移
        
        Args:
            tables: 要迁移的表名列表，None表示迁移所有表
            migrate_schema: 是否迁移表结构
            progress_callback: 进度回调函数
            skip_if_synced: 如果数据库已同步则跳过迁移
        
        Returns:
            MigrationResult: 迁移结果
        """
        self._is_running = True
        start_time = time.time()
        
        # 智能检测：如果数据库已同步则跳过迁移
        if skip_if_synced:
            from utils.migration_precheck import DatabasePrechecker
            prechecker = DatabasePrechecker(self.source_url, self.target_url)
            is_synced, sync_details = prechecker.check_sync_status()
            
            if is_synced:
                logger.info("数据库已同步，跳过迁移")
                return MigrationResult(
                    success=True,
                    tables_migrated=sync_details.get("tables_checked", 0),
                    tables_failed=0,
                    total_rows_migrated=0,
                    total_rows_failed=0,
                    duration_seconds=0,
                    table_progress=[],
                    errors=[],
                    skipped=True,
                    skip_reason="数据库已同步"
                )
        
        source_extractor = TableSchemaExtractor(self.source_conn)
        if tables is None:
            tables = source_extractor.get_all_tables()
        
        tables_migrated = 0
        tables_failed = 0
        total_rows_migrated = 0
        total_rows_failed = 0
        errors: List[Dict[str, Any]] = []
        
        if migrate_schema:
            schema_migrator = SchemaMigrator(self.source_conn, self.target_conn)
            schema_results = schema_migrator.migrate_schema(tables)

            for table_name, (success, error_msg) in schema_results.items():
                if not success:
                    errors.append({
                        "table": table_name,
                        "error": f"表结构迁移失败: {error_msg}"
                    })
        
        table_migrator = TableMigrator(
            self.source_conn,
            self.target_conn,
            self.batch_size
        )
        
        for table_name in tables:
            if not self._is_running:
                logger.warning("迁移被中断")
                break
            
            def callback(name: str, migrated: int):
                if name in self.progress:
                    self.progress[name].migrated_rows = migrated
                if progress_callback:
                    progress_callback(name, migrated)
            
            try:
                progress = table_migrator.migrate_table(table_name, callback)
                self.progress[table_name] = progress
                
                if progress.status == "completed":
                    tables_migrated += 1
                    total_rows_migrated += progress.migrated_rows
                elif progress.status == "failed":
                    tables_failed += 1
                    total_rows_failed += progress.total_rows - progress.migrated_rows
                    errors.append({
                        "table": table_name,
                        "error": progress.error_message
                    })
                    
            except Exception as e:
                tables_failed += 1
                logger.error(f"表 {table_name} 迁移异常: {e}")
                errors.append({
                    "table": table_name,
                    "error": str(e)
                })
        
        duration = time.time() - start_time
        
        self.source_conn.close()
        self.target_conn.close()
        
        return MigrationResult(
            success=tables_failed == 0,
            tables_migrated=tables_migrated,
            tables_failed=tables_failed,
            total_rows_migrated=total_rows_migrated,
            total_rows_failed=total_rows_failed,
            duration_seconds=duration,
            table_progress=list(self.progress.values()),
            errors=errors
        )
    
    def stop(self):
        """停止迁移"""
        self._is_running = False
    
    def get_progress(self) -> Dict[str, MigrationProgress]:
        """获取迁移进度"""
        return self.progress


def run_migration(
    source_url: str,
    target_url: str,
    batch_size: int = 1000,
    tables: Optional[List[str]] = None,
    progress_callback: Optional[Callable] = None
) -> MigrationResult:
    """
    执行数据库迁移
    
    Args:
        source_url: 源数据库连接URL
        target_url: 目标数据库连接URL
        batch_size: 批量大小
        tables: 要迁移的表名列表
        progress_callback: 进度回调
    
    Returns:
        MigrationResult: 迁移结果
    """
    service = DatabaseMigrationService(
        source_url=source_url,
        target_url=target_url,
        batch_size=batch_size
    )
    
    return service.migrate(
        tables=tables,
        migrate_schema=True,
        progress_callback=progress_callback
    )


def run_migration_from_env(
    target_url: str,
    batch_size: int = 1000,
    tables: Optional[List[str]] = None,
    progress_callback: Optional[Callable] = None
) -> MigrationResult:
    """
    使用环境变量中的源数据库URL执行迁移
    
    Args:
        target_url: 目标数据库连接URL
        batch_size: 批量大小
        tables: 要迁移的表名列表
        progress_callback: 进度回调
    
    Returns:
        MigrationResult: 迁移结果
    """
    from config import get_config
    config = get_config()
    source_url = config.database.url
    
    return run_migration(
        source_url=source_url,
        target_url=target_url,
        batch_size=batch_size,
        tables=tables,
        progress_callback=progress_callback
    )
