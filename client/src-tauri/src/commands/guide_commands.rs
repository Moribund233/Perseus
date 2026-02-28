/**
 * 引导页面命令模块
 *
 * 提供应用引导流程相关的功能
 */
use crate::core::process_manager::get_server_exe_path;
use crate::models::{GitCheckResult, ServerCheckResult};
use std::path::Path;
use std::process::Command;

/**
 * 检查服务端路径是否已配置
 *
 * @return 服务端检查结果
 */
#[tauri::command]
pub fn check_server_path() -> Result<ServerCheckResult, String> {
    match get_server_exe_path() {
        Ok(path) => {
            let path_str = path.to_string_lossy().to_string();
            Ok(ServerCheckResult {
                found: true,
                path: Some(path_str),
                version: None,
                auto_detected: false,
            })
        }
        Err(_) => Ok(ServerCheckResult {
            found: false,
            path: None,
            version: None,
            auto_detected: false,
        }),
    }
}

/**
 * 验证并保存服务端路径
 *
 * @param path 服务端路径
 * @return 服务端检查结果
 */
#[tauri::command]
pub fn validate_and_save_server_path(path: String) -> Result<ServerCheckResult, String> {
    let path_obj = Path::new(&path);

    if !path_obj.exists() {
        return Ok(ServerCheckResult {
            found: false,
            path: None,
            version: None,
            auto_detected: false,
        });
    }

    let file_name = path_obj.file_name().and_then(|n| n.to_str()).unwrap_or("");
    if !file_name.contains("langit-server") {
        return Ok(ServerCheckResult {
            found: false,
            path: None,
            version: None,
            auto_detected: false,
        });
    }

    let mut client_config = crate::core::config::load_config()?;
    client_config.server.path.custom_path = Some(path.clone());
    crate::core::config::save_config(&client_config)?;

    Ok(ServerCheckResult {
        found: true,
        path: Some(path),
        version: None,
        auto_detected: false,
    })
}

/**
 * 检查Git安装
 *
 * @return Git检查结果
 */
#[tauri::command]
pub fn check_git_installation() -> Result<GitCheckResult, String> {
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

            Ok(GitCheckResult {
                installed: true,
                version: Some(version),
                path: None,
                http_backend_available: http_backend_check,
            })
        }
        _ => Ok(GitCheckResult {
            installed: false,
            version: None,
            path: None,
            http_backend_available: false,
        }),
    }
}

/**
 * 标记引导完成
 */
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

/**
 * 检查是否已完成引导
 *
 * @return 是否已完成
 */
#[tauri::command]
pub fn is_guide_completed() -> Result<bool, String> {
    let config_dir = dirs::config_dir()
        .ok_or("无法获取配置目录")?
        .join("langit-client");
    let guide_marker = config_dir.join(".guide_completed");

    Ok(guide_marker.exists())
}

/**
 * 检查是否存在用户配置文件
 * 用于判断是否需要显示引导页面
 *
 * @return 是否存在
 */
#[tauri::command]
pub fn has_user_config_file() -> Result<bool, String> {
    Ok(crate::core::config::has_user_config())
}

/**
 * 重置客户端配置
 * 删除配置文件和引导标记，使应用重新进入引导流程
 */
#[tauri::command]
pub fn reset_client_config() -> Result<(), String> {
    // 删除配置文件
    if let Some(config_path) = crate::core::config::get_config_path() {
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
