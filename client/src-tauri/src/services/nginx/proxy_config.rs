/**
 * 代理配置管理模块
 *
 * 管理Nginx代理配置的保存和读取
 */
use std::fs;

use crate::core::config;
use crate::models::{NginxConfigSaveResponse, NginxProxyConfig};

use super::config_gen::generate_nginx_config;
use super::config_paths::{get_nginx_config_dir, get_nginx_config_path};
use super::lifecycle::ensure_nginx_config_files;
use super::process::find_nginx_process;

/**
 * 保存Nginx代理配置
 *
 * @param proxy_config 代理配置
 * @return 保存响应
 */
pub fn save_nginx_proxy_config(proxy_config: NginxProxyConfig) -> NginxConfigSaveResponse {
    let mut client_config = match config::load_config() {
        Ok(config) => config,
        Err(e) => {
            return NginxConfigSaveResponse {
                success: false,
                message: format!("加载配置失败: {}", e),
                need_restart: false,
            }
        }
    };

    let is_linux_platform = client_config.platform.platform_type.is_linux();

    let was_running = if is_linux_platform {
        find_nginx_process("").is_some()
    } else {
        client_config.nginx.status == "running"
    };

    client_config.nginx.proxy = proxy_config;

    match config::save_config(&client_config) {
        Ok(_) => {
            let config_dir = if is_linux_platform {
                get_nginx_config_dir()
            } else {
                client_config.nginx.config_dir.clone()
            };

            let conf_path = if is_linux_platform {
                get_nginx_config_path()
            } else {
                client_config
                    .nginx
                    .config_dir
                    .as_ref()
                    .map(|dir| std::path::Path::new(dir).join("nginx.conf"))
            };

            if let (Some(conf_path), Some(config_dir)) = (conf_path, config_dir) {
                if let Err(e) = ensure_nginx_config_files(&config_dir) {
                    return NginxConfigSaveResponse {
                        success: false,
                        message: format!("准备Nginx配置文件失败: {}", e),
                        need_restart: was_running,
                    };
                }

                let nginx_conf = generate_nginx_config(&client_config.nginx.proxy, &config_dir);

                match fs::write(&conf_path, nginx_conf) {
                    Ok(_) => {
                        log::info!("Nginx配置文件已保存到: {:?}", conf_path);
                        NginxConfigSaveResponse {
                            success: true,
                            message: "配置已保存".to_string(),
                            need_restart: was_running,
                        }
                    }
                    Err(e) => NginxConfigSaveResponse {
                        success: false,
                        message: format!("保存配置文件失败: {}", e),
                        need_restart: was_running,
                    },
                }
            } else {
                NginxConfigSaveResponse {
                    success: true,
                    message: "配置已保存（配置文件将在Nginx载入后生成）".to_string(),
                    need_restart: was_running,
                }
            }
        }
        Err(e) => NginxConfigSaveResponse {
            success: false,
            message: format!("保存配置失败: {}", e),
            need_restart: false,
        },
    }
}

/**
 * 获取Nginx代理配置
 *
 * @return 代理配置
 */
pub fn get_nginx_proxy_config() -> NginxProxyConfig {
    match config::load_config() {
        Ok(client_config) => client_config.nginx.proxy,
        Err(_) => NginxProxyConfig::default(),
    }
}
