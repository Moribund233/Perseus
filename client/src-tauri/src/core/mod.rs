/**
 * 核心模块
 *
 * 包含应用程序的核心功能模块
 */
// 配置子模块
pub mod config;

// 核心功能模块
pub mod api_client;
pub mod local_auth;
pub mod log_websocket;
pub mod process_manager;

// 重新导出常用类型
pub use api_client::ApiClient;
pub use log_websocket::LogWebSocketManager;
pub use process_manager::{
    find_server_process, get_server_exe_path, get_server_info, is_server_running, start_server,
    stop_server, ProcessInfo, SystemResources,
};
