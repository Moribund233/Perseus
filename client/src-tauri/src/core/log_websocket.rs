/**
 * WebSocket 日志管理器
 *
 * 在 Tauri 后端维护稳定的 WebSocket 连接，替代前端直接连接
 * 解决 Linux WebKitGTK WebSocket 不稳定问题
 *
 * 此模块是对 services::websocket 的薄封装，专注于日志功能
 */
use tauri::AppHandle;

// 从 websocket 服务模块重新导出类型
pub use crate::services::websocket::{
    ConnectionState, LogEntry, LogFilters, SubscribeOptions,
};

// 内部使用 WebSocketManager
use crate::services::websocket::WebSocketManager;

/// WebSocket 日志管理器
/// 封装通用的 WebSocketManager，提供日志特定的功能
pub struct LogWebSocketManager {
    inner: WebSocketManager,
}

impl LogWebSocketManager {
    /// 创建新的日志管理器
    pub fn new(app_handle: AppHandle) -> Self {
        Self {
            inner: WebSocketManager::new(app_handle),
        }
    }

    /// 获取当前状态
    pub async fn get_state(&self) -> ConnectionState {
        self.inner.get_state().await
    }

    /// 连接到 WebSocket 服务器
    pub fn connect(&self, url: String, token: Option<String>) -> Result<(), String> {
        self.inner.connect(url, token)
    }

    /// 断开连接
    pub fn disconnect(&self) -> Result<(), String> {
        self.inner.disconnect()
    }

    /// 订阅日志
    pub fn subscribe(&self, options: SubscribeOptions) -> Result<(), String> {
        self.inner.subscribe(options)
    }

    /// 取消订阅
    pub fn unsubscribe(&self) -> Result<(), String> {
        self.inner.unsubscribe()
    }

    /// 获取统计信息
    pub fn get_stats(&self) -> Result<(), String> {
        self.inner.get_stats()
    }
}
