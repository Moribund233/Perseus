/**
 * 配置路径管理模块
 *
 * 管理Nginx配置文件和目录的路径
 */
use std::path::{Path, PathBuf};

use crate::core::config;

/**
 * 获取Nginx配置文件保存路径
 *
 * @return 配置文件路径
 */
pub fn get_nginx_config_path() -> Option<PathBuf> {
    // 优先从配置中检测平台
    match config::load_config() {
        Ok(client_config) => {
            if client_config.platform.platform_type.is_linux() {
                // Linux平台：在用户目录下创建配置文件
                dirs::config_dir()
                    .map(|dir| dir.join("langit-client").join("nginx").join("nginx.conf"))
            } else {
                // Windows平台：使用配置目录
                client_config
                    .nginx
                    .config_dir
                    .map(|dir| Path::new(&dir).join("nginx.conf"))
            }
        }
        Err(_) => {
            // 默认使用配置目录
            dirs::config_dir().map(|dir| dir.join("langit-client").join("nginx").join("nginx.conf"))
        }
    }
}

/**
 * 获取Nginx配置目录
 *
 * @return 配置目录路径
 */
pub fn get_nginx_config_dir() -> Option<String> {
    get_nginx_config_path().and_then(|p| {
        p.parent()
            .map(|parent| parent.to_string_lossy().to_string())
    })
}

/**
 * 从路径推断Nginx配置目录
 *
 * @param exe_path Nginx可执行文件路径
 * @return 配置目录路径
 */
pub fn infer_config_dir(exe_path: &str) -> Option<String> {
    let path = Path::new(exe_path);

    if let Some(parent) = path.parent() {
        // 尝试 ../conf
        let conf_dir = parent.join("conf");
        if conf_dir.exists() && conf_dir.is_dir() {
            return Some(conf_dir.to_string_lossy().to_string());
        }

        // 尝试 ../../conf
        if let Some(grandparent) = parent.parent() {
            let conf_dir = grandparent.join("conf");
            if conf_dir.exists() && conf_dir.is_dir() {
                return Some(conf_dir.to_string_lossy().to_string());
            }
        }
    }

    None
}

/// 获取Nginx工作目录
pub fn get_nginx_work_dir(exe_path: &str) -> Option<PathBuf> {
    Path::new(exe_path).parent().map(|parent| {
        if parent
            .file_name()
            .map(|n| n == "sbin" || n == "bin")
            .unwrap_or(false)
        {
            parent.parent().unwrap_or(parent).to_path_buf()
        } else {
            parent.to_path_buf()
        }
    })
}
