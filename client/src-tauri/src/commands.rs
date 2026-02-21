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
    // 先尝试通过 API 优雅关闭（使用3秒短超时，避免服务端挂起时长时间等待）
    match api_client::stop_service_with_timeout(3).await {
        Ok(response) => {
            if response.success {
                // 等待一段时间后检查进程是否已停止
                tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
            }
        }
        Err(e) => {
            // API 调用失败，记录日志后直接强制停止
            log::warn!("优雅关闭失败（{}），将强制停止进程", e);
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
    use sysinfo::System;

    // 使用全局 SYSTEM 实例，避免每次都重新初始化
    let mut system = process_manager::SYSTEM.lock().unwrap();

    // 刷新CPU和内存信息
    system.refresh_cpu();
    system.refresh_memory();

    // 获取CPU信息
    let cpu_count = system.cpus().len() as i32;
    let cpu_freq_mhz = system.cpus().first().map(|c| c.frequency() as f64);
    // 计算平均CPU使用率
    let cpu_percent = system
        .cpus()
        .iter()
        .map(|c| c.cpu_usage() as f64)
        .sum::<f64>()
        / cpu_count as f64;

    // 获取内存信息（sysinfo 0.30 返回的是字节，转换为GB需要除以 1024 * 1024 * 1024）
    let memory_total_gb = system.total_memory() as f64 / (1024.0 * 1024.0 * 1024.0);
    let memory_used_gb = system.used_memory() as f64 / (1024.0 * 1024.0 * 1024.0);
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
    let processor = system
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

// ==================== 引导页面命令 ====================

/// 检查服务端路径
#[tauri::command]
pub fn check_server_path() -> Result<crate::models::ServerCheckResult, String> {
    use crate::process_manager::get_server_exe_path;

    match get_server_exe_path() {
        Ok(path) => {
            let path_str = path.to_string_lossy().to_string();
            Ok(crate::models::ServerCheckResult {
                found: true,
                path: Some(path_str),
                version: None,
                auto_detected: true,
            })
        }
        Err(_) => Ok(crate::models::ServerCheckResult {
            found: false,
            path: None,
            version: None,
            auto_detected: false,
        }),
    }
}

/// 验证并保存服务端路径
#[tauri::command]
pub fn validate_and_save_server_path(
    path: String,
) -> Result<crate::models::ServerCheckResult, String> {
    use crate::config;
    use std::path::Path;

    let path_obj = Path::new(&path);

    // 检查文件是否存在
    if !path_obj.exists() {
        return Ok(crate::models::ServerCheckResult {
            found: false,
            path: None,
            version: None,
            auto_detected: false,
        });
    }

    // 检查文件名是否包含 langit-server
    let file_name = path_obj.file_name().and_then(|n| n.to_str()).unwrap_or("");
    if !file_name.contains("langit-server") {
        return Ok(crate::models::ServerCheckResult {
            found: false,
            path: None,
            version: None,
            auto_detected: false,
        });
    }

    // 保存到配置
    let mut client_config = config::load_config()?;
    client_config.server.path.custom_path = Some(path.clone());
    config::save_config(&client_config)?;

    Ok(crate::models::ServerCheckResult {
        found: true,
        path: Some(path),
        version: None,
        auto_detected: false,
    })
}

/// 检查Git安装
#[tauri::command]
pub fn check_git_installation() -> Result<crate::models::GitCheckResult, String> {
    use std::process::Command;

    // 检查 git --version
    let version_output = Command::new("git").arg("--version").output();

    match version_output {
        Ok(output) if output.status.success() => {
            let version = String::from_utf8_lossy(&output.stdout).trim().to_string();

            // 检查 git-http-backend 是否存在
            let http_backend_check = if cfg!(target_os = "windows") {
                Command::new("where")
                    .arg("git-http-backend")
                    .output()
                    .map(|o| o.status.success())
                    .unwrap_or(false)
            } else {
                Command::new("which")
                    .arg("git-http-backend")
                    .output()
                    .map(|o| o.status.success())
                    .unwrap_or(false)
            };

            Ok(crate::models::GitCheckResult {
                installed: true,
                version: Some(version),
                path: None,
                http_backend_available: http_backend_check,
            })
        }
        _ => Ok(crate::models::GitCheckResult {
            installed: false,
            version: None,
            path: None,
            http_backend_available: false,
        }),
    }
}

/// 标记引导完成
#[tauri::command]
pub fn mark_guide_completed() -> Result<(), String> {
    // 创建一个标记文件来表示引导已完成
    let config_dir = dirs::config_dir()
        .ok_or("无法获取配置目录")?
        .join("langit-client");

    std::fs::write(config_dir.join(".guide_completed"), "1")
        .map_err(|e| format!("创建标记文件失败: {}", e))?;

    Ok(())
}

/// 检查是否已完成引导
#[tauri::command]
pub fn is_guide_completed() -> Result<bool, String> {
    let config_dir = dirs::config_dir()
        .ok_or("无法获取配置目录")?
        .join("langit-client");
    let guide_marker = config_dir.join(".guide_completed");

    Ok(guide_marker.exists())
}

/// 检查是否存在用户配置文件
/// 用于判断是否需要显示引导页面
#[tauri::command]
pub fn has_user_config_file() -> Result<bool, String> {
    Ok(crate::config::has_user_config())
}

/// 重置客户端配置
/// 删除配置文件和引导标记，使应用重新进入引导流程
#[tauri::command]
pub fn reset_client_config() -> Result<(), String> {
    use crate::config;

    // 删除配置文件
    if let Some(config_path) = config::get_config_path() {
        if config_path.exists() {
            std::fs::remove_file(&config_path).map_err(|e| format!("删除配置文件失败: {}", e))?;
        }
    }

    // 删除引导标记文件
    let config_dir = dirs::config_dir()
        .ok_or("无法获取配置目录")?
        .join("langit-client");
    let guide_marker = config_dir.join(".guide_completed");
    if guide_marker.exists() {
        std::fs::remove_file(&guide_marker).map_err(|e| format!("删除引导标记失败: {}", e))?;
    }

    Ok(())
}

/// 设置客户端安全密码
#[tauri::command]
pub fn set_security_password(password: String) -> Result<(), String> {
    crate::secure_config::set_security_password(password)
}

/// 验证客户端安全密码
#[tauri::command]
pub fn verify_security_password(password: String) -> Result<bool, String> {
    crate::secure_config::verify_security_password(&password)
}

/// 检查是否已设置安全密码
#[tauri::command]
pub fn has_security_password() -> Result<bool, String> {
    crate::secure_config::has_security_password()
}

/// 获取调试模式状态
#[tauri::command]
pub fn get_debug_mode() -> Result<bool, String> {
    crate::secure_config::get_debug_mode()
}

/// 更新调试模式
#[tauri::command]
pub fn update_debug_mode(debug: bool) -> Result<(), String> {
    crate::secure_config::update_debug_mode(debug)
}

/// 重置所有安全令牌（需要管理员权限）
#[tauri::command]
pub fn reset_all_tokens() -> Result<(), String> {
    crate::secure_config::reset_all_tokens()
}

/// 检查是否以提升的权限运行
#[tauri::command]
pub fn is_elevated() -> Result<bool, String> {
    #[cfg(target_os = "windows")]
    {
        use std::process::Command;
        match Command::new("net").args(["session"]).output() {
            Ok(output) => Ok(output.status.success()),
            Err(_) => Ok(false),
        }
    }

    #[cfg(target_os = "linux")]
    {
        Ok(unsafe { libc::getuid() == 0 })
    }

    #[cfg(target_os = "macos")]
    {
        Ok(unsafe { libc::getuid() == 0 })
    }

    #[cfg(not(any(target_os = "windows", target_os = "linux", target_os = "macos")))]
    {
        Ok(false)
    }
}

/// 获取 JWT 密钥
#[tauri::command]
pub fn get_jwt_secret_key() -> Result<String, String> {
    crate::secure_config::get_jwt_secret_key()
}

// ==================== 数据库迁移命令 ====================

/// 获取数据库状态（从服务端 API）
#[tauri::command]
pub async fn get_database_status_from_api(
) -> Result<crate::api_client::DatabaseStatusResponse, String> {
    crate::api_client::get_database_status().await
}

/// 执行数据库迁移
#[tauri::command]
pub async fn migrate_database(
    source_type: String,
    target_type: String,
    source_url: String,
    target_url: String,
) -> Result<crate::api_client::DatabaseMigrateResponse, String> {
    let request = crate::api_client::DatabaseMigrateRequest {
        source_type,
        target_type,
        source_url,
        target_url,
    };
    crate::api_client::migrate_database(request).await
}

/// 测试数据库连接
#[tauri::command]
pub async fn test_database_connection(
    db_url: String,
) -> Result<crate::models::ConfigResponse, String> {
    crate::api_client::test_database_connection(db_url).await
}

// ==================== 压力测试和数据库配置命令 ====================

/// 获取压力测试模式状态
#[tauri::command]
pub fn get_stress_test() -> Result<bool, String> {
    crate::secure_config::get_stress_test()
}

/// 更新压力测试模式
#[tauri::command]
pub fn update_stress_test(stress: bool) -> Result<(), String> {
    crate::secure_config::update_stress_test(stress)
}

/// 获取所有数据库连接 URL
#[tauri::command]
pub fn get_database_urls() -> Result<std::collections::HashMap<String, String>, String> {
    crate::secure_config::get_database_urls()
}

/// 获取指定类型的数据库连接 URL
#[tauri::command]
pub fn get_database_url(db_type: String) -> Result<String, String> {
    crate::secure_config::get_database_url(&db_type)
}

/// 获取数据库类型（从 client.toml 读取）
#[tauri::command]
pub fn get_database_type() -> Result<String, String> {
    let config = crate::config::load_config()?;
    Ok(config.db_type)
}

/// 切换数据库类型（保存到 client.toml）
#[tauri::command]
pub fn switch_database_type(db_type: String) -> Result<(), String> {
    let mut config = crate::config::load_config()?;
    config.db_type = db_type;
    crate::config::save_config(&config)
}

/// 更新指定类型的数据库连接 URL
#[tauri::command]
pub fn update_database_url(db_type: String, url: String) -> Result<(), String> {
    crate::secure_config::update_database_url(db_type, url)
}
