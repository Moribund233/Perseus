/**
 * 生命周期管理模块
 *
 * 管理Nginx的启动、停止和重启
 */
use std::fs;
use std::path::Path;
use std::process::{Command, Stdio};

use crate::core::config;
use crate::models::NginxActionResponse;

use super::config_paths::{get_nginx_config_dir, get_nginx_config_path, get_nginx_work_dir};
use super::platform::is_linux;
use super::process::find_nginx_process;
use super::response::{error_response, error_response_with_status, success_response_with_status};

/**
 * 确保Nginx配置目录包含必要的文件
 *
 * @param config_dir 配置目录路径
 * @return 操作结果
 */
pub fn ensure_nginx_config_files(config_dir: &str) -> Result<(), String> {
    let config_path = Path::new(config_dir);

    // 确保logs目录存在
    let logs_dir = config_path.join("logs");
    if !logs_dir.exists() {
        fs::create_dir_all(&logs_dir).map_err(|e| format!("创建logs目录失败: {}", e))?;
    }

    // 检查mime.types文件是否存在
    let mime_types_path = config_path.join("mime.types");
    if !mime_types_path.exists() {
        let system_mime_paths = [
            "/etc/nginx/mime.types",
            "/usr/local/nginx/conf/mime.types",
            "/usr/share/nginx/mime.types",
        ];
        for system_path in &system_mime_paths {
            if Path::new(system_path).exists() {
                match fs::copy(system_path, &mime_types_path) {
                    Ok(_) => {
                        log::info!("已从 {} 复制mime.types", system_path);
                        break;
                    }
                    Err(e) => {
                        log::warn!("从 {} 复制mime.types失败: {}", system_path, e);
                    }
                }
            }
        }
    }

    Ok(())
}

/// 更新Nginx状态到配置
fn update_nginx_status(status: &str, pid: Option<u32>) {
    if let Ok(mut client_config) = config::load_config() {
        client_config.nginx.status = status.to_string();
        client_config.nginx.pid = pid;
        let _ = config::save_config(&client_config);
    }
}

/**
 * 启动Nginx
 *
 * @return 操作响应
 */
pub fn start_nginx() -> NginxActionResponse {
    if is_linux() {
        return start_linux_nginx();
    }

    let config = match config::load_config() {
        Ok(c) => c.nginx,
        Err(e) => return error_response(format!("加载配置失败: {}", e)),
    };

    if !config.is_loaded {
        return error_response_with_status("Nginx未载入，请先载入Nginx", "stopped", None);
    }

    let exe_path = match &config.exe_path {
        Some(p) => p.clone(),
        None => return error_response_with_status("Nginx可执行文件路径未设置", "stopped", None),
    };

    if let Some(pid) = find_nginx_process(&exe_path) {
        return success_response_with_status(
            format!("Nginx已经在运行中 (PID: {})", pid),
            "running",
            Some(pid),
        );
    }

    let mut cmd = Command::new(&exe_path);

    if let Some(work_dir) = get_nginx_work_dir(&exe_path) {
        cmd.current_dir(work_dir);
    }

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NEW_PROCESS_GROUP: u32 = 0x00000200;
        const DETACHED_PROCESS: u32 = 0x00000008;
        cmd.creation_flags(CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS);
    }

    match cmd.stdout(Stdio::null()).stderr(Stdio::null()).spawn() {
        Ok(_) => {
            std::thread::sleep(std::time::Duration::from_millis(800));

            match find_nginx_process(&exe_path) {
                Some(pid) => {
                    update_nginx_status("running", Some(pid));
                    success_response_with_status(
                        format!("Nginx启动成功 (PID: {})", pid),
                        "running",
                        Some(pid),
                    )
                }
                None => error_response_with_status("Nginx进程启动后未检测到运行", "error", None),
            }
        }
        Err(e) => error_response_with_status(format!("启动Nginx失败: {}", e), "error", None),
    }
}

/**
 * 启动Linux系统上的Nginx
 *
 * @return 操作响应
 */
fn start_linux_nginx() -> NginxActionResponse {
    if let Some(pid) = find_nginx_process("") {
        return success_response_with_status(
            format!("Nginx已经在运行中 (PID: {})", pid),
            "running",
            Some(pid),
        );
    }

    let conf_path = get_nginx_config_path();
    let config_dir = get_nginx_config_dir();

    if let Some(ref config_dir) = config_dir {
        if let Err(e) = ensure_nginx_config_files(config_dir) {
            return error_response_with_status(
                format!("准备Nginx配置文件失败: {}", e),
                "error",
                None,
            );
        }
    }

    let mut cmd = Command::new("nginx");
    cmd.stdout(Stdio::null()).stderr(Stdio::null());

    if let Some(ref conf_path) = conf_path {
        if conf_path.exists() {
            cmd.arg("-c").arg(conf_path);
        }
    }

    if let Some(ref config_dir) = config_dir {
        cmd.current_dir(config_dir);
    }

    match cmd.spawn() {
        Ok(_) => {
            std::thread::sleep(std::time::Duration::from_millis(800));
            match find_nginx_process("") {
                Some(pid) => success_response_with_status(
                    format!("Nginx启动成功 (PID: {})", pid),
                    "running",
                    Some(pid),
                ),
                None => error_response_with_status("Nginx进程启动后未检测到运行", "error", None),
            }
        }
        Err(e) => error_response_with_status(format!("启动Nginx失败: {}", e), "error", None),
    }
}

