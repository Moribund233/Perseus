/**
 * 平台检测和抽象模块
 *
 * 提供Windows和Linux平台的检测和抽象
 */
use std::path::Path;

use crate::models::NginxPlatformInfo;

/// 检查是否为Windows平台
pub fn is_windows() -> bool {
    cfg!(target_os = "windows")
}

/// 检查是否为Linux平台
pub fn is_linux() -> bool {
    cfg!(target_os = "linux")
}

/**
 * 获取Nginx平台信息
 *
 * @return 平台信息
 */
pub fn get_nginx_platform_info() -> NginxPlatformInfo {
    let platform = std::env::consts::OS.to_string();

    match platform.as_str() {
        "windows" => NginxPlatformInfo {
            platform,
            supports_manual_load: true,
            supports_download: true,
            uses_package_manager: false,
            package_manager: None,
            package_version: None,
            config_path: None,
        },
        "linux" => {
            let (package_manager, package_version, config_path) = detect_linux_nginx();
            NginxPlatformInfo {
                platform,
                supports_manual_load: false,
                supports_download: false,
                uses_package_manager: true,
                package_manager,
                package_version,
                config_path,
            }
        }
        _ => NginxPlatformInfo {
            platform,
            supports_manual_load: false,
            supports_download: false,
            uses_package_manager: false,
            package_manager: None,
            package_version: None,
            config_path: None,
        },
    }
}

/**
 * 检测Linux系统上的Nginx信息
 *
 * @return (包管理器, 版本, 配置文件路径)
 */
fn detect_linux_nginx() -> (Option<String>, Option<String>, Option<String>) {
    let package_manager = detect_package_manager();
    let version = get_linux_nginx_version();
    let config_path = detect_nginx_config_path();

    (package_manager, version, config_path)
}

/**
 * 检测Linux包管理器
 *
 * @return 包管理器名称
 */
fn detect_package_manager() -> Option<String> {
    let managers = vec![
        ("/usr/bin/apt", "apt"),
        ("/usr/bin/apt-get", "apt"),
        ("/usr/bin/yum", "yum"),
        ("/usr/bin/dnf", "dnf"),
        ("/usr/bin/pacman", "pacman"),
        ("/sbin/apk", "apk"),
    ];

    for (path, name) in managers {
        if Path::new(path).exists() {
            return Some(name.to_string());
        }
    }

    None
}

/**
 * 获取Linux系统上Nginx的版本
 *
 * @return 版本信息
 */
fn get_linux_nginx_version() -> Option<String> {
    use std::process::Command;

    if let Ok(output) = Command::new("nginx").arg("-v").output() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);

        let version_info = if stderr.contains("nginx") {
            stderr.to_string()
        } else if stdout.contains("nginx") {
            stdout.to_string()
        } else {
            return None;
        };

        return version_info.lines().next().map(|s| s.trim().to_string());
    }

    None
}

/**
 * 检测Nginx配置文件路径
 *
 * @return 配置文件路径
 */
fn detect_nginx_config_path() -> Option<String> {
    let common_paths = vec![
        "/etc/nginx/nginx.conf",
        "/usr/local/nginx/conf/nginx.conf",
        "/opt/nginx/conf/nginx.conf",
    ];

    for path in common_paths {
        if Path::new(path).exists() {
            return Some(path.to_string());
        }
    }

    None
}
