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

/// 检查服务端路径是否已配置
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
                auto_detected: false,
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

    if !path_obj.exists() {
        return Ok(crate::models::ServerCheckResult {
            found: false,
            path: None,
            version: None,
            auto_detected: false,
        });
    }

    let file_name = path_obj.file_name().and_then(|n| n.to_str()).unwrap_or("");
    if !file_name.contains("langit-server") {
        return Ok(crate::models::ServerCheckResult {
            found: false,
            path: None,
            version: None,
            auto_detected: false,
        });
    }

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

/// 重置所有安全令牌
#[tauri::command]
pub fn reset_all_tokens() -> Result<(), String> {
    crate::secure_config::reset_all_tokens()
}

/// 获取 JWT 密钥
#[tauri::command]
pub fn get_jwt_secret_key() -> Result<String, String> {
    crate::secure_config::get_jwt_secret_key()
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

// ==================== 数据库安装检测命令 ====================

/// 检测系统中已安装的数据库
///
/// 返回已安装的数据库类型列表：["sqlite", "postgresql", "mysql"]
/// - SQLite: 总是可用（内置于 Python）
/// - PostgreSQL: 检查 psql/pg_isready 命令是否存在
/// - MySQL: 检查 mysql/mysqld 命令是否存在
#[tauri::command]
pub async fn check_installed_databases() -> Result<Vec<String>, String> {
    let mut installed = vec!["sqlite".to_string()];

    // 检查 PostgreSQL (psql 或 pg_isready)
    if check_any_command_exists(&["psql", "pg_isready"]).await {
        installed.push("postgresql".to_string());
        log::info!("PostgreSQL 已安装");
    }

    // 检查 MySQL (mysql 或 mysqld)
    if check_any_command_exists(&["mysql", "mysqld"]).await {
        installed.push("mysql".to_string());
        log::info!("MySQL 已安装");
    }

    log::info!("已安装的数据库: {:?}", installed);
    Ok(installed)
}

/// 检查任一命令是否存在
async fn check_any_command_exists(commands: &[&str]) -> bool {
    for cmd in commands {
        if check_command_exists(cmd).await.unwrap_or(false) {
            return true;
        }
    }
    false
}

/// 检查命令是否存在
#[cfg(target_os = "windows")]
async fn check_command_exists(command: &str) -> Result<bool, std::io::Error> {
    tokio::process::Command::new("where")
        .arg(command)
        .output()
        .await
        .map(|output| output.status.success())
}

#[cfg(not(target_os = "windows"))]
async fn check_command_exists(command: &str) -> Result<bool, std::io::Error> {
    tokio::process::Command::new("which")
        .arg(command)
        .output()
        .await
        .map(|output| output.status.success())
}

// ==================== 数据库连接测试命令 ====================

/// 检查 SQLite 数据库文件是否存在
#[tauri::command]
pub fn check_sqlite_file(file_path: String) -> Result<bool, String> {
    use std::path::Path;

    let path = Path::new(&file_path);
    Ok(path.exists() && path.is_file())
}

/// 测试 TCP 连接（用于 PostgreSQL/MySQL）
#[tauri::command]
pub async fn test_tcp_connection(
    host: String,
    port: u16,
) -> Result<crate::models::TcpTestResult, String> {
    use tokio::net::TcpStream;
    use tokio::time::{timeout, Duration};

    let addr = format!("{}:{}", host, port);

    // 5秒超时
    let result = timeout(Duration::from_secs(5), TcpStream::connect(&addr)).await;

    match result {
        Ok(Ok(_)) => Ok(crate::models::TcpTestResult {
            success: true,
            error: None,
        }),
        Ok(Err(e)) => Ok(crate::models::TcpTestResult {
            success: false,
            error: Some(format!("连接失败: {}", e)),
        }),
        Err(_) => Ok(crate::models::TcpTestResult {
            success: false,
            error: Some("连接超时".to_string()),
        }),
    }
}

// ==================== 数据库迁移命令 ====================

/// 执行迁移预检查
#[tauri::command]
pub async fn precheck_migration(
    target_url: String,
) -> Result<crate::models::PrecheckResponse, String> {
    crate::api_client::precheck_migration(&target_url).await
}

/// 执行数据库迁移
#[tauri::command]
pub async fn execute_migration(
    target_url: String,
    batch_size: Option<i32>,
) -> Result<crate::models::MigrationResponse, String> {
    crate::api_client::execute_migration(&target_url, batch_size).await
}

/// 切换数据库
/// 完整的切换流程：预检查 -> 迁移（如需要）-> 更新配置
#[tauri::command]
pub async fn switch_database(
    db_type: String,
    target_url: String,
) -> Result<crate::models::DatabaseSwitchResponse, String> {
    log::info!("开始切换数据库: {} -> {}", db_type, target_url);

    // 保存原始数据库类型用于回滚
    let original_db_type = get_database_type()?;

    // 步骤1: 执行预检查
    log::info!("步骤1: 执行预检查...");
    let precheck_result = match crate::api_client::precheck_migration(&target_url).await {
        Ok(result) => result,
        Err(e) => {
            log::error!("预检查失败: {}", e);
            return Ok(crate::models::DatabaseSwitchResponse {
                success: false,
                message: format!("预检查失败: {}", e),
                need_migration: false,
                migration_result: None,
                need_restart: false,
            });
        }
    };

    // 检查预检查是否通过
    if !precheck_result.passed {
        let error_msg = precheck_result
            .errors
            .iter()
            .map(|e| e.message.clone())
            .collect::<Vec<_>>()
            .join("; ");
        log::error!("预检查未通过: {}", error_msg);
        return Ok(crate::models::DatabaseSwitchResponse {
            success: false,
            message: format!("预检查未通过: {}", error_msg),
            need_migration: false,
            migration_result: None,
            need_restart: false,
        });
    }

    // 步骤2: 先更新客户端配置中的数据库类型
    log::info!("步骤2: 更新客户端配置...");
    if let Err(e) = switch_database_type(db_type.clone()) {
        log::error!("更新数据库类型失败: {}", e);
        return Ok(crate::models::DatabaseSwitchResponse {
            success: false,
            message: format!("更新配置失败: {}", e),
            need_migration: false,
            migration_result: None,
            need_restart: false,
        });
    }

    // 步骤3: 检查是否需要迁移
    let need_migration = !precheck_result.is_synced;
    let mut migration_result: Option<crate::models::MigrationResponse> = None;

    if need_migration {
        log::info!("步骤3: 需要数据迁移，开始执行...");

        // 执行迁移
        match crate::api_client::execute_migration(&target_url, Some(1000)).await {
            Ok(result) => {
                if result.success {
                    log::info!(
                        "迁移成功: {} 个表, {} 行数据",
                        result.tables_migrated,
                        result.total_rows_migrated
                    );
                    migration_result = Some(result);
                } else {
                    log::error!("迁移失败，开始回滚...");
                    // 迁移失败，回滚数据库类型
                    let _ = switch_database_type(original_db_type.clone());

                    let error_msg = result
                        .errors
                        .iter()
                        .map(|e| format!("{}: {}", e.table, e.error))
                        .collect::<Vec<_>>()
                        .join("; ");

                    return Ok(crate::models::DatabaseSwitchResponse {
                        success: false,
                        message: format!("迁移失败: {}", error_msg),
                        need_migration: true,
                        migration_result: Some(result),
                        need_restart: false,
                    });
                }
            }
            Err(e) => {
                log::error!("迁移执行失败: {}，开始回滚...", e);
                // 迁移失败，回滚数据库类型
                let _ = switch_database_type(original_db_type.clone());

                return Ok(crate::models::DatabaseSwitchResponse {
                    success: false,
                    message: format!("迁移执行失败: {}", e),
                    need_migration: true,
                    migration_result: None,
                    need_restart: false,
                });
            }
        }
    } else {
        log::info!("步骤3: 数据库已同步，无需迁移");
    }

    // 步骤4: 更新环境变量配置
    log::info!("步骤4: 更新环境变量配置...");
    if let Err(e) = update_database_url(db_type.clone(), target_url) {
        log::error!("更新数据库URL失败: {}，开始回滚...", e);
        // 回滚数据库类型
        let _ = switch_database_type(original_db_type.clone());

        return Ok(crate::models::DatabaseSwitchResponse {
            success: false,
            message: format!("更新数据库URL失败: {}", e),
            need_migration,
            migration_result: migration_result.clone(),
            need_restart: false,
        });
    }

    // 步骤5: 返回成功结果
    let message = if need_migration {
        format!(
            "数据库切换成功，已迁移 {} 个表",
            migration_result
                .as_ref()
                .map(|r| r.tables_migrated)
                .unwrap_or(0)
        )
    } else {
        "数据库已同步，切换成功".to_string()
    };

    log::info!("数据库切换完成: {}", message);

    Ok(crate::models::DatabaseSwitchResponse {
        success: true,
        message,
        need_migration,
        migration_result,
        need_restart: true, // 需要重启服务才能生效
    })
}

/// 回滚数据库切换
/// 在迁移失败时恢复原来的数据库类型
#[tauri::command]
pub fn rollback_database_switch(original_db_type: String) -> Result<(), String> {
    log::info!("回滚数据库切换到: {}", original_db_type);
    switch_database_type(original_db_type)
}

/// 获取当前数据库连接信息
#[tauri::command]
pub fn get_current_database_info() -> Result<serde_json::Value, String> {
    let db_type = get_database_type()?;
    let url = crate::secure_config::get_database_url(&db_type)?;

    Ok(serde_json::json!({
        "db_type": db_type,
        "url": url
    }))
}

/// 测试数据库连接
#[tauri::command]
pub async fn test_database_connection(url: String) -> Result<serde_json::Value, String> {
    // 根据 URL 类型选择测试方式
    if url.starts_with("sqlite") {
        // SQLite: 检查文件是否存在或能否创建
        let file_path = url.replace("sqlite:///", "");
        let exists = std::path::Path::new(&file_path).exists();

        Ok(serde_json::json!({
            "success": true,
            "message": if exists { "数据库文件存在" } else { "将创建新数据库文件" }
        }))
    } else if url.contains("postgresql") || url.contains("mysql") {
        // PostgreSQL/MySQL: 测试 TCP 连接
        // 解析 host 和 port
        let host_port = url
            .split("@")
            .nth(1)
            .and_then(|s| s.split("/").next())
            .unwrap_or("localhost:5432");

        let parts: Vec<&str> = host_port.split(':').collect();
        let host = parts[0];
        let port = parts.get(1).and_then(|p| p.parse().ok()).unwrap_or(5432u16);

        // 使用 TCP 连接测试
        use tokio::net::TcpStream;
        use tokio::time::{timeout, Duration};

        let addr = format!("{}:{}", host, port);
        let result = timeout(Duration::from_secs(5), TcpStream::connect(&addr)).await;

        match result {
            Ok(Ok(_)) => Ok(serde_json::json!({
                "success": true,
                "message": "数据库连接成功"
            })),
            Ok(Err(e)) => Ok(serde_json::json!({
                "success": false,
                "message": format!("连接失败: {}", e)
            })),
            Err(_) => Ok(serde_json::json!({
                "success": false,
                "message": "连接超时"
            })),
        }
    } else {
        Ok(serde_json::json!({
            "success": false,
            "message": "不支持的数据库类型"
        }))
    }
}

// ==================== WebSocket 日志命令 ====================

use crate::log_websocket::{ConnectionState, LogWebSocketManager, SubscribeOptions};
use std::sync::Arc;
use tauri::State;

/// WebSocket 日志状态
pub struct LogWsState {
    pub manager: Arc<tokio::sync::Mutex<Option<LogWebSocketManager>>>,
}

impl Default for LogWsState {
    fn default() -> Self {
        Self {
            manager: Arc::new(tokio::sync::Mutex::new(None)),
        }
    }
}

/// 初始化 WebSocket 日志管理器
#[tauri::command]
pub async fn init_log_websocket(
    app_handle: tauri::AppHandle,
    state: State<'_, LogWsState>,
) -> Result<(), String> {
    let mut manager_lock = state.manager.lock().await;
    if manager_lock.is_none() {
        let manager = LogWebSocketManager::new(app_handle);
        *manager_lock = Some(manager);
        log::info!("WebSocket 日志管理器已初始化");
    }
    Ok(())
}

/// 连接到 WebSocket 日志服务
#[tauri::command]
pub async fn connect_log_websocket(
    url: String,
    token: Option<String>,
    state: State<'_, LogWsState>,
) -> Result<(), String> {
    let manager_lock = state.manager.lock().await;
    if let Some(ref manager) = *manager_lock {
        manager.connect(url, token)
    } else {
        Err("WebSocket 日志管理器未初始化".to_string())
    }
}

/// 断开 WebSocket 日志连接
#[tauri::command]
pub async fn disconnect_log_websocket(state: State<'_, LogWsState>) -> Result<(), String> {
    let manager_lock = state.manager.lock().await;
    if let Some(ref manager) = *manager_lock {
        manager.disconnect()
    } else {
        Err("WebSocket 日志管理器未初始化".to_string())
    }
}

/// 获取 WebSocket 日志连接状态
#[tauri::command]
pub async fn get_log_websocket_state(
    state: State<'_, LogWsState>,
) -> Result<ConnectionState, String> {
    let manager_lock = state.manager.lock().await;
    if let Some(ref manager) = *manager_lock {
        Ok(manager.get_state().await)
    } else {
        Ok(ConnectionState::Disconnected)
    }
}

/// 订阅日志
#[tauri::command]
pub async fn subscribe_logs(
    options: SubscribeOptions,
    state: State<'_, LogWsState>,
) -> Result<(), String> {
    let manager_lock = state.manager.lock().await;
    if let Some(ref manager) = *manager_lock {
        manager.subscribe(options)
    } else {
        Err("WebSocket 日志管理器未初始化".to_string())
    }
}

/// 取消订阅日志
#[tauri::command]
pub async fn unsubscribe_logs(state: State<'_, LogWsState>) -> Result<(), String> {
    let manager_lock = state.manager.lock().await;
    if let Some(ref manager) = *manager_lock {
        manager.unsubscribe()
    } else {
        Err("WebSocket 日志管理器未初始化".to_string())
    }
}
