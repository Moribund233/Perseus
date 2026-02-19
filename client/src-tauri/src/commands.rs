/**
 * Tauri 命令模块
 *
 * 定义前端可调用的 Rust 命令
 */
use std::sync::Mutex;

use crate::api_client;
use crate::config;
use crate::models::*;
use crate::process_manager;

/// 应用状态
pub struct AppState {
    pub server_pid: Mutex<Option<u32>>,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            server_pid: Mutex::new(None),
        }
    }
}

// ==================== 服务控制命令 ====================

/// 获取服务状态
#[tauri::command]
pub async fn get_service_status() -> Result<ServiceStatus, String> {
    api_client::get_service_status().await
}

/// 启动服务
#[tauri::command]
pub async fn start_service() -> Result<ActionResponse, String> {
    match process_manager::start_server() {
        Ok(pid) => Ok(ActionResponse {
            success: true,
            message: format!("服务已启动 (PID: {})", pid),
        }),
        Err(e) => Ok(ActionResponse {
            success: false,
            message: e,
        }),
    }
}

/// 停止服务
#[tauri::command]
pub async fn stop_service() -> Result<ActionResponse, String> {
    // 先尝试通过 API 优雅关闭
    match api_client::stop_service().await {
        Ok(response) => {
            if response.success {
                // 等待一段时间后检查进程是否已停止
                tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
            }
        }
        Err(_) => {
            // API 调用失败，直接强制停止
        }
    }

    // 强制停止进程
    match process_manager::stop_server() {
        Ok(_) => Ok(ActionResponse {
            success: true,
            message: "服务已停止".to_string(),
        }),
        Err(e) => Ok(ActionResponse {
            success: false,
            message: e,
        }),
    }
}

/// 重启服务
#[tauri::command]
pub async fn restart_service() -> Result<ActionResponse, String> {
    // 先停止服务
    let _ = stop_service().await;

    // 等待一段时间
    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

    // 启动服务
    start_service().await
}

/// 检查服务是否运行
#[tauri::command]
pub fn is_service_running() -> bool {
    process_manager::is_server_running()
}

// ==================== 性能监控命令 ====================

/// 获取性能数据
#[tauri::command]
pub fn get_performance_data() -> Result<PerformanceData, String> {
    let resources = process_manager::get_system_resources();

    // 获取服务端进程信息
    let server_info = process_manager::get_server_info();

    let memory = if let Some(info) = server_info {
        info.memory_mb
    } else {
        resources.memory_used_mb
    };

    // 这里简化处理，实际应该维护一个请求计数器
    Ok(PerformanceData {
        cpu: resources.cpu_usage as f64,
        memory,
        uptime: 0, // 从服务状态获取
        requests: 0,
    })
}

/// 获取系统资源使用情况
#[tauri::command]
pub fn get_system_resources() -> Result<process_manager::SystemResources, String> {
    Ok(process_manager::get_system_resources())
}

/// 获取服务端进程信息
#[tauri::command]
pub fn get_server_process_info() -> Result<Option<process_manager::ProcessInfo>, String> {
    Ok(process_manager::get_server_info())
}

// ==================== 日志管理命令 ====================

/// 获取日志信息
#[tauri::command]
pub async fn get_log_info() -> Result<LogInfoResponse, String> {
    api_client::get_log_info().await
}

/// 获取日志内容
#[tauri::command]
pub async fn get_log_content(
    date: Option<String>,
    log_name: String,
    lines: i32,
    level: Option<String>,
) -> Result<LogContentResponse, String> {
    api_client::get_log_content(date, log_name, lines, level).await
}

/// 清理旧日志
#[tauri::command]
pub async fn cleanup_logs(keep_days: i32) -> Result<LogCleanupResponse, String> {
    api_client::cleanup_logs(keep_days).await
}

// ==================== 配置管理命令 ====================

/// 获取应用配置
#[tauri::command]
pub async fn get_app_config(section: Option<String>) -> Result<ConfigResponse, String> {
    api_client::get_app_config(section).await
}

/// 更新应用配置
#[tauri::command]
pub async fn update_app_config(config: serde_json::Value) -> Result<ConfigResponse, String> {
    api_client::update_app_config(config).await
}

/// 重置应用配置
#[tauri::command]
pub async fn reset_app_config() -> Result<ConfigResponse, String> {
    api_client::reset_app_config().await
}

