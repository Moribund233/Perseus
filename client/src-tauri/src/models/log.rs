/**
 * 日志相关模型
 *
 * 定义日志信息、日志文件、日志内容等数据结构
 */
use serde::{Deserialize, Serialize};

/// 日志信息响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogInfoResponse {
    pub log_dir: String,
    pub today_dir: String,
    pub today_files: Vec<LogFileInfo>,
    pub available_dates: Vec<String>,
}

/// 日志文件信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogFileInfo {
    pub name: String,
    pub size: i64,
    pub size_formatted: String,
    pub modified: String,
}

/// 日志内容响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogContentResponse {
    pub date: String,
    pub log_name: String,
    pub lines: i32,
    pub total_lines: i32,
    pub content: String,
    pub exists: bool,
}

/// 日志清理响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogCleanupResponse {
    pub success: bool,
    pub deleted_count: i32,
    pub keep_days: i32,
}
