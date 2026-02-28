/**
 * WebSocket 服务模块
 *
 * 提供通用的 WebSocket 连接管理功能
 * 支持连接建立、消息处理、自动重连等
 */
// 子模块
mod connection;
mod handler;
mod manager;
mod types;

// 重新导出公共接口
pub use connection::{connect, try_reconnect, WebSocketStream};
pub use handler::{emit_error, emit_state_change, handle_message};
pub use manager::WebSocketManager;
pub use types::{
    ConnectionState, InternalCommand, LogEntry, LogFilters, SubscribeOptions, WsMessage,
};
