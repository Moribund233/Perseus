/**
 * Nginx管理命令模块
 *
 * 提供Nginx状态查询、启动、停止、配置管理等功能
 */
use crate::core::config;
use crate::models::{
    NginxActionResponse, NginxConfigSaveResponse, NginxProxyConfig, NginxStatusResponse,
    PlatformInfo,
};

/**
 * 获取Nginx状态
 *
 * @return Nginx状态响应
 */
#[tauri::command]
pub fn get_nginx_status() -> Result<NginxStatusResponse, String> {
    Ok(crate::services::nginx::get_nginx_status())
}

/**
 * 载入Nginx
 *
 * @param exe_path Nginx可执行文件路径
 * @return 操作响应
 */
#[tauri::command]
pub fn load_nginx(exe_path: String) -> Result<NginxActionResponse, String> {
    Ok(crate::services::nginx::load_nginx(exe_path))
}

/**
 * 启动Nginx
 *
 * @return 操作响应
 */
#[tauri::command]
pub fn start_nginx() -> Result<NginxActionResponse, String> {
    Ok(crate::services::nginx::start_nginx())
}

/**
 * 停止Nginx
 *
 * @return 操作响应
 */
#[tauri::command]
pub fn stop_nginx() -> Result<NginxActionResponse, String> {
    Ok(crate::services::nginx::stop_nginx())
}

/**
 * 重启Nginx
 *
 * @return 操作响应
 */
#[tauri::command]
pub fn restart_nginx() -> Result<NginxActionResponse, String> {
    Ok(crate::services::nginx::restart_nginx())
}

/**
 * 下载并解压Nginx
 *
 * @param url 下载URL
 * @param target_dir 目标目录
 * @return 操作响应
 */
#[tauri::command]
pub async fn download_and_extract_nginx(
    url: String,
    target_dir: Option<String>,
) -> Result<NginxActionResponse, String> {
    Ok(crate::services::nginx::download_and_extract_nginx(url, target_dir).await)
}

/**
 * 获取Nginx下载URL
 *
 * @return 下载URL
 */
#[tauri::command]
pub fn get_nginx_download_url() -> Result<String, String> {
    Ok(crate::services::nginx::get_nginx_download_url())
}

/**
 * 更新Nginx下载URL
 *
 * @param url 新的下载URL
 * @return 操作响应
 */
#[tauri::command]
pub fn update_nginx_download_url(url: String) -> Result<NginxActionResponse, String> {
    Ok(crate::services::nginx::update_nginx_download_url(url))
}

/**
 * 验证Nginx可执行文件
 *
 * @param exe_path 可执行文件路径
 * @return 验证结果
 */
#[tauri::command]
pub fn validate_nginx(exe_path: String) -> Result<String, String> {
    crate::services::nginx::validate_nginx(&exe_path)
}

/**
 * 获取Nginx代理配置
 *
 * @return 代理配置
 */
#[tauri::command]
pub fn get_nginx_proxy_config() -> Result<NginxProxyConfig, String> {
    Ok(crate::services::nginx::get_nginx_proxy_config())
}

/**
 * 保存Nginx代理配置
 *
 * @param config 代理配置
 * @return 保存响应
 */
#[tauri::command]
pub fn save_nginx_proxy_config(
    config: NginxProxyConfig,
) -> Result<NginxConfigSaveResponse, String> {
    Ok(crate::services::nginx::save_nginx_proxy_config(config))
}

/**
 * 获取平台信息
 *
 * @return 平台信息
 */
#[tauri::command]
pub fn get_platform_info() -> Result<PlatformInfo, String> {
    let config = config::load_config()?;
    Ok(config.platform)
}