/// 验证应用配置
#[tauri::command]
pub async fn validate_app_config(
    config: Option<serde_json::Value>,
) -> Result<ConfigResponse, String> {
    api_client::validate_app_config(config).await
}

// ==================== 客户端配置命令 ====================

/// 获取客户端配置
#[tauri::command]
pub fn get_client_config() -> Result<ClientConfig, String> {
    config::load_config()
}

/// 保存客户端配置
#[tauri::command]
pub fn save_client_config(config: ClientConfig) -> Result<(), String> {
    config::save_config(&config)
}

/// 更新服务端地址
#[tauri::command]
pub fn update_server_url(url: String) -> Result<(), String> {
    config::update_server_url(url)
}

/// 更新认证令牌
#[tauri::command]
pub fn update_auth_token(token: Option<String>) -> Result<(), String> {
    config::update_auth_token(token)
}

/// 获取服务端地址
#[tauri::command]
pub fn get_server_url() -> Result<String, String> {
    config::get_server_url()
}

// ==================== 健康检查命令 ====================

/// 检查服务端连接
#[tauri::command]
pub async fn check_connection() -> Result<bool, String> {
    match api_client::get_service_status().await {
        Ok(_) => Ok(true),
        Err(e) => {
            log::warn!("检查连接失败: {}", e);
            Ok(false)
        }
    }
}

/// 获取健康状态（不需要认证）
#[tauri::command]
pub async fn get_health_status() -> Result<serde_json::Value, String> {
    let client = api_client::ApiClient::new_without_local_auth()?;
    client.get("/health").await
}

// ==================== 本地系统信息命令 ====================

/// 获取本地系统信息
#[tauri::command]
pub fn get_local_system_info() -> Result<SystemInfo, String> {
    use sysinfo::{CpuRefreshKind, MemoryRefreshKind, RefreshKind, System};

    let mut sys = System::new_with_specifics(
        RefreshKind::new()
            .with_cpu(CpuRefreshKind::everything())
            .with_memory(MemoryRefreshKind::everything()),
    );

    // 刷新系统信息
    sys.refresh_all();

    // 获取CPU信息
    let cpu_count = sys.cpus().len() as i32;
    let cpu_freq_mhz = sys.cpus().first().map(|c| c.frequency() as f64);
    // global_cpu_usage() 需要刷新后才能使用
    let cpu_percent =
        sys.cpus().iter().map(|c| c.cpu_usage() as f64).sum::<f64>() / cpu_count as f64;

    // 获取内存信息（sysinfo 0.30 返回的是字节，转换为GB需要除以 1024 * 1024 * 1024）
    let memory_total_gb = sys.total_memory() as f64 / (1024.0 * 1024.0 * 1024.0);
    let memory_used_gb = sys.used_memory() as f64 / (1024.0 * 1024.0 * 1024.0);
    let memory_percent = if memory_total_gb > 0.0 {
        (memory_used_gb / memory_total_gb) * 100.0
    } else {
        0.0
    };

    // 获取平台信息
    let platform = std::env::consts::OS.to_string();
    let architecture = std::env::consts::ARCH.to_string();

    // 获取主机名和处理器信息
    // host_name() 和 kernel_version() 是关联函数，不是方法
    let hostname = System::host_name().unwrap_or_else(|| "Unknown".to_string());
    let processor = sys
        .cpus()
        .first()
        .map(|c| c.brand().to_string())
        .unwrap_or_else(|| "Unknown".to_string());

    // 获取平台版本（使用内核版本）
    let platform_version = System::kernel_version().unwrap_or_else(|| "Unknown".to_string());

    // 获取磁盘信息（简化处理）
    let disk_total_gb = 0.0;
    let disk_used_gb = 0.0;
    let disk_percent = 0.0;

    // 获取网络信息
    let network_info = get_network_info();

    Ok(SystemInfo {
        platform,
        platform_version,
        architecture,
        processor,
        hostname,
        cpu_count,
        cpu_freq_mhz,
        cpu_percent,
        memory_total_gb,
        memory_used_gb,
        memory_percent,
        disk_total_gb,
        disk_used_gb,
        disk_percent,
        network: network_info,
    })
}

