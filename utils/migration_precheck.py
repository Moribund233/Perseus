"""
数据库迁移预检查工具

提供智能的跨数据库迁移预检查功能
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from utils.logging import get_named_logger
from utils.migration import Connection, SchemaReader, DbType, Dialect
from utils.migration.schema import SchemaComparator, TypeMapper
from utils.db_validation import validate_database_url, check_driver_installed

logger = get_named_logger("migration")


@dataclass
class CheckResult:
    """检查结果"""
    passed: bool
    severity: str
    category: str
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class PrecheckReport:
    """预检查报告"""
    source_db_type: str
    target_db_type: str
    passed: bool
    results: List[CheckResult] = field(default_factory=list)
    is_synced: bool = False
    sync_details: Optional[Dict[str, Any]] = None
    
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
    
    INCOMPATIBLE_TYPES = {
        (DbType.MYSQL, DbType.POSTGRESQL): [
            {"from": "TINYINT(1)", "to": "BOOLEAN", "note": "MySQL TINYINT(1) 转换为 PostgreSQL BOOLEAN"},
            {"from": "MEDIUMTEXT", "to": "TEXT", "note": "MySQL MEDIUMTEXT 映射为 PostgreSQL TEXT"},
            {"from": "LONGTEXT", "to": "TEXT", "note": "MySQL LONGTEXT 映射为 PostgreSQL TEXT"},
        ],
        (DbType.POSTGRESQL, DbType.MYSQL): [
            {"from": "JSONB", "to": "JSON", "note": "PostgreSQL JSONB 转换为 MySQL JSON"},
            {"from": "ARRAY", "to": "TEXT", "note": "PostgreSQL ARRAY 类型需要自定义处理"},
            {"from": "UUID", "to": "VARCHAR(36)", "note": "PostgreSQL UUID 转换为 MySQL VARCHAR"},
        ],
        (DbType.SQLITE, DbType.MYSQL): [
            {"from": "INTEGER", "to": "INTEGER/BIGINT", "note": "SQLite INTEGER 可能溢出"},
            {"from": "DATETIME", "to": "TEXT", "note": "SQLite 无原生 DATETIME 类型"},
            {"from": "BOOLEAN", "to": "INTEGER", "note": "SQLite 无原生 BOOLEAN 类型"},
        ],
    }
    
    def __init__(self, source_url: str, target_url: str):
        self.source_url = source_url
        self.target_url = target_url
        self.source_db_type = DbType.detect(source_url)
        self.target_db_type = DbType.detect(target_url)
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
            source_db_type=self.source_db_type.value,
            target_db_type=self.target_db_type.value,
            passed=passed,
            results=self.results
        )
    
    def _check_url_validity(self):
        """检查 URL 有效性"""
        source_valid, source_error = validate_database_url(self.source_url)
        if not source_valid:
            self.results.append(CheckResult(
                passed=False, severity="error", category="connection",
                message=f"源数据库URL无效: {source_error}"
            ))
        
        target_valid, target_error = validate_database_url(self.target_url)
        if not target_valid:
            self.results.append(CheckResult(
                passed=False, severity="error", category="connection",
                message=f"目标数据库URL无效: {target_error}"
            ))
    
    def _check_driver_availability(self):
        """检查数据库驱动是否安装"""
        source_installed, source_msg = check_driver_installed(self.source_db_type.value, self.source_url)
        if not source_installed:
            self.results.append(CheckResult(
                passed=False, severity="error", category="connection",
                message=f"源数据库驱动未安装: {source_msg}"
            ))
        
        target_installed, target_msg = check_driver_installed(self.target_db_type.value, self.target_url)
        if not target_installed:
            self.results.append(CheckResult(
                passed=False, severity="error", category="connection",
                message=f"目标数据库驱动未安装: {target_msg}"
            ))
    
    def _check_connection(self):
        """检查数据库连接"""
        for name, url in [("源", self.source_url), ("目标", self.target_url)]:
            try:
                conn = Connection(url)
                ok, error = conn.test_connection(auto_create_db=(name == "目标"))
                conn.close()
                
                if ok:
                    self.results.append(CheckResult(
                        passed=True, severity="info", category="connection",
                        message=f"{name}数据库连接成功" + ("（如数据库不存在已自动创建）" if name == "目标" else "")
                    ))
                else:
                    self.results.append(CheckResult(
                        passed=False, severity="error", category="connection",
                        message=f"{name}数据库连接失败: {error}"
                    ))
            except Exception as e:
                self.results.append(CheckResult(
                    passed=False, severity="error", category="connection",
                    message=f"{name}数据库连接异常: {str(e)}"
                ))
    
    def _check_schema_compatibility(self):
        """检查表结构兼容性"""
        try:
            source_conn = Connection(self.source_url)
            target_conn = Connection(self.target_url)
            
            source_reader = SchemaReader(source_conn)
            target_reader = SchemaReader(target_conn)
            
            comparator = SchemaComparator(source_reader, target_reader)
            comparison = comparator.compare()
            
            if comparison["source_empty"]:
                self.results.append(CheckResult(
                    passed=False, severity="error", category="schema",
                    message="源数据库中没有表"
                ))
                source_conn.close()
                target_conn.close()
                return
            
            if comparison["missing_in_target"]:
                self.results.append(CheckResult(
                    passed=True, severity="info", category="schema",
                    message=f"目标数据库缺少以下表: {', '.join(comparison['missing_in_target'])}",
                    details={"missing_tables": list(comparison['missing_in_target'])}
                ))
            
            if comparison["target_empty"]:
                self.results.append(CheckResult(
                    passed=True, severity="info", category="schema",
                    message=f"目标数据库为空，将迁移 {len(comparison['source_tables'])} 个表",
                    details={"tables_to_migrate": list(comparison['source_tables'])}
                ))
            
            for table in comparison["common_tables"]:
                self._check_table_compatibility(source_reader, target_reader, table)
            
            source_conn.close()
            target_conn.close()
            
        except Exception as e:
            self.results.append(CheckResult(
                passed=False, severity="error", category="schema",
                message=f"检查表结构兼容性时发生错误: {str(e)}"
            ))
    
    def _check_table_compatibility(self, source_reader: SchemaReader, target_reader: SchemaReader, table: str):
        """检查单个表的兼容性"""
        source_schema = source_reader.get_table_schema(table)
        target_schema = target_reader.get_table_schema(table)
        
        source_cols = {c.name: c for c in source_schema.columns}
        target_cols = {c.name: c for c in target_schema.columns}
        
        missing_cols = set(source_cols.keys()) - set(target_cols.keys())
        if missing_cols:
            self.results.append(CheckResult(
                passed=True, severity="warning", category="schema",
                message=f"表 {table} 在目标数据库中缺少列: {', '.join(missing_cols)}",
                details={"table": table, "missing_columns": list(missing_cols)}
            ))
        
        common_cols = set(source_cols.keys()) & set(target_cols.keys())
        for col in common_cols:
            source_type = TypeMapper.normalize_type(self.source_db_type.value, source_cols[col].type)
            target_type = TypeMapper.normalize_type(self.target_db_type.value, target_cols[col].type)
            
            if source_type != target_type:
                self.results.append(CheckResult(
                    passed=True, severity="warning", category="data",
                    message=f"表 {table} 列 {col} 类型可能不兼容: {source_cols[col].type} -> {target_cols[col].type}",
                    details={
                        "table": table, "column": col,
                        "source_type": source_cols[col].type,
                        "target_type": target_cols[col].type
                    }
                ))
    
    def _check_data_type_compatibility(self):
        """检查数据类型兼容性"""
        key = (self.source_db_type, self.target_db_type)
        incompatible = self.INCOMPATIBLE_TYPES.get(key, [])
        
        if incompatible:
            self.results.append(CheckResult(
                passed=True, severity="warning", category="compatibility",
                message=f"检测到 {len(incompatible)} 种可能不兼容的数据类型转换",
                details={"incompatible_types": incompatible}
            ))
        else:
            self.results.append(CheckResult(
                passed=True, severity="info", category="compatibility",
                message="数据类型兼容性检查通过"
            ))
    
    def _check_special_features(self):
        """检查特殊功能兼容性"""
        try:
            source_conn = Connection(self.source_url)
            source_inspector = source_conn.inspector
            
            source_views = source_inspector.get_view_names()
            if source_views:
                self.results.append(CheckResult(
                    passed=True, severity="warning", category="compatibility",
                    message=f"源数据库包含 {len(source_views)} 个视图，视图迁移需要额外处理",
                    details={"views": source_views}
                ))
            
            source_conn.close()
        except Exception:
            pass
    
    def check_sync_status(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        智能检测源数据库和目标数据库是否已同步
        
        Returns:
            Tuple[bool, Optional[Dict]]: (是否已同步, 同步详情)
        """
        try:
            source_conn = Connection(self.source_url)
            target_conn = Connection(self.target_url)
            
            source_reader = SchemaReader(source_conn)
            target_reader = SchemaReader(target_conn)
            
            source_tables = set(source_reader.get_all_tables())
            target_tables = set(target_reader.get_all_tables())
            
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
            
            table_status = {}
            all_synced = True
            
            for table in source_tables:
                source_schema = source_reader.get_table_schema(table)
                target_schema = target_reader.get_table_schema(table)
                
                source_cols = {c.name for c in source_schema.columns}
                target_cols = {c.name for c in target_schema.columns}
                
                if source_cols != target_cols:
                    table_status[table] = {"synced": False, "reason": "列不同"}
                    all_synced = False
                    continue
                
                dialect = source_conn.dialect
                source_count = source_conn.fetch_scalar(f"SELECT COUNT(*) FROM {dialect.quote_ident(table)}")
                target_count = target_conn.fetch_scalar(f"SELECT COUNT(*) FROM {dialect.quote_ident(table)}")
                
                if source_count != target_count:
                    table_status[table] = {
                        "synced": False, "reason": "行数不同",
                        "source_rows": source_count, "target_rows": target_count
                    }
                    all_synced = False
                    continue
                
                if source_count > 0:
                    import hashlib
                    source_rows = source_conn.fetch_all(f"SELECT * FROM {dialect.quote_ident(table)} ORDER BY id")
                    target_rows = target_conn.fetch_all(f"SELECT * FROM {dialect.quote_ident(table)} ORDER BY id")
                    
                    source_hash = hashlib.md5(str(source_rows).encode()).hexdigest()
                    target_hash = hashlib.md5(str(target_rows).encode()).hexdigest()
                    
                    if source_hash != target_hash:
                        table_status[table] = {
                            "synced": False, "reason": "数据内容不同",
                            "source_hash": source_hash[:16] + "...",
                            "target_hash": target_hash[:16] + "..."
                        }
                        all_synced = False
                        continue
                
                table_status[table] = {"synced": True, "rows": source_count}
            
            source_conn.close()
            target_conn.close()
            
            return all_synced, {
                "tables_checked": len(source_tables),
                "tables_synced": sum(1 for s in table_status.values() if s["synced"]),
                "table_details": table_status
            }
            
        except Exception as e:
            return False, {"reason": f"检查失败: {str(e)}"}


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
    
    if check_sync and report.passed:
        synced, details = prechecker.check_sync_status()
        report.is_synced = synced
        report.sync_details = details
    
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
