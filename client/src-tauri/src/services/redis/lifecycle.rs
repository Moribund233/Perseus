/**
 * Redis生命周期管理模块
 *
 * 管理Redis的启动、停止和重启
 * Windows平台：通过Windows服务控制
 * Linux平台：通过systemctl命令控制
 */
use std::process::Command;

use crate::core::config;
use crate::models::RedisActionResponse;

use super::response::{error_response, success_response};

#[cfg(target_os = "windows")]
use super::windows_service::{is_redis_service_installed, start_redis_service, stop_redis_service};

/// Windows服务名称
const REDIS_SERVICE_NAME: &str = "Redis";

/**
 * 启动Redis
 *
 * @return 操作响应
 */
pub fn start_redis() -> RedisActionResponse {
    let client_config = match config::load_config() {
        Ok(c) => c,
        Err(e) => return error_response(format!("加载配置失败: {}", e)),
    };

    // Linux平台
    if client_config.platform.platform_type.is_linux() {
        return start_linux_redis();
    }

    // Windows平台
    let redis_config = client_config.redis;

    if !redis_config.is_loaded {
        return error_response("Redis未载入，请先载入Redis目录".to_string());
    }

    // 检查是否已作为Windows服务安装
    #[cfg(target_os = "windows")]
    {
        if redis_config.is_windows_service {
            return start_redis_service_wrapper();
        }
    }

    // 未安装为服务，使用直接启动方式
    #[cfg(target_os = "windows")]
    {
        start_redis_direct()
    }
    #[cfg(not(target_os = "windows"))]
    {
        error_response("非Windows平台不支持直接启动".to_string())
    }
}

/**
 * 停止Redis
 *
 * @return 操作响应
 */
pub fn stop_redis() -> RedisActionResponse {
    let client_config = match config::load_config() {
        Ok(c) => c,
        Err(e) => return error_response(format!("加载配置失败: {}", e)),
    };

    // Linux平台
    if client_config.platform.platform_type.is_linux() {
        return stop_linux_redis();
    }

    // Windows平台
    let redis_config = client_config.redis;

    if !redis_config.is_loaded {
        return error_response("Redis未载入".to_string());
    }

    // 检查是否已作为Windows服务安装
    #[cfg(target_os = "windows")]
    {
        if redis_config.is_windows_service {
            return stop_redis_service_wrapper();
        }
    }

    // 未安装为服务，使用直接停止方式
    #[cfg(target_os = "windows")]
    {
        stop_redis_direct()
    }
    #[cfg(not(target_os = "windows"))]
    {
        error_response("非Windows平台不支持直接停止".to_string())
    }
}

/**
 * 重启Redis
 *
 * @return 操作响应
 */
pub fn restart_redis() -> RedisActionResponse {
    let client_config = match config::load_config() {
        Ok(c) => c,
        Err(e) => return error_response(format!("加载配置失败: {}", e)),
    };

    // Linux平台
    if client_config.platform.platform_type.is_linux() {
        return restart_linux_redis();
    }

    // Windows平台：先停止再启动
    let stop_result = stop_redis();
    if !stop_result.success {
        return stop_result;
    }

    // 等待一小段时间确保进程完全停止
    std::thread::sleep(std::time::Duration::from_millis(500));

    start_redis()
}

/**
 * Linux平台启动Redis
 *
 * @return 操作响应
 */
fn start_linux_redis() -> RedisActionResponse {
    match Command::new("systemctl").args(["start", "redis"]).output() {
        Ok(output) => {
            if output.status.success() {
                update_redis_status("running");
                success_response("Redis已启动".to_string())
            } else {
                let stderr = String::from_utf8_lossy(&output.stderr);
                error_response(format!("启动Redis失败: {}", stderr))
            }
        }
        Err(e) => error_response(format!("执行启动命令失败: {}", e)),
    }
}

/**
 * Linux平台停止Redis
 *
 * @return 操作响应
 */
