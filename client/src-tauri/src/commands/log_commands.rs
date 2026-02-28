/**
 * 日志管理命令模块
 *
 * 提供日志信息查询、内容获取和清理功能
 */
use crate::core::api_client;
use crate::models::{LogCleanupResponse, LogContentResponse, LogInfoResponse};

/**
 * 获取日志信息
 *
 * @return 日志信息响应
 */
#[tauri::command]
pub async fn get_log_info() -> Result<LogInfoResponse, String> {
    api_client::get_log_info().await
}

/**
 * 获取日志内容
 *
 * @param date 日期（可选）
 * @param log_name 日志名称
 * @param lines 行数
 * @param level 日志级别（可选）
 * @return 日志内容响应
 */
#[tauri::command]
pub async fn get_log_content(
    date: Option<String>,
    log_name: String,
    lines: i32,
    level: Option<String>,
) -> Result<LogContentResponse, String> {
    api_client::get_log_content(date, log_name, lines, level).await
}

/**
 * 清理旧日志
 *
 * @param keep_days 保留天数
 * @return 清理响应
 */
#[tauri::command]
pub async fn cleanup_logs(keep_days: i32) -> Result<LogCleanupResponse, String> {
    api_client::cleanup_logs(keep_days).await
}
