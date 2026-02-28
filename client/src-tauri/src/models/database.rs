/**
 * 数据库迁移相关模型
 *
 * 定义数据库预检查、迁移、切换等数据结构
 */
use serde::{Deserialize, Serialize};

/// 预检查请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrecheckRequest {
    pub target_url: String,
}

/// 检查结果项
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckResult {
    pub passed: bool,
    pub severity: String,
    pub category: String,
    pub message: String,
    pub details: Option<serde_json::Value>,
}

/// 预检查响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrecheckResponse {
    pub source_db_type: String,
    pub target_db_type: String,
    pub passed: bool,
    pub is_synced: bool,
    pub sync_details: Option<SyncDetails>,
    pub summary: CheckSummary,
    pub errors: Vec<CheckResult>,
    pub warnings: Vec<CheckResult>,
    pub infos: Vec<CheckResult>,
}

/// 同步详情
/// 使用灵活的结构，因为服务端返回的字段可能不同
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncDetails {
    #[serde(default)]
    pub tables_checked: Option<i32>,
    #[serde(default)]
    pub tables_synced: Option<i32>,
    #[serde(default)]
    pub table_details: Option<serde_json::Value>,
    #[serde(default)]
    pub reason: Option<String>,
    #[serde(default)]
    pub source_tables: Option<i32>,
    #[serde(default)]
    pub target_tables: Option<i32>,
    #[serde(default)]
    pub missing_in_target: Option<Vec<String>>,
    #[serde(default)]
    pub missing_in_source: Option<Vec<String>>,
}

/// 检查摘要
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckSummary {
    pub total: i32,
    pub errors: i32,
    pub warnings: i32,
    pub infos: i32,
}

/// 迁移请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MigrationRequest {
    pub target_url: String,
    pub batch_size: Option<i32>,
    pub tables: Option<Vec<String>>,
}

/// 表迁移进度
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TableProgress {
    pub table_name: String,
    pub total_rows: i32,
    pub migrated_rows: i32,
    pub status: String,
    pub started_at: Option<String>,
    pub completed_at: Option<String>,
    pub error_message: Option<String>,
}

/// 迁移错误
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MigrationError {
    pub table: String,
    pub error: String,
}

/// 迁移响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MigrationResponse {
    pub success: bool,
    pub tables_migrated: i32,
    pub tables_failed: i32,
    pub total_rows_migrated: i32,
    pub total_rows_failed: i32,
    pub duration_seconds: f64,
    pub table_progress: Vec<TableProgress>,
    pub errors: Vec<MigrationError>,
    pub skipped: Option<bool>,
    pub skip_reason: Option<String>,
}

/// 数据库切换请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseSwitchRequest {
    pub db_type: String,
    pub target_url: String,
}

/// 数据库切换响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseSwitchResponse {
    pub success: bool,
    pub message: String,
    pub need_migration: bool,
    pub migration_result: Option<MigrationResponse>,
    pub need_restart: bool,
}
