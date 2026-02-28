/**
 * 配置管理命令模块
 *
 * 提供应用配置和客户端配置的获取、更新、验证功能
 */
use crate::core::api_client;
use crate::core::config;
use crate::models::{ClientConfig, ConfigResponse};

// ==================== 应用配置命令 ====================

/**
 * 获取应用配置
 *
 * @param section 配置节（可选）
 * @return 配置响应
 */
#[tauri::command]
pub async fn get_app_config(section: Option<String>) -> Result<ConfigResponse, String> {
    api_client::get_app_config(section).await
}

/**
 * 更新应用配置
 *
 * @param config 配置JSON
 * @return 配置响应
 */
#[tauri::command]
pub async fn update_app_config(config: serde_json::Value) -> Result<ConfigResponse, String> {
    api_client::update_app_config(config).await
}

/**
 * 重置应用配置
 *
 * @return 配置响应
 */
#[tauri::command]
pub async fn reset_app_config() -> Result<ConfigResponse, String> {
    api_client::reset_app_config().await
}

/**
 * 验证应用配置
 *
 * @param config 配置JSON（可选）
 * @return 配置响应
 */
#[tauri::command]
pub async fn validate_app_config(
    config: Option<serde_json::Value>,
) -> Result<ConfigResponse, String> {
    api_client::validate_app_config(config).await
}

// ==================== 客户端配置命令 ====================

/**
 * 获取客户端配置
 *
 * @return 客户端配置
 */
#[tauri::command]
pub fn get_client_config() -> Result<ClientConfig, String> {
    config::load_config()
}

/**
 * 保存客户端配置
 *
 * @param config 客户端配置
 */
#[tauri::command]
pub fn save_client_config(config: ClientConfig) -> Result<(), String> {
    config::save_config(&config)
}

/**
 * 更新服务端地址
 *
 * @param url 服务端URL
 */
#[tauri::command]
pub fn update_server_url(url: String) -> Result<(), String> {
    config::update_server_url(url)
}

/**
 * 更新认证令牌
 *
 * @param token 认证令牌（可选）
 */
#[tauri::command]
pub fn update_auth_token(token: Option<String>) -> Result<(), String> {
    config::update_auth_token(token)
}

/**
 * 获取服务端地址
 *
 * @return 服务端URL
 */
#[tauri::command]
pub fn get_server_url() -> Result<String, String> {
    config::get_server_url()
}