fn stop_linux_redis() -> RedisActionResponse {
    match Command::new("systemctl").args(["stop", "redis"]).output() {
        Ok(output) => {
            if output.status.success() {
                update_redis_status("stopped");
                success_response("Redis已停止".to_string())
            } else {
                let stderr = String::from_utf8_lossy(&output.stderr);
                error_response(format!("停止Redis失败: {}", stderr))
            }
        }
        Err(e) => error_response(format!("执行停止命令失败: {}", e)),
    }
}

/**
 * Linux平台重启Redis
 *
 * @return 操作响应
 */
fn restart_linux_redis() -> RedisActionResponse {
    match Command::new("systemctl")
        .args(["restart", "redis"])
        .output()
    {
        Ok(output) => {
            if output.status.success() {
                update_redis_status("running");
                success_response("Redis已重启".to_string())
            } else {
                let stderr = String::from_utf8_lossy(&output.stderr);
                error_response(format!("重启Redis失败: {}", stderr))
            }
        }
        Err(e) => error_response(format!("执行重启命令失败: {}", e)),
    }
}

/**
 * Windows平台直接启动Redis（非服务方式）
 *
 * @return 操作响应
 */
#[cfg(target_os = "windows")]
fn start_redis_direct() -> RedisActionResponse {
    use std::os::windows::process::CommandExt;

    let config = match config::load_config() {
        Ok(c) => c.redis,
        Err(e) => return error_response(format!("加载配置失败: {}", e)),
    };

    let exe_dir = match &config.exe_dir {
        Some(d) => d.clone(),
        None => return error_response("Redis目录未设置".to_string()),
    };

    let redis_server_path = std::path::Path::new(&exe_dir).join("redis-server.exe");

    if !redis_server_path.exists() {
        return error_response(format!(
            "redis-server.exe不存在: {}",
            redis_server_path.display()
        ));
    }

    // 构建配置文件路径
    let config_path = match &config.config_path {
        Some(p) => p.clone(),
        None => {
            // 使用默认配置文件
            let default_config = std::path::Path::new(&exe_dir).join("redis.conf");
            if default_config.exists() {
                default_config.to_string_lossy().to_string()
            } else {
                return error_response("未找到Redis配置文件".to_string());
            }
        }
    };

    // 启动Redis进程
    match Command::new(&redis_server_path)
        .arg(&config_path)
        .creation_flags(0x00000008) // DETACHED_PROCESS
        .spawn()
    {
        Ok(_) => {
            update_redis_status("running");
            success_response("Redis已启动".to_string())
        }
        Err(e) => error_response(format!("启动Redis失败: {}", e)),
    }
}

#[cfg(not(target_os = "windows"))]
fn start_redis_direct() -> RedisActionResponse {
    error_response("非Windows平台不支持".to_string())
}

/**
 * Windows平台直接停止Redis（非服务方式）
 *
 * @return 操作响应
 */
#[cfg(target_os = "windows")]
fn stop_redis_direct() -> RedisActionResponse {
    let config = match config::load_config() {
        Ok(c) => c.redis,
        Err(e) => return error_response(format!("加载配置失败: {}", e)),
    };

    let exe_dir = match &config.exe_dir {
        Some(d) => d.clone(),
        None => return error_response("Redis目录未设置".to_string()),
    };

    let redis_cli_path = std::path::Path::new(&exe_dir).join("redis-cli.exe");

    if !redis_cli_path.exists() {
        return error_response(format!("redis-cli.exe不存在: {}", redis_cli_path.display()));
    }

    // 使用redis-cli发送SHUTDOWN命令
    let port = config.port;
    let mut cmd = Command::new(&redis_cli_path);
    cmd.arg("-p").arg(port.to_string()).arg("SHUTDOWN");

    // 如果有密码，添加认证
    if config.require_pass {
        if let Some(password) = &config.password {
            cmd.arg("-a").arg(password);
        }
    }

    match cmd.output() {
        Ok(_) => {
            update_redis_status("stopped");
            success_response("Redis已停止".to_string())
        }
        Err(e) => error_response(format!("停止Redis失败: {}", e)),
    }
}

