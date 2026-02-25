"""
数据库迁移服务

提供数据迁移功能，支持批量迁移、分批提交、断点续传
"""
import time
import hashlib
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import text

from utils.logging import get_named_logger
from utils.migration import Connection, SchemaReader, DbType
from utils.migration.schema import SchemaMigrator
from utils.migration.auto_dependency import DependencyResolver

logger = get_named_logger("migration")


# 可选：手动覆盖的表依赖关系
# 当自动检测无法满足需求时，可在此添加特殊依赖
# 格式: {父表: [子表列表]}
MANUAL_DEPENDENCIES: Dict[str, List[str]] = {
    # 示例: "users": ["user_profiles"],
}


@dataclass
class MigrationProgress:
    """迁移进度"""
    table_name: str
    total_rows: int
    migrated_rows: int
    status: str
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
    skipped: bool = False
    skip_reason: Optional[str] = None


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
        check_sync: bool = True
    ):
        self.source_url = source_url
        self.target_url = target_url
        self.batch_size = batch_size
        self.check_sync = check_sync

        self.source_conn = Connection(source_url)
        self.target_conn = Connection(target_url)

        self.progress: Dict[str, MigrationProgress] = {}
        self._is_running = True

    def _sort_tables_by_dependency(self, tables: List[str]) -> List[str]:
        """
        根据外键依赖关系对表进行拓扑排序
        确保父表先于子表迁移，避免外键约束错误

        使用自动依赖发现机制，从数据库外键约束中自动提取依赖关系。

        Args:
            tables: 表名列表

        Returns:
            List[str]: 排序后的表名列表（父表在前，子表在后）
        """
        try:
            # 使用自动依赖发现
            resolver = DependencyResolver(self.source_conn)
            sorted_tables = resolver.topological_sort(tables)

            # 应用手动覆盖的依赖（如果有）
            if MANUAL_DEPENDENCIES:
                sorted_tables = self._apply_manual_dependencies(sorted_tables, tables)

            return sorted_tables
        except Exception as e:
            logger.warning(f"自动依赖发现失败，使用原始顺序: {e}")
            return tables

    def _apply_manual_dependencies(self, sorted_tables: List[str], original_tables: List[str]) -> List[str]:
        """
        应用手动指定的依赖关系

        Args:
            sorted_tables: 已排序的表列表
            original_tables: 原始表列表

        Returns:
            List[str]: 调整后的表列表
        """
        # 构建位置映射
        positions = {table: idx for idx, table in enumerate(sorted_tables)}

        for parent, children in MANUAL_DEPENDENCIES.items():
            if parent not in positions:
                continue
            parent_pos = positions[parent]

            for child in children:
                if child not in positions or child not in original_tables:
                    continue
                child_pos = positions[child]

                # 确保子表在父表之后
                if child_pos < parent_pos:
                    # 交换位置
                    sorted_tables.remove(child)
                    sorted_tables.insert(parent_pos, child)
                    # 更新位置映射
                    positions = {table: idx for idx, table in enumerate(sorted_tables)}

        return sorted_tables
    
    def migrate(
        self,
        tables: Optional[List[str]] = None,
        migrate_schema: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> MigrationResult:
        """
        执行迁移
        
        Args:
            tables: 要迁移的表名列表
            migrate_schema: 是否迁移表结构
            progress_callback: 进度回调函数
        """
        start_time = time.time()
        
        if self.check_sync:
            synced, sync_details = self._check_sync_status()
            if synced:
                duration = time.time() - start_time
                self._close_connections()
                return MigrationResult(
                    success=True,
                    tables_migrated=0,
                    tables_failed=0,
                    total_rows_migrated=0,
                    total_rows_failed=0,
                    duration_seconds=duration,
                    skipped=True,
                    skip_reason="数据库已同步，无需迁移"
                )
        
        source_reader = SchemaReader(self.source_conn)
        if tables is None:
            tables = source_reader.get_all_tables()

        if not tables:
            self._close_connections()
            return MigrationResult(
                success=True,
                tables_migrated=0,
                tables_failed=0,
                total_rows_migrated=0,
                total_rows_failed=0,
                duration_seconds=time.time() - start_time
            )

        # 根据外键依赖关系对表进行排序，确保父表先于子表迁移
        sorted_tables = self._sort_tables_by_dependency(tables)
        logger.info(f"表迁移顺序（按依赖排序）: {sorted_tables}")

        tables_migrated = 0
        tables_failed = 0
        total_rows_migrated = 0
        total_rows_failed = 0
        errors: List[Dict[str, Any]] = []

        schema_migrator = None
        if migrate_schema:
            schema_migrator = SchemaMigrator(self.source_conn, self.target_conn)
            schema_results = schema_migrator.migrate(sorted_tables, defer_foreign_keys=True)

            for table_name, (success, error_msg) in schema_results.items():
                if not success:
                    errors.append({"table": table_name, "error": f"表结构迁移失败: {error_msg}"})

        for table_name in sorted_tables:
            if not self._is_running:
                logger.warning("迁移被中断")
                break
            
            try:
                progress = self._migrate_table(table_name, source_reader, progress_callback)
                self.progress[table_name] = progress
                
                if progress.status == "completed":
                    tables_migrated += 1
                    total_rows_migrated += progress.migrated_rows
                else:
                    tables_failed += 1
                    total_rows_failed += progress.total_rows - progress.migrated_rows
                    errors.append({"table": table_name, "error": progress.error_message})
                    
            except Exception as e:
                tables_failed += 1
                logger.error(f"表 {table_name} 迁移异常: {e}")
                errors.append({"table": table_name, "error": str(e)})
        
        # 数据迁移完成后，添加外键约束
        if schema_migrator and tables_failed == 0:
            logger.info("数据迁移完成，开始添加外键约束...")
            schema_migrator.add_pending_foreign_keys()
        
        duration = time.time() - start_time
        self._close_connections()
        
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
    
    def _migrate_table(
        self,
        table_name: str,
        source_reader: SchemaReader,
        progress_callback: Optional[Callable] = None
    ) -> MigrationProgress:
        """迁移单个表"""
        progress = MigrationProgress(
            table_name=table_name,
            total_rows=0,
            migrated_rows=0,
            status="in_progress",
            started_at=datetime.now()
        )
        
        try:
            progress.total_rows = self._get_row_count(self.source_conn, table_name)
            
            if progress.total_rows == 0:
                progress.status = "completed"
                progress.completed_at = datetime.now()
                return progress
            
            migrated = self._migrate_data(table_name, source_reader, progress_callback)
            progress.migrated_rows = migrated
            progress.status = "completed"
            progress.completed_at = datetime.now()
            
        except Exception as e:
            progress.status = "failed"
            progress.error_message = str(e)
            progress.completed_at = datetime.now()
            logger.error(f"表 {table_name} 迁移失败: {e}")
        
        return progress
    
    def _migrate_data(
        self,
        table_name: str,
        source_reader: SchemaReader,
        progress_callback: Optional[Callable] = None
    ) -> int:
        """迁移数据"""
        target_reader = SchemaReader(self.target_conn)
        
        source_columns = [c.name for c in source_reader.get_table_schema(table_name).columns]
        target_columns = [c.name for c in target_reader.get_table_schema(table_name).columns]
        common_columns = [c for c in source_columns if c in target_columns]
        
        if not common_columns:
            raise ValueError(f"表 {table_name} 没有可迁移的公共列")
        
        target_schema = target_reader.get_table_schema(table_name)
        target_column_types = {c.name: c.type for c in target_schema.columns}

        source_dialect = self.source_conn.dialect
        target_dialect = self.target_conn.dialect
        insert_sql = text(target_dialect.insert_on_conflict(table_name, common_columns))

        offset = 0
        migrated = 0
        col_list = ", ".join(common_columns)

        while True:
            select_sql = text(f"SELECT {col_list} FROM {source_dialect.quote_ident(table_name)} LIMIT :limit OFFSET :offset")
            
            rows = self.source_conn.fetch_all(select_sql, {"limit": self.batch_size, "offset": offset})
            
            if not rows:
                break
            
            batch_data = []
            for row in rows:
                row_dict = dict(zip(common_columns, row))
                for col in common_columns:
                    value = row_dict[col]
                    if col in target_column_types:
                        target_type = target_column_types[col].lower()
                        if 'bool' in target_type and isinstance(value, int):
                            row_dict[col] = bool(value)
                batch_data.append(row_dict)
            
            self.target_conn.execute(insert_sql, batch_data)
            
            migrated += len(batch_data)
            offset += self.batch_size
            
            if progress_callback:
                progress_callback(table_name, migrated)
        
        return migrated
    
    def _get_row_count(self, conn: Connection, table_name: str) -> int:
        """获取表行数"""
        dialect = conn.dialect
        return conn.fetch_scalar(f"SELECT COUNT(*) FROM {dialect.quote_ident(table_name)}")
    
    def _check_sync_status(self) -> tuple:
        """检查数据库是否已同步"""
        try:
            source_reader = SchemaReader(self.source_conn)
            target_reader = SchemaReader(self.target_conn)
            
            source_tables = set(source_reader.get_all_tables())
            target_tables = set(target_reader.get_all_tables())
            
            if source_tables != target_tables:
                return False, {"reason": "表集合不同"}
            
            for table in source_tables:
                source_count = self._get_row_count(self.source_conn, table)
                target_count = self._get_row_count(self.target_conn, table)
                
                if source_count != target_count:
                    return False, {"reason": f"表 {table} 行数不同"}
                
                if source_count > 0:
                    source_hash = self._get_table_hash(self.source_conn, table)
                    target_hash = self._get_table_hash(self.target_conn, table)
                    
                    if source_hash != target_hash:
                        return False, {"reason": f"表 {table} 数据内容不同"}
            
            return True, {"tables_checked": len(source_tables)}
            
        except Exception as e:
            return False, {"reason": f"检查失败: {str(e)}"}
    
    def _get_table_hash(self, conn: Connection, table_name: str) -> str:
        """获取表数据哈希"""
        dialect = conn.dialect
        rows = conn.fetch_all(f"SELECT * FROM {dialect.quote_ident(table_name)} ORDER BY id")
        data_str = "".join(str(row) for row in rows)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def stop(self):
        """停止迁移"""
        self._is_running = False
    
    def get_progress(self) -> Dict[str, MigrationProgress]:
        """获取迁移进度"""
        return self.progress
    
    def _close_connections(self):
        """关闭连接"""
        self.source_conn.close()
        self.target_conn.close()


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
