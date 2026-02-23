"""
数据库迁移预检查工具

提供智能的跨数据库迁移预检查功能，包括连接测试、类型兼容性评估等
"""
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field

from utils.db_migration_utils import (
    DatabaseType,
    MigrationConnection,
    TableSchemaExtractor,
    TypeMapper,
    get_source_connection,
    create_target_connection,
    create_database_if_not_exists
)
from utils.db_validation import validate_database_url, check_driver_installed

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """检查结果数据类"""
    passed: bool
    severity: str  # "error", "warning", "info"
    category: str  # "connection", "schema", "data", "compatibility"
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class PrecheckReport:
    """预检查报告"""
    source_db_type: str
    target_db_type: str
    passed: bool
    results: List[CheckResult] = field(default_factory=list)
    # 智能检测相关字段
    is_synced: bool = False  # 数据库是否已同步
    sync_details: Optional[Dict[str, Any]] = None  # 同步详情
    
    @property
    def errors(self) -> List[CheckResult]:
        return [r for r in self.results if r.severity == "error"]
    
    @property
    def warnings(self) -> List[CheckResult]:
        return [r for r in self.results if r.severity == "warning"]
    
    @property
    def infos(self) -> List[CheckResult]:
        return [r for r in self.results if r.severity == "info"]
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "source_db_type": self.source_db_type,
            "target_db_type": self.target_db_type,
            "passed": self.passed,
            "is_synced": self.is_synced,
            "summary": {
                "total": len(self.results),
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "infos": len(self.infos)
            },
            "errors": [r.__dict__ for r in self.errors],
            "warnings": [r.__dict__ for r in self.warnings],
            "infos": [r.__dict__ for r in self.infos]
        }
        if self.sync_details:
            result["sync_details"] = self.sync_details
        return result