#[cfg(not(target_os = "windows"))]
fn stop_redis_direct() -> RedisActionResponse {
    error_response("非Windows平台不支持".to_string())
}

/**
 * Windows服务方式启动Redis
 *
 * @return 操作响应
 */
#[cfg(target_os = "windows")]
fn start_redis_service_wrapper() -> RedisActionResponse {
    if !is_redis_service_installed() {
        return error_response("Redis服务未安装".to_string());
    }

    match start_redis_service(REDIS_SERVICE_NAME) {
        Ok(_) => {
            update_redis_status("running");
            success_response("Redis服务已启动".to_string())
        }
        Err(e) => error_response(format!("启动Redis服务失败: {}", e)),
    }
}

#[cfg(not(target_os = "windows"))]
fn start_redis_service_wrapper() -> RedisActionResponse {
    error_response("非Windows平台不支持".to_string())
}

/**
 * Windows服务方式停止Redis
 *
 * @return 操作响应
 */
#[cfg(target_os = "windows")]
fn stop_redis_service_wrapper() -> RedisActionResponse {
    if !is_redis_service_installed() {
        return error_response("Redis服务未安装".to_string());
    }

    match stop_redis_service(REDIS_SERVICE_NAME) {
        Ok(_) => {
            update_redis_status("stopped");
            success_response("Redis服务已停止".to_string())
        }
        Err(e) => error_response(format!("停止Redis服务失败: {}", e)),
    }
}

#[cfg(not(target_os = "windows"))]
fn stop_redis_service_wrapper() -> RedisActionResponse {
    error_response("非Windows平台不支持".to_string())
}

/**
 * 更新Redis状态到配置
 *
 * @param status 状态字符串
 */
fn update_redis_status(status: &str) {
    if let Ok(mut client_config) = config::load_config() {
        client_config.redis.status = status.to_string();
        let _ = config::save_config(&client_config);
    }
}

/**
 * 检查Redis运行状态
 *
 * @return 状态字符串
 */
pub fn check_redis_status() -> String {
    let client_config = match config::load_config() {
        Ok(c) => c,
        Err(_) => return "unknown".to_string(),
    };

    // Linux平台
    if client_config.platform.platform_type.is_linux() {
        return check_linux_redis_status();
    }

    // Windows平台
    let redis_config = client_config.redis;

    if !redis_config.is_loaded {
        return "stopped".to_string();
    }

    // 检查服务状态
    #[cfg(target_os = "windows")]
    {
        if redis_config.is_windows_service {
            match super::windows_service::is_redis_service_running() {
                Ok(true) => "running".to_string(),
                Ok(false) => "stopped".to_string(),
                Err(_) => "error".to_string(),
            }
        } else {
            // 直接检查进程
            match check_redis_process() {
                true => "running".to_string(),
                false => "stopped".to_string(),
            }
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        "unknown".to_string()
    }
}

/**
 * 检查Linux平台Redis状态
 *
 * @return 状态字符串
 */
fn check_linux_redis_status() -> String {
    match Command::new("systemctl")
        .args(["is-active", "redis"])
        .output()
    {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout);
            if stdout.trim() == "active" {
                "running".to_string()
            } else {
                "stopped".to_string()
            }
        }
        Err(_) => "unknown".to_string(),
    }
}

/**
 * 检查Redis进程是否在运行（Windows直接启动方式）
 *
 * @return 是否运行中
 */
#[cfg(target_os = "windows")]
fn check_redis_process() -> bool {
    use std::process::Command;

    let output = match Command::new("tasklist")
        .args(["/FI", "IMAGENAME eq redis-server.exe", "/NH"])
        .output()
    {
        Ok(o) => o,
        Err(_) => return false,
    };

    let stdout = String::from_utf8_lossy(&output.stdout);
    stdout.contains("redis-server.exe")
}

#[cfg(not(target_os = "windows"))]
fn check_redis_process() -> bool {
    false
}
