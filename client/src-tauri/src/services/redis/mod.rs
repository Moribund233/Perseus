/**
 * Redis管理模块
 *
 * 管理Redis的生命周期、配置和服务管理
 * 支持Windows和Linux平台
 *
 * Windows平台特性：
 * - 支持手动载入Redis目录
 * - 支持安装为Windows服务
 * - 自动管理PATH环境变量
 *
 * Linux平台特性：
 * - 通过systemctl管理服务
 * - 自动检测包管理器安装的Redis
 */
// 子模块
mod config_manager;
mod lifecycle;
mod response;
mod windows_service;

// 重新导出公共接口
pub use config_manager::{get_redis_status, load_redis, set_runtime_config, update_redis_config};
pub use lifecycle::{check_redis_status, restart_redis, start_redis, stop_redis};
pub use windows_service::{
    add_to_path, install_redis_service, is_redis_service_installed, is_redis_service_running,
    remove_from_path, uninstall_redis_service,
};
