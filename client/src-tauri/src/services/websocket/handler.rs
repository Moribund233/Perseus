/**
 * WebSocket 消息处理模块
 *
 * 处理接收到的 WebSocket 消息并触发相应事件
 */
use std::sync::Arc;
use tauri::{AppHandle, Emitter};
use tokio::sync::RwLock;

use super::types::{ConnectionState, LogEntry, WsMessage};

/**
 * 处理 WebSocket 消息
 *
 * @param app_handle Tauri 应用句柄
 * @param text 消息文本
 * @param log_buffer 日志缓冲区
 * @param max_buffer_size 最大缓冲区大小
 * @param state 连接状态
 */
pub async fn handle_message(
    app_handle: &AppHandle,
    text: &str,
    log_buffer: &mut Vec<LogEntry>,
    max_buffer_size: usize,
    state: &Arc<RwLock<ConnectionState>>,
) {
    match serde_json::from_str::<WsMessage>(text) {
        Ok(msg) => {
            match msg {
                WsMessage::Log {
                    timestamp,
                    level,
                    logger,
                    message,
                } => {
                    let entry = LogEntry {
                        timestamp,
                        level,
                        logger,
                        message,
                    };

                    // 添加到缓冲区
                    log_buffer.push(entry.clone());
                    if log_buffer.len() > max_buffer_size {
                        log_buffer.drain(0..log_buffer.len() - max_buffer_size);
                    }

                    // 发送到前端
                    let _ = app_handle.emit("log:new", entry);
                }
                WsMessage::LogHistory { logs } => {
                    // 更新缓冲区
                    log_buffer.extend(logs.clone());
                    if log_buffer.len() > max_buffer_size {
                        log_buffer.drain(0..log_buffer.len() - max_buffer_size);
                    }

                    // 发送到前端
                    let _ = app_handle.emit("log:history", logs);
                }
                WsMessage::LogsSubscribed => {
                    *state.write().await = ConnectionState::Subscribed;
                    emit_state_change(app_handle, ConnectionState::Subscribed).await;
                }
                WsMessage::LogsUnsubscribed => {
                    *state.write().await = ConnectionState::Connected;
                    emit_state_change(app_handle, ConnectionState::Connected).await;
                }
                WsMessage::Connected => {
                    // 服务端确认连接成功
                    *state.write().await = ConnectionState::Connected;
                    emit_state_change(app_handle, ConnectionState::Connected).await;
                    log::info!("WebSocket 连接已确认");
                }
                WsMessage::Pong { .. } => {
                    // 心跳响应，无需处理
                }
                WsMessage::Error { error } => {
                    emit_error(app_handle, &error).await;
                }
                _ => {}
            }
        }
        Err(e) => {
            log::warn!("解析 WebSocket 消息失败: {}", e);
        }
    }
}

/**
 * 发送状态变化事件
 *
 * @param app_handle Tauri 应用句柄
 * @param state 新状态
 */
pub async fn emit_state_change(app_handle: &AppHandle, state: ConnectionState) {
    let _ = app_handle.emit("log:state-change", state);
}

/**
 * 发送错误事件
 *
 * @param app_handle Tauri 应用句柄
 * @param error 错误信息
 */
pub async fn emit_error(app_handle: &AppHandle, error: &str) {
    let _ = app_handle.emit("log:error", error);
}