class DatabasePrechecker:
    """
    数据库迁移预检查器
    
    执行跨数据库迁移前的全面预检查
    """
    
    def __init__(self, source_url: str, target_url: str):
        self.source_url = source_url
        self.target_url = target_url
        self.source_db_type = DatabaseType.detect(source_url)
        self.target_db_type = DatabaseType.detect(target_url)
        self.results: List[CheckResult] = []
    
    def run_precheck(self) -> PrecheckReport:
        """执行完整的预检查"""
        self.results = []
        
        self._check_url_validity()
        self._check_driver_availability()
        self._check_connection()
        self._check_schema_compatibility()
        self._check_data_type_compatibility()
        self._check_special_features()
        
        passed = all(r.severity != "error" for r in self.results)
        
        return PrecheckReport(
            source_db_type=self.source_db_type,
            target_db_type=self.target_db_type,
            passed=passed,
            results=self.results
        )
    
    def _check_url_validity(self):
        """检查URL有效性"""
        source_valid, source_error = validate_database_url(self.source_url)
        if not source_valid:
            self.results.append(CheckResult(
                passed=False,
                severity="error",
                category="connection",
                message=f"源数据库URL无效: {source_error}"
            ))
        
        target_valid, target_error = validate_database_url(self.target_url)
        if not target_valid:
            self.results.append(CheckResult(
                passed=False,
                severity="error",
                category="connection",
                message=f"目标数据库URL无效: {target_error}"
            ))
    
    def _check_driver_availability(self):
        """检查数据库驱动是否安装"""
        source_installed, source_msg = check_driver_installed(self.source_db_type, self.source_url)
        if not source_installed:
            self.results.append(CheckResult(
                passed=False,
                severity="error",
                category="connection",
                message=f"源数据库驱动未安装: {source_msg}"
            ))
        
        target_installed, target_msg = check_driver_installed(self.target_db_type, self.target_url)
        if not target_installed:
            self.results.append(CheckResult(
                passed=False,
                severity="error",
                category="connection",
                message=f"目标数据库驱动未安装: {target_msg}"
            ))
    
    def _check_connection(self):
        """检查数据库连接"""
        try:
            source_conn = MigrationConnection(self.source_url)
            source_ok, source_error = source_conn.test_connection()
            if not source_ok:
                self.results.append(CheckResult(
                    passed=False,
                    severity="error",
                    category="connection",
                    message=f"源数据库连接失败: {source_error}"
                ))
            else:
                self.results.append(CheckResult(
                    passed=True,
                    severity="info",
                    category="connection",
                    message="源数据库连接成功"
                ))
            source_conn.close()
        except Exception as e:
            self.results.append(CheckResult(
                passed=False,
                severity="error",
                category="connection",
                message=f"源数据库连接异常: {str(e)}"
            ))
        
        try:
            target_conn = MigrationConnection(self.target_url)
            target_ok, target_error = target_conn.test_connection(auto_create_db=True)
            if not target_ok:
                self.results.append(CheckResult(
                    passed=False,
                    severity="error",
                    category="connection",
                    message=f"目标数据库连接失败: {target_error}"
                ))
            else:
                self.results.append(CheckResult(
                    passed=True,
                    severity="info",
                    category="connection",
                    message="目标数据库连接成功（如数据库不存在已自动创建）"
                ))
            target_conn.close()
        except Exception as e:
            self.results.append(CheckResult(
                passed=False,
                severity="error",
                category="connection",
                message=f"目标数据库连接异常: {str(e)}"
            ))
    
    def _check_schema_compatibility(self):
        """检查表结构兼容性"""
        try:
            source_conn = MigrationConnection(self.source_url)
            target_conn = MigrationConnection(self.target_url)
            
            source_extractor = TableSchemaExtractor(source_conn)
            target_extractor = TableSchemaExtractor(target_conn)
            
            source_tables = set(source_extractor.get_all_tables())
            target_tables = set(target_extractor.get_all_tables())
            
            if not source_tables:
                self.results.append(CheckResult(
                    passed=False,
                    severity="error",
                    category="schema",
                    message="源数据库中没有表"
                ))
                source_conn.close()
                target_conn.close()
                return
            
            if target_tables:
                missing_in_target = source_tables - target_tables
                if missing_in_target:
                    self.results.append(CheckResult(
                        passed=True,
                        severity="info",
                        category="schema",
                        message=f"目标数据库缺少以下表: {', '.join(missing_in_target)}",
                        details={"missing_tables": list(missing_in_target)}
                    ))
                
                existing_in_both = source_tables & target_tables
                if existing_in_both:
                    self._check_existing_tables_compatibility(
                        source_extractor, target_extractor, existing_in_both
                    )
            else:
                self.results.append(CheckResult(
                    passed=True,
                    severity="info",
                    category="schema",
                    message=f"目标数据库为空，将迁移 {len(source_tables)} 个表",
                    details={"tables_to_migrate": list(source_tables)}
                ))
            
            source_conn.close()
            target_conn.close()
            
        except Exception as e:
            self.results.append(CheckResult(
                passed=False,
                severity="error",
                category="schema",
                message=f"检查表结构兼容性时发生错误: {str(e)}"
            ))
    
    def _check_existing_tables_compatibility(
        self,
        source_extractor: TableSchemaExtractor,
        target_extractor: TableSchemaExtractor,
        common_tables: set
    ):
        """检查已存在表的列兼容性"""
        for table in common_tables:
            source_cols = {c["name"]: c for c in source_extractor.get_table_columns(table)}
            target_cols = {c["name"]: c for c in target_extractor.get_table_columns(table)}
            
            missing_cols = set(source_cols.keys()) - set(target_cols.keys())
            if missing_cols:
                self.results.append(CheckResult(
                    passed=True,
                    severity="warning",
                    category="schema",
                    message=f"表 {table} 在目标数据库中缺少列: {', '.join(missing_cols)}",
                    details={"table": table, "missing_columns": list(missing_cols)}
                ))
            
            common_cols = set(source_cols.keys()) & set(target_cols.keys())
            for col in common_cols:
                source_type = TypeMapper.normalize_type(self.source_db_type, source_cols[col]["type"])
                target_type = TypeMapper.normalize_type(self.target_db_type, target_cols[col]["type"])
                
                if source_type != target_type:
                    self.results.append(CheckResult(
                        passed=True,
                        severity="warning",
                        category="data",
                        message=f"表 {table} 列 {col} 类型可能不兼容: {source_cols[col]['type']} -> {target_cols[col]['type']}",
                        details={
                            "table": table,
                            "column": col,
                            "source_type": source_cols[col]["type"],
                            "target_type": target_cols[col]["type"],
                            "normalized_source": source_type,
                            "normalized_target": target_type
                        }
                    ))
    
    def _check_data_type_compatibility(self):
        """检查数据类型兼容性"""
        incompatible_types = self._get_incompatible_types()
        
        if incompatible_types:
            self.results.append(CheckResult(
                passed=True,
                severity="warning",
                category="compatibility",
                message=f"检测到 {len(incompatible_types)} 种可能不兼容的数据类型转换",
                details={"incompatible_types": incompatible_types}
            ))
        else:
            self.results.append(CheckResult(
                passed=True,
                severity="info",
                category="compatibility",
                message="数据类型兼容性检查通过"
            ))
    
    def _get_incompatible_types(self) -> List[Dict[str, str]]:
        """获取不兼容的类型转换列表"""
        incompatibilities = []
        
        if self.source_db_type == DatabaseType.MYSQL and self.target_db_type == DatabaseType.POSTGRESQL:
            incompatibilities.extend([
                {"from": "TINYINT(1)", "to": "BOOLEAN", "note": "MySQL TINYINT(1) 转换为 PostgreSQL BOOLEAN"},
                {"from": "MEDIUMTEXT", "to": "TEXT", "note": "MySQL MEDIUMTEXT 映射为 PostgreSQL TEXT"},
                {"from": "LONGTEXT", "to": "TEXT", "note": "MySQL LONGTEXT 映射为 PostgreSQL TEXT"},
            ])
        
        elif self.source_db_type == DatabaseType.POSTGRESQL and self.target_db_type == DatabaseType.MYSQL:
            incompatibilities.extend([
                {"from": "JSONB", "to": "JSON", "note": "PostgreSQL JSONB 转换为 MySQL JSON"},
                {"from": "ARRAY", "to": "TEXT", "note": "PostgreSQL ARRAY 类型需要自定义处理"},
                {"from": "UUID", "to": "VARCHAR(36)", "note": "PostgreSQL UUID 转换为 MySQL VARCHAR"},
            ])
        
        elif self.source_db_type == DatabaseType.SQLITE:
            incompatibilities.extend([
                {"from": "INTEGER", "to": "INTEGER/BIGINT", "note": "SQLite INTEGER 可能溢出"},
                {"from": "DATETIME", "to": "TEXT", "note": "SQLite 无原生 DATETIME 类型"},
                {"from": "BOOLEAN", "to": "INTEGER", "note": "SQLite 无原生 BOOLEAN 类型"},
            ])
        
        return incompatibilities
    
    def _check_special_features(self):
        """检查特殊功能兼容性"""
        source_conn = MigrationConnection(self.source_url)
        target_conn = MigrationConnection(self.target_url)
        
        source_inspector = source_conn.get_inspector()
        target_inspector = target_conn.get_inspector()
        
        source_views = source_inspector.get_view_names()
        if source_views:
            self.results.append(CheckResult(
                passed=True,
                severity="warning",
                category="compatibility",
                message=f"源数据库包含 {len(source_views)} 个视图，视图迁移需要额外处理",
                details={"views": source_views}
            ))
        
        source_triggers = source_inspector.get_table_names()
        if source_triggers:
            self.results.append(CheckResult(
                passed=True,
                severity="warning",
                category="compatibility",
                message=f"源数据库包含触发器，触发器迁移需要额外处理",
                details={"note": "触发器需要手动迁移"}
            ))
        
        source_conn.close()
        target_conn.close()
    
    def check_sync_status(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        智能检测源数据库和目标数据库是否已同步
        
        检查内容：
        1. 表结构是否相同
        2. 数据行数是否相同
        3. 关键表的数据哈希是否相同
        
        Returns:
            Tuple[bool, Optional[Dict]]: (是否已同步, 同步详情)
        """
        try:
            source_conn = MigrationConnection(self.source_url)
            target_conn = MigrationConnection(self.target_url)
            
            source_extractor = TableSchemaExtractor(source_conn)
            target_extractor = TableSchemaExtractor(target_conn)
            
            source_tables = set(source_extractor.get_all_tables())
            target_tables = set(target_extractor.get_all_tables())
            
            # 检查表集合是否相同
            if source_tables != target_tables:
                source_conn.close()
                target_conn.close()
                return False, {
                    "reason": "表集合不同",
                    "source_tables": len(source_tables),
                    "target_tables": len(target_tables),
                    "missing_in_target": list(source_tables - target_tables),
                    "missing_in_source": list(target_tables - source_tables)
                }
            
            # 检查每个表的结构和数据
            table_status = {}
            all_synced = True
            
            for table in source_tables:
                # 获取列信息
                source_cols = {c["name"]: c for c in source_extractor.get_table_columns(table)}
                target_cols = {c["name"]: c for c in target_extractor.get_table_columns(table)}
                
                if set(source_cols.keys()) != set(target_cols.keys()):
                    table_status[table] = {"synced": False, "reason": "列不同"}
                    all_synced = False
                    continue
                
                # 检查行数
                source_count = self._get_table_row_count(source_conn, table)
                target_count = self._get_table_row_count(target_conn, table)
                
                if source_count != target_count:
                    table_status[table] = {
                        "synced": False,
                        "reason": "行数不同",
                        "source_rows": source_count,
                        "target_rows": target_count
                    }
                    all_synced = False
                    continue
                
                # 如果行数相同且不为0，检查数据哈希
                if source_count > 0:
                    source_hash = self._get_table_data_hash(source_conn, table)
                    target_hash = self._get_table_data_hash(target_conn, table)
                    
                    if source_hash != target_hash:
                        table_status[table] = {
                            "synced": False,
                            "reason": "数据内容不同",
                            "source_hash": source_hash[:16] + "...",
                            "target_hash": target_hash[:16] + "..."
                        }
                        all_synced = False
                        continue
                
                table_status[table] = {
                    "synced": True,
                    "rows": source_count
                }
            
            source_conn.close()
            target_conn.close()
            
            return all_synced, {
                "tables_checked": len(source_tables),
                "tables_synced": sum(1 for s in table_status.values() if s["synced"]),
                "table_details": table_status
            }
            
        except Exception as e:
            return False, {"reason": f"检查失败: {str(e)}"}
    
    def _get_table_row_count(self, conn: MigrationConnection, table_name: str) -> int:
        """获取表的行数"""
        from sqlalchemy import text
        with conn.engine.connect() as db_conn:
            result = db_conn.execute(text(f"SELECT COUNT(*) FROM \"{table_name}\""))
            return result.scalar()
    
    def _get_table_data_hash(self, conn: MigrationConnection, table_name: str) -> str:
        """获取表数据的哈希值（用于快速比较）"""
        import hashlib
        from sqlalchemy import text
        
        with conn.engine.connect() as db_conn:
            # 获取所有数据并计算哈希
            result = db_conn.execute(text(f"SELECT * FROM \"{table_name}\" ORDER BY id"))
            rows = result.fetchall()
            
            # 将所有行转换为字符串并计算哈希
            data_str = ""
            for row in rows:
                data_str += str(row)
            
            return hashlib.md5(data_str.encode()).hexdigest()


def run_precheck(source_url: str, target_url: str, check_sync: bool = True) -> PrecheckReport:
    """
    执行数据库迁移预检查
    
    Args:
        source_url: 源数据库连接URL
        target_url: 目标数据库连接URL
        check_sync: 是否检查同步状态
    
    Returns:
        PrecheckReport: 预检查报告
    """
    prechecker = DatabasePrechecker(source_url, target_url)
    report = prechecker.run_precheck()
    
    # 如果预检查通过，检查同步状态
    if check_sync and report.passed:
        is_synced, sync_details = prechecker.check_sync_status()
        report.is_synced = is_synced
        report.sync_details = sync_details
        
        if is_synced:
            report.results.append(CheckResult(
                passed=True,
                severity="info",
                category="sync",
                message="源数据库和目标数据库已同步，无需迁移",
                details=sync_details
            ))
    
    return report


def run_precheck_from_env(target_url: str) -> PrecheckReport:
    """
    使用环境变量中的源数据库URL执行预检查
    
    Args:
        target_url: 目标数据库连接URL
    
    Returns:
        PrecheckReport: 预检查报告
    """
    from config import get_config
    config = get_config()
    source_url = config.database.url
    return run_precheck(source_url, target_url)
