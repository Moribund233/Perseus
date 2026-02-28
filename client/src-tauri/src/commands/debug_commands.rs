/**
 * Debug 端点命令模块
 *
 * 提供调试相关的功能，如重置数据库、重置配置等
 */
use crate::core::api_client;

/**
 * 重置数据库
 *
 * @param force 是否强制重置
 * @param create_test_data 是否创建测试数据
 * @return 操作结果JSON
 */
#[tauri::command]
pub async fn reset_database(
    force: bool,
    create_test_data: bool,
) -> Result<serde_json::Value, String> {
    api_client::reset_database(force, create_test_data).await
}

/**
 * 重置配置文件
 *
 * @param force 是否强制重置
 * @param backup 是否备份
 * @return 操作结果JSON
 */
#[tauri::command]
pub async fn reset_config(force: bool, backup: bool) -> Result<serde_json::Value, String> {
    api_client::reset_config(force, backup).await
}

/**
 * 获取调试状态
 *
 * @return 调试状态JSON
 */
#[tauri::command]
pub async fn get_debug_status() -> Result<serde_json::Value, String> {
    api_client::get_debug_status().await
}