/**
 * 停止Nginx
 *
 * @return 操作响应
 */
pub fn stop_nginx() -> NginxActionResponse {
    if is_linux() {
        return stop_linux_nginx();
    }

    let config = match config::load_config() {
        Ok(c) => c.nginx,
        Err(e) => return error_response(format!("加载配置失败: {}", e)),
    };

    let exe_path = match &config.exe_path {
        Some(p) => p.clone(),
        None => return error_response_with_status("Nginx可执行文件路径未设置", "stopped", None),
    };

    if find_nginx_process(&exe_path).is_none() {
        update_nginx_status("stopped", None);
        return success_response_with_status("Nginx未在运行", "stopped", None);
    }

    let mut quit_cmd = Command::new(&exe_path);
    quit_cmd.arg("-s").arg("quit");

    if let Some(work_dir) = get_nginx_work_dir(&exe_path) {
        quit_cmd.current_dir(work_dir);
    }

    match quit_cmd.output() {
        Ok(_) => {
            for _ in 0..10 {
                std::thread::sleep(std::time::Duration::from_millis(500));
                if find_nginx_process(&exe_path).is_none() {
                    update_nginx_status("stopped", None);
                    return success_response_with_status("Nginx已停止", "stopped", None);
                }
            }
            NginxActionResponse {
                success: false,
                message: "Nginx停止命令已发送，但进程仍在运行".to_string(),
                status: Some("running".to_string()),
                pid: find_nginx_process(&exe_path),
            }
        }
        Err(e) => {
            log::error!("执行Nginx停止命令失败: {}", e);
            error_response_with_status(
                format!("停止Nginx失败: {}", e),
                "running",
                find_nginx_process(&exe_path),
            )
        }
    }
}

/**
 * 停止Linux系统上的Nginx
 *
 * @return 操作响应
 */
fn stop_linux_nginx() -> NginxActionResponse {
    if find_nginx_process("").is_none() {
        return success_response_with_status("Nginx未在运行", "stopped", None);
    }

    let conf_path = get_nginx_config_path();
    let config_dir = get_nginx_config_dir();

    let mut quit_cmd = Command::new("nginx");
    quit_cmd.arg("-s").arg("quit");

    if let Some(ref conf_path) = conf_path {
        quit_cmd.arg("-c").arg(conf_path);
    }

    if let Some(ref config_dir) = config_dir {
        quit_cmd.current_dir(config_dir);
    }

    match quit_cmd.output() {
        Ok(_) => {
            for _ in 0..10 {
                std::thread::sleep(std::time::Duration::from_millis(500));
                if find_nginx_process("").is_none() {
                    return success_response_with_status("Nginx已停止", "stopped", None);
                }
            }

            log::info!("Nginx -s quit 未能停止进程，尝试使用 -s stop");
            let mut stop_cmd = Command::new("nginx");
            stop_cmd.arg("-s").arg("stop");

            if let Some(ref conf_path) = conf_path {
                stop_cmd.arg("-c").arg(conf_path);
            }

            if let Some(ref config_dir) = config_dir {
                stop_cmd.current_dir(config_dir);
            }

            if let Err(e) = stop_cmd.output() {
                log::error!("执行Nginx stop命令失败: {}", e);
            } else {
                for _ in 0..5 {
                    std::thread::sleep(std::time::Duration::from_millis(500));
                    if find_nginx_process("").is_none() {
                        return success_response_with_status("Nginx已停止", "stopped", None);
                    }
                }
            }

            NginxActionResponse {
                success: false,
                message: "Nginx停止命令已发送，但进程仍在运行".to_string(),
                status: Some("running".to_string()),
                pid: find_nginx_process(""),
            }
        }
        Err(e) => {
            log::error!("执行Nginx停止命令失败: {}", e);
            error_response_with_status(
                format!("停止Nginx失败: {}", e),
                "running",
                find_nginx_process(""),
            )
        }
    }
}

/**
 * 重启Nginx
 *
 * @return 操作响应
 */
pub fn restart_nginx() -> NginxActionResponse {
    let _ = stop_nginx();
    std::thread::sleep(std::time::Duration::from_secs(1));
    let start_result = start_nginx();

    NginxActionResponse {
        success: start_result.success,
        message: format!(
            "Nginx重启{}: {}",
            if start_result.success {
                "成功"
            } else {
                "失败"
            },
            start_result.message
        ),
        status: start_result.status,
        pid: start_result.pid,
    }
}
