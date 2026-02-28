mod config_gen;
mod config_paths;
mod download;
mod lifecycle;
mod loader;
/**
 * Nginx管理模块
 *
 * 管理Nginx的生命周期、配置和下载
 * 支持Windows和Linux平台
 */
// 子模块
mod platform;
mod process;
mod proxy_config;
mod response;

// 重新导出公共接口
pub use config_gen::generate_nginx_config;
pub use config_paths::{
    get_nginx_config_dir, get_nginx_config_path, get_nginx_work_dir, infer_config_dir,
};
pub use download::{download_and_extract_nginx, get_nginx_download_url, update_nginx_download_url};
pub use lifecycle::{ensure_nginx_config_files, restart_nginx, start_nginx, stop_nginx};
pub use loader::{get_nginx_status, load_nginx, validate_nginx, NginxManagerState};
pub use platform::{get_nginx_platform_info, is_linux, is_windows};
pub use process::find_nginx_process;
pub use proxy_config::{get_nginx_proxy_config, save_nginx_proxy_config};
