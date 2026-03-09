/**
 * WebSocket 管理器模块
 *
 * 提供 WebSocket 连接的生命周期管理
 */
use std::sync::Arc;
use std::time::Duration;
use tauri::AppHandle;
use tokio::sync::{mpsc, RwLock};
use tokio::time::interval;

use super::connection::{
    connect, send_ping, send_subscribe, send_unsubscribe, try_reconnect, WebSocketStream,
};
use super::handler::{emit_error, emit_state_change, handle_message};
use super::types::{ConnectionState, InternalCommand, LogFilters, SubscribeOptions};

/// WebSocket 日志管理器
pub struct WebSocketManager {
    /// 当前状态
    state: Arc<RwLock<ConnectionState>>,
    /// 命令发送通道
    command_tx: mpsc::UnboundedSender<InternalCommand>,
}

impl WebSocketManager {
    /// 创建新的管理器
    pub fn new(app_handle: AppHandle) -> Self {
        let (command_tx, command_rx) = mpsc::unbounded_channel();
        let state = Arc::new(RwLock::new(ConnectionState::Disconnected));
        let manager = Self {
            state: state.clone(),
            command_tx,
        };

        // 启动后台任务
        tokio::spawn(Self::run_event_loop(app_handle, state, command_rx));

        manager
    }

    /// 获取当前状态
    pub async fn get_state(&self) -> ConnectionState {
        *self.state.read().await
    }

    /// 连接到 WebSocket 服务器
    pub fn connect(&self, url: String, token: Option<String>) -> Result<(), String> {
        self.command_tx
            .send(InternalCommand::Connect { url, token })
            .map_err(|e| format!("发送连接命令失败: {}", e))
    }

    /// 断开连接
    pub fn disconnect(&self) -> Result<(), String> {
        self.command_tx
            .send(InternalCommand::Disconnect)
            .map_err(|e| format!("发送断开命令失败: {}", e))
    }

    /// 订阅日志
    pub fn subscribe(&self, options: SubscribeOptions) -> Result<(), String> {
        self.command_tx
            .send(InternalCommand::Subscribe(options))
            .map_err(|e| format!("发送订阅命令失败: {}", e))
    }

    /// 取消订阅
    pub fn unsubscribe(&self) -> Result<(), String> {
        self.command_tx
            .send(InternalCommand::Unsubscribe)
            .map_err(|e| format!("发送取消订阅命令失败: {}", e))
    }

    /// 获取统计信息
    pub fn get_stats(&self) -> Result<(), String> {
        self.command_tx
            .send(InternalCommand::GetStats)
            .map_err(|e| format!("发送获取统计命令失败: {}", e))
    }