/// 获取网络信息
fn get_network_info() -> crate::models::NetworkInfo {
    use sysinfo::Networks;

    let mut total_bytes_sent = 0u64;
    let mut total_bytes_received = 0u64;
    let mut total_packets_sent = 0u64;
    let mut total_packets_received = 0u64;
    let mut total_errors_in = 0u64;
    let mut total_errors_out = 0u64;

    // 创建 Networks 实例并刷新
    let networks = Networks::new_with_refreshed_list();

    // 遍历所有网络接口，累加统计数据
    for (_, data) in &networks {
        total_bytes_sent += data.total_transmitted();
        total_bytes_received += data.total_received();
        total_packets_sent += data.total_packets_transmitted();
        total_packets_received += data.total_packets_received();
        total_errors_in += data.errors_on_received();
        total_errors_out += data.errors_on_transmitted();
    }

    crate::models::NetworkInfo {
        bytes_sent: total_bytes_sent,
        bytes_received: total_bytes_received,
        packets_sent: total_packets_sent,
        packets_received: total_packets_received,
        errors_in: total_errors_in,
        errors_out: total_errors_out,
    }
}

// ==================== 本地认证命令 ====================

/// 获取本地认证 Token
/// 用于 WebSocket 连接认证
#[tauri::command]
pub fn get_local_token() -> Result<String, String> {
    let auth_config = crate::local_auth::get_local_auth_config()?;

    if auth_config.local_token.is_empty() {
        return Err("本地认证 Token 未初始化".to_string());
    }

    Ok(auth_config.local_token)
}

// ==================== Nginx管理命令 ====================

/// 获取Nginx状态
#[tauri::command]
pub fn get_nginx_status() -> Result<crate::models::NginxStatusResponse, String> {
    Ok(crate::nginx_manager::get_nginx_status())
}

/// 载入Nginx
#[tauri::command]
pub fn load_nginx(exe_path: String) -> Result<crate::models::NginxActionResponse, String> {
    Ok(crate::nginx_manager::load_nginx(exe_path))
}

/// 启动Nginx
#[tauri::command]
pub fn start_nginx() -> Result<crate::models::NginxActionResponse, String> {
    Ok(crate::nginx_manager::start_nginx())
}

/// 停止Nginx
#[tauri::command]
pub fn stop_nginx() -> Result<crate::models::NginxActionResponse, String> {
    Ok(crate::nginx_manager::stop_nginx())
}

/// 重启Nginx
#[tauri::command]
pub fn restart_nginx() -> Result<crate::models::NginxActionResponse, String> {
    Ok(crate::nginx_manager::restart_nginx())
}

/// 下载并解压Nginx
#[tauri::command]
pub async fn download_and_extract_nginx(
    url: String,
    target_dir: Option<String>,
) -> Result<crate::models::NginxActionResponse, String> {
    Ok(crate::nginx_manager::download_and_extract_nginx(url, target_dir).await)
}

/// 获取Nginx下载URL
#[tauri::command]
pub fn get_nginx_download_url() -> Result<String, String> {
    Ok(crate::nginx_manager::get_nginx_download_url())
}

/// 更新Nginx下载URL
#[tauri::command]
pub fn update_nginx_download_url(
    url: String,
) -> Result<crate::models::NginxActionResponse, String> {
    Ok(crate::nginx_manager::update_nginx_download_url(url))
}

/// 验证Nginx可执行文件
#[tauri::command]
pub fn validate_nginx(exe_path: String) -> Result<String, String> {
    crate::nginx_manager::validate_nginx(&exe_path)
}

/// 获取Nginx代理配置
#[tauri::command]
pub fn get_nginx_proxy_config() -> Result<crate::models::NginxProxyConfig, String> {
    Ok(crate::nginx_manager::get_nginx_proxy_config())
}

/// 保存Nginx代理配置
#[tauri::command]
pub fn save_nginx_proxy_config(
    config: crate::models::NginxProxyConfig,
) -> Result<crate::models::NginxConfigSaveResponse, String> {
    Ok(crate::nginx_manager::save_nginx_proxy_config(config))
}

/// 获取Nginx平台信息
#[tauri::command]
pub fn get_nginx_platform_info() -> Result<crate::models::NginxPlatformInfo, String> {
    Ok(crate::nginx_manager::get_nginx_platform_info())
}
