/**
 * WebSocket 日志命令模块
 *
 * 提供WebSocket日志连接的初始化、连接管理和订阅功能
 */
use crate::core::log_websocket::{ConnectionState, LogWebSocketManager, SubscribeOptions};
use std::sync::Arc;
use tauri::{AppHandle, State};

/**
 * WebSocket 日志状态
 */
pub struct LogWsState {
    pub manager: Arc<tokio::sync::Mutex<Option<LogWebSocketManager>>>,
}

impl Default for LogWsState {
    fn default() -> Self {
        Self {
            manager: Arc::new(tokio::sync::Mutex::new(None)),
        }
    }
}

/**
 * 初始化 WebSocket 日志管理器
 *
 * @param app_handle Tauri应用句柄
 * @param state WebSocket状态
 */
#[tauri::command]
pub async fn init_log_websocket(
    app_handle: AppHandle,
    state: State<'_, LogWsState>,
) -> Result<(), String> {
    let mut manager_lock = state.manager.lock().await;
    if manager_lock.is_none() {
        let manager = LogWebSocketManager::new(app_handle);
        *manager_lock = Some(manager);
        log::info!("WebSocket 日志管理器已初始化");
    }
    Ok(())
}

/**
 * 连接到 WebSocket 日志服务
 *
 * @param url WebSocket URL
 * @param token 认证令牌（可选）
 * @param state WebSocket状态
 */
#[tauri::command]
pub async fn connect_log_websocket(
    url: String,
    token: Option<String>,
    state: State<'_, LogWsState>,
) -> Result<(), String> {
    let manager_lock = state.manager.lock().await;
    if let Some(ref manager) = *manager_lock {
        manager.connect(url, token)
    } else {
        Err("WebSocket 日志管理器未初始化".to_string())
    }
}

/**
 * 断开 WebSocket 日志连接
 *
 * @param state WebSocket状态
 */
#[tauri::command]
pub async fn disconnect_log_websocket(state: State<'_, LogWsState>) -> Result<(), String> {
    let manager_lock = state.manager.lock().await;
    if let Some(ref manager) = *manager_lock {
        manager.disconnect()
    } else {
        Err("WebSocket 日志管理器未初始化".to_string())
    }
}

/**
 * 获取 WebSocket 日志连接状态
 *
 * @param state WebSocket状态
 * @return 连接状态
 */
#[tauri::command]
pub async fn get_log_websocket_state(
    state: State<'_, LogWsState>,
) -> Result<ConnectionState, String> {
    let manager_lock = state.manager.lock().await;
    if let Some(ref manager) = *manager_lock {
        Ok(manager.get_state().await)
    } else {
        Ok(ConnectionState::Disconnected)
    }
}

/**
 * 订阅日志
 *
 * @param options 订阅选项
 * @param state WebSocket状态
 */
#[tauri::command]
pub async fn subscribe_logs(
    options: SubscribeOptions,
    state: State<'_, LogWsState>,
) -> Result<(), String> {
    let manager_lock = state.manager.lock().await;
    if let Some(ref manager) = *manager_lock {
        manager.subscribe(options)
    } else {
        Err("WebSocket 日志管理器未初始化".to_string())
    }
}

/**
 * 取消订阅日志
 *
 * @param state WebSocket状态
 */
#[tauri::command]
pub async fn unsubscribe_logs(state: State<'_, LogWsState>) -> Result<(), String> {
    let manager_lock = state.manager.lock().await;
    if let Some(ref manager) = *manager_lock {
        manager.unsubscribe()
    } else {
        Err("WebSocket 日志管理器未初始化".to_string())
    }
}