    /// 事件循环
    async fn run_event_loop(
        app_handle: AppHandle,
        state: Arc<RwLock<ConnectionState>>,
        mut command_rx: mpsc::UnboundedReceiver<InternalCommand>,
    ) {
        let mut ws_stream: Option<WebSocketStream> = None;
        let mut reconnect_attempts = 0;
        let max_reconnect_attempts = 5;
        let mut current_url: Option<String> = None;
        let mut current_token: Option<String> = None;
        let mut current_filters: Option<LogFilters> = None;
        let mut ping_interval = interval(Duration::from_secs(30));
        let mut log_buffer: Vec<super::types::LogEntry> = Vec::with_capacity(1000);
        let max_buffer_size = 5000;

        loop {
            tokio::select! {
                // 处理命令
                Some(cmd) = command_rx.recv() => {
                    match cmd {
                        InternalCommand::Connect { url, token } => {
                            current_url = Some(url.clone());
                            current_token = token.clone();

                            // 更新状态
                            *state.write().await = ConnectionState::Connecting;
                            emit_state_change(&app_handle, ConnectionState::Connecting).await;

                            // 尝试连接
                            match connect(&url, token.as_deref()).await {
                                Ok(stream) => {
                                    ws_stream = Some(stream);
                                    reconnect_attempts = 0;
                                    *state.write().await = ConnectionState::Connected;
                                    emit_state_change(&app_handle, ConnectionState::Connected).await;
                                    log::info!("WebSocket 日志连接已建立");
                                }
                                Err(e) => {
                                    log::error!("WebSocket 连接失败: {}", e);
                                    *state.write().await = ConnectionState::Error;
                                    emit_state_change(&app_handle, ConnectionState::Error).await;
                                    emit_error(&app_handle, &format!("连接失败: {}", e)).await;
                                }
                            }
                        }
                        InternalCommand::Disconnect => {
                            if let Some(mut stream) = ws_stream.take() {
                                let _ = stream.close(None).await;
                            }
                            *state.write().await = ConnectionState::Disconnected;
                            emit_state_change(&app_handle, ConnectionState::Disconnected).await;
                            current_url = None;
                            current_token = None;
                            current_filters = None;
                            log_buffer.clear();
                        }
                        InternalCommand::Subscribe(options) => {
                            if let Some(ref mut stream) = ws_stream {
                                current_filters = options.filters.clone();

                                if let Err(e) = send_subscribe(
                                    stream,
                                    options.filters.unwrap_or_default(),
                                    options.history_count.unwrap_or(50),
                                ).await {
                                    log::error!("{}", e);
                                }
                            }
                        }
                        InternalCommand::Unsubscribe => {
                            if let Some(ref mut stream) = ws_stream {
                                if let Err(e) = send_unsubscribe(stream).await {
                                    log::error!("{}", e);
                                }
                            }
                            *state.write().await = ConnectionState::Connected;
                            emit_state_change(&app_handle, ConnectionState::Connected).await;
                        }
                        InternalCommand::GetStats => {
                            // 可以在这里实现获取统计信息的逻辑
                        }
                    }
                }

                // 处理 WebSocket 消息
                Some(msg_result) = async {
                    if let Some(ref mut stream) = ws_stream {
                        use futures::StreamExt;
                        stream.next().await
                    } else {
                        None
                    }
                } => {
                    match msg_result {
                        Ok(msg) => {
                            use tokio_tungstenite::tungstenite::Message;
                            match msg {
                                Message::Text(text) => {
                                    handle_message(&app_handle, &text, &mut log_buffer, max_buffer_size, &state).await;
                                }
                                Message::Close(_) => {
                                    log::warn!("WebSocket 连接已关闭");
                                    ws_stream = None;
                                    *state.write().await = ConnectionState::Disconnected;
                                    emit_state_change(&app_handle, ConnectionState::Disconnected).await;

                                    // 尝试重连
                                    if let Some(ref url) = current_url {
                                        if reconnect_attempts < max_reconnect_attempts {
                                            reconnect_attempts += 1;

                                            if let Some(stream) = try_reconnect(
                                                url,
                                                current_token.as_deref(),
                                                reconnect_attempts,
                                                max_reconnect_attempts,
                                            ).await {
                                                ws_stream = Some(stream);
                                                reconnect_attempts = 0;
                                                *state.write().await = ConnectionState::Connected;
                                                emit_state_change(&app_handle, ConnectionState::Connected).await;

                                                // 重新订阅
                                                if let Some(ref filters) = current_filters {
                                                    if let Some(ref mut stream) = ws_stream {
                                                        let _ = send_subscribe(stream, filters.clone(), 50).await;
                                                    }
                                                }
                                            }
                                        } else {
                                            emit_error(&app_handle, "WebSocket 重连失败，已达到最大重试次数").await;
                                        }
                                    }
                                }
                                _ => {}
                            }
                        }
                        Err(e) => {
                            // 检查是否是服务端正常关闭连接
                            let error_str = e.to_string();
                            let is_graceful_shutdown = error_str.contains("os error 10054")  // Windows: 远程主机强迫关闭连接
                                || error_str.contains("os error 10053")  // Windows: 软件中止连接
                                || error_str.contains("Connection reset by peer")
                                || error_str.contains("Connection aborted")
                                || error_str.contains("broken pipe");

                            if is_graceful_shutdown {
                                // 服务端正常关闭，使用 WARN 级别并显示友好消息
                                log::warn!("WebSocket 连接已断开: 服务端已关闭");
                                ws_stream = None;
                                *state.write().await = ConnectionState::Disconnected;
                                emit_state_change(&app_handle, ConnectionState::Disconnected).await;
                                // 不发送错误事件，因为这是预期的行为
                            } else {
                                // 真正的错误，使用 ERROR 级别
                                log::error!("WebSocket 错误: {}", e);
                                ws_stream = None;
                                *state.write().await = ConnectionState::Error;
                                emit_state_change(&app_handle, ConnectionState::Error).await;
                                emit_error(&app_handle, &format!("WebSocket 错误: {}", e)).await;
                            }
                        }
                    }
                }

                // 心跳
                _ = ping_interval.tick() => {
                    if let Some(ref mut stream) = ws_stream {
                        if let Err(e) = send_ping(stream).await {
                            log::warn!("{}", e);
                        }
                    }
                }

                // 没有其他事件时继续循环
                else => {
                    tokio::time::sleep(Duration::from_millis(100)).await;
                }
            }
        }
    }
}
