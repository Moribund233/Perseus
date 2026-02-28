/**
 * Nginx载入模块
 *
 * 管理Nginx的验证、载入和状态管理
 */
use std::path::Path;
use std::process::{Command, Stdio};
use std::sync::Mutex;

use crate::core::config;
use crate::models::{NginxActionResponse, NginxConfig, NginxStatusResponse};

use super::config_paths::{get_nginx_config_dir, infer_config_dir};
use super::platform::get_nginx_platform_info;
use super::platform::is_linux;
use super::process::find_nginx_process;
use super::response::{error_response, success_response_with_status};

/// Nginx管理器状态
pub struct NginxManagerState {
    pub config: Mutex<NginxConfig>,
}

impl Default for NginxManagerState {
    fn default() -> Self {
        let config = config::load_config().map(|c| c.nginx).unwrap_or_default();
        Self {
            config: Mutex::new(config),
        }
    }
}

/**
 * 验证Nginx可执行文件是否有效
 *
 * @param exe_path Nginx可执行文件路径
 * @return 验证结果，成功返回版本信息
 */
pub fn validate_nginx(exe_path: &str) -> Result<String, String> {
    let path = Path::new(exe_path);

    if !path.exists() {
        return Err(format!("Nginx可执行文件不存在: {}", exe_path));
    }

    if !path.is_file() {
        return Err(format!("路径不是文件: {}", exe_path));
    }

    let output = Command::new(exe_path)
        .arg("-v")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|e| format!("执行Nginx验证失败: {}", e))?;

    let version_output = String::from_utf8_lossy(&output.stderr);
    let stdout_output = String::from_utf8_lossy(&output.stdout);

    let version_info = if version_output.contains("nginx") {
        version_output.to_string()
    } else if stdout_output.contains("nginx") {
        stdout_output.to_string()
    } else {
        return Err("无法获取Nginx版本信息，文件可能不是有效的Nginx可执行文件".to_string());
    };

    let version = version_info
        .lines()
        .next()
        .unwrap_or("nginx")
        .trim()
        .to_string();

    Ok(version)
}

/**
 * 载入Nginx
 *
 * @param exe_path Nginx可执行文件路径
 * @return 操作响应
 */
pub fn load_nginx(exe_path: String) -> NginxActionResponse {
    let version = match validate_nginx(&exe_path) {
        Ok(v) => v,
        Err(e) => return error_response(e),
    };

    let config_dir = infer_config_dir(&exe_path);
    let mut client_config = match config::load_config() {
        Ok(c) => c,
        Err(e) => return error_response(format!("加载配置失败: {}", e)),
    };

    client_config.nginx.exe_path = Some(exe_path.clone());
    client_config.nginx.config_dir = config_dir;
    client_config.nginx.is_loaded = true;
    client_config.nginx.version = Some(version.clone());

    if let Some(pid) = find_nginx_process(&exe_path) {
        client_config.nginx.status = "running".to_string();
        client_config.nginx.pid = Some(pid);
    } else {
        client_config.nginx.status = "stopped".to_string();
        client_config.nginx.pid = None;
    }

    if let Err(e) = config::save_config(&client_config) {
        return error_response(format!("保存配置失败: {}", e));
    }

    success_response_with_status(
        format!("Nginx载入成功: {}", version),
        client_config.nginx.status,
        client_config.nginx.pid,
    )
}

/**
 * 获取Nginx状态
 *
 * @return 状态响应
 */
pub fn get_nginx_status() -> NginxStatusResponse {
    if is_linux() {
        return get_linux_nginx_status();
    }

    match config::load_config() {
        Ok(client_config) => {
            let nginx = client_config.nginx;

            let (status, pid) = if nginx.is_loaded {
                if let Some(ref exe_path_ref) = nginx.exe_path {
                    if let Some(found_pid) = find_nginx_process(exe_path_ref) {
                        ("running".to_string(), Some(found_pid))
                    } else {
                        ("stopped".to_string(), None)
                    }
                } else {
                    (nginx.status, nginx.pid)
                }
            } else {
                (nginx.status, nginx.pid)
            };

            NginxStatusResponse {
                is_loaded: nginx.is_loaded,
                status,
                pid,
                version: nginx.version,
                exe_path: nginx.exe_path,
                config_dir: nginx.config_dir,
            }
        }
        Err(_) => NginxStatusResponse {
            is_loaded: false,
            status: "stopped".to_string(),
            pid: None,
            version: None,
            exe_path: None,
            config_dir: None,
        },
    }
}

/**
 * 获取Linux系统上的Nginx状态
 *
 * @return 状态响应
 */
fn get_linux_nginx_status() -> NginxStatusResponse {
    let platform_info = get_nginx_platform_info();

    let pid = find_nginx_process("");
    let is_running = pid.is_some();

    let config_dir = get_nginx_config_dir().or_else(|| {
        platform_info
            .config_path
            .as_ref()
            .and_then(|p| Path::new(p).parent())
            .map(|p| p.to_string_lossy().to_string())
    });

    NginxStatusResponse {
        is_loaded: is_running || platform_info.package_version.is_some(),
        status: if is_running {
            "running".to_string()
        } else {
            "stopped".to_string()
        },
        pid,
        version: platform_info.package_version,
        exe_path: Some("/usr/sbin/nginx".to_string()),
        config_dir,
    }
}
