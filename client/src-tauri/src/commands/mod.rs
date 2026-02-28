/**
 * Tauri 命令模块
 *
 * 定义前端可调用的 Rust 命令
 * 按功能划分为多个子模块
 */
use std::sync::Mutex;

// 子模块
pub mod config_commands;
pub mod database_commands;
pub mod debug_commands;
pub mod guide_commands;
pub mod local_auth_commands;
pub mod log_commands;
pub mod nginx_commands;
pub mod security_commands;
pub mod service_commands;
pub mod system_commands;
pub mod websocket_commands;

/// 应用状态
pub struct AppState {
    pub server_pid: Mutex<Option<u32>>,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            server_pid: Mutex::new(None),
        }
    }
}

// 重新导出所有命令函数，保持向后兼容
pub use config_commands::*;
pub use database_commands::*;
pub use debug_commands::*;
pub use guide_commands::*;
pub use local_auth_commands::*;
pub use log_commands::*;
pub use nginx_commands::*;
pub use security_commands::*;
pub use service_commands::*;
pub use system_commands::*;
pub use websocket_commands::{LogWsState, *};
