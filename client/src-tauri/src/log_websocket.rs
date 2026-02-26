/**
 * WebSocket 日志管理器
 *
 * 在 Tauri 后端维护稳定的 WebSocket 连接，替代前端直接连接
 * 解决 Linux WebKitGTK WebSocket 不稳定问题
 */
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::Duration;
use tauri::{AppHandle, Emitter};
use tokio::sync::{mpsc, RwLock};
use tokio::time::interval;

/// 日志条目
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub timestamp: String,
    pub level: String,
    pub logger: String,
    pub message: String,
}

/// 日志过滤器
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct LogFilters {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub levels: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub loggers: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub keywords: Option<Vec<String>>,
}

/// 订阅选项
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubscribeOptions {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub filters: Option<LogFilters>,
    #[serde(rename = "history_count", skip_serializing_if = "Option::is_none")]
    pub history_count: Option<usize>,
}

/// 连接状态
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum ConnectionState {
    Disconnected,
    Connecting,
    Connected,
    Subscribed,
    Error,
}

/// WebSocket 消息类型
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
enum WsMessage {
    #[serde(rename = "subscribe_logs")]
    SubscribeLogs {
        filters: LogFilters,
        #[serde(rename = "history_count")]
        history_count: usize,
    },
    #[serde(rename = "unsubscribe_logs")]
    UnsubscribeLogs,
    #[serde(rename = "ping")]
    Ping { timestamp: i64 },
    #[serde(rename = "pong")]
    Pong { timestamp: i64 },
    #[serde(rename = "log")]
    Log {
        timestamp: String,
        level: String,
        logger: String,
        message: String,
    },
    #[serde(rename = "log_history")]
    LogHistory { logs: Vec<LogEntry> },
    #[serde(rename = "logs_subscribed")]
    LogsSubscribed,
    #[serde(rename = "logs_unsubscribed")]
    LogsUnsubscribed,
    #[serde(rename = "connected")]
    Connected,
    #[serde(rename = "error")]
    Error { error: String },
}

/// 内部命令
#[derive(Debug)]
enum InternalCommand {
    Connect { url: String, token: Option<String> },
    Disconnect,
    Subscribe(SubscribeOptions),
    Unsubscribe,
    GetStats,
}

/// WebSocket 日志管理器
pub struct LogWebSocketManager {
    /// 当前状态
    state: Arc<RwLock<ConnectionState>>,
    /// 命令发送通道
    command_tx: mpsc::UnboundedSender<InternalCommand>,
}

impl LogWebSocketManager {
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
        let mut ws_stream: Option<
            tokio_tungstenite::WebSocketStream<
                tokio_tungstenite::MaybeTlsStream<tokio::net::TcpStream>,
            >,
        > = None;
        let mut reconnect_attempts = 0;
        let max_reconnect_attempts = 5;
        let reconnect_interval = Duration::from_secs(3);
        let mut current_url: Option<String> = None;
        let mut current_token: Option<String> = None;
        let mut current_filters: Option<LogFilters> = None;
        let mut ping_interval = interval(Duration::from_secs(30));
        let mut log_buffer: Vec<LogEntry> = Vec::with_capacity(1000);
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
                            Self::emit_state_change(&app_handle, ConnectionState::Connecting).await;

                            // 尝试连接
                            match Self::do_connect(&url, token.as_deref()).await {
                                Ok(stream) => {
                                    ws_stream = Some(stream);
                                    reconnect_attempts = 0;
                                    *state.write().await = ConnectionState::Connected;
                                    Self::emit_state_change(&app_handle, ConnectionState::Connected).await;
                                    log::info!("WebSocket 日志连接已建立");
                                }
                                Err(e) => {
                                    log::error!("WebSocket 连接失败: {}", e);
                                    *state.write().await = ConnectionState::Error;
                                    Self::emit_state_change(&app_handle, ConnectionState::Error).await;
                                    Self::emit_error(&app_handle, &format!("连接失败: {}", e)).await;
                                }
                            }
                        }
                        InternalCommand::Disconnect => {
                            if let Some(mut stream) = ws_stream.take() {
                                let _ = stream.close(None).await;
                            }
                            *state.write().await = ConnectionState::Disconnected;
                            Self::emit_state_change(&app_handle, ConnectionState::Disconnected).await;
                            current_url = None;
                            current_token = None;
                            current_filters = None;
                            log_buffer.clear();
                        }
                        InternalCommand::Subscribe(options) => {
                            if let Some(ref mut stream) = ws_stream {
                                current_filters = options.filters.clone();

                                let msg = WsMessage::SubscribeLogs {
                                    filters: options.filters.unwrap_or_default(),
                                    history_count: options.history_count.unwrap_or(50),
                                };

                                if let Ok(json) = serde_json::to_string(&msg) {
                                    use tokio_tungstenite::tungstenite::Message;
                                    if let Err(e) = stream.send(Message::Text(json)).await {
                                        log::error!("发送订阅消息失败: {}", e);
                                    }
                                }
                            }
                        }
                        InternalCommand::Unsubscribe => {
                            if let Some(ref mut stream) = ws_stream {
                                let msg = WsMessage::UnsubscribeLogs;
                                if let Ok(json) = serde_json::to_string(&msg) {
                                    use tokio_tungstenite::tungstenite::Message;
                                    if let Err(e) = stream.send(Message::Text(json)).await {
                                        log::error!("发送取消订阅消息失败: {}", e);
                                    }
                                }
                            }
                            *state.write().await = ConnectionState::Connected;
                            Self::emit_state_change(&app_handle, ConnectionState::Connected).await;
                        }
                        InternalCommand::GetStats => {
                            // 可以在这里实现获取统计信息的逻辑
                        }
                    }
                }

                // 处理 WebSocket 消息
                Some(msg_result) = async {
                    if let Some(ref mut stream) = ws_stream {
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
                                    Self::handle_ws_message(&app_handle, &text, &mut log_buffer, max_buffer_size, &state).await;
                                }
                                Message::Close(_) => {
                                    log::warn!("WebSocket 连接已关闭");
                                    ws_stream = None;
                                    *state.write().await = ConnectionState::Disconnected;
                                    Self::emit_state_change(&app_handle, ConnectionState::Disconnected).await;

                                    // 尝试重连
                                    if let Some(ref url) = current_url {
                                        if reconnect_attempts < max_reconnect_attempts {
                                            reconnect_attempts += 1;
                                            tokio::time::sleep(reconnect_interval).await;

                                            match Self::do_connect(url, current_token.as_deref()).await {
                                                Ok(stream) => {
                                                    ws_stream = Some(stream);
                                                    reconnect_attempts = 0;
                                                    *state.write().await = ConnectionState::Connected;
                                                    Self::emit_state_change(&app_handle, ConnectionState::Connected).await;
                                                    log::info!("WebSocket 重连成功");

                                                    // 重新订阅
                                                    if let Some(ref filters) = current_filters {
                                                        let sub_msg = WsMessage::SubscribeLogs {
                                                            filters: filters.clone(),
                                                            history_count: 50,
                                                        };
                                                        if let Ok(json) = serde_json::to_string(&sub_msg) {
                                                            use tokio_tungstenite::tungstenite::Message;
                                                            if let Some(ref mut stream) = ws_stream {
                                                                let _ = stream.send(Message::Text(json)).await;
                                                            }
                                                        }
                                                    }
                                                }
                                                Err(e) => {
                                                    log::error!("WebSocket 重连失败: {}", e);
                                                }
                                            }
                                        } else {
                                            Self::emit_error(&app_handle, "WebSocket 重连失败，已达到最大重试次数").await;
                                        }
                                    }
                                }
                                _ => {}
                            }
                        }
                        Err(e) => {
                            log::error!("WebSocket 错误: {}", e);
                            ws_stream = None;
                            *state.write().await = ConnectionState::Error;
                            Self::emit_state_change(&app_handle, ConnectionState::Error).await;
                            Self::emit_error(&app_handle, &format!("WebSocket 错误: {}", e)).await;
                        }
                    }
                }

                // 心跳
                _ = ping_interval.tick() => {
                    if let Some(ref mut stream) = ws_stream {
                        let ping_msg = WsMessage::Ping {
                            timestamp: chrono::Utc::now().timestamp_millis(),
                        };
                        if let Ok(json) = serde_json::to_string(&ping_msg) {
                            use tokio_tungstenite::tungstenite::Message;
                            if let Err(e) = stream.send(Message::Text(json)).await {
                                log::warn!("发送心跳失败: {}", e);
                            }
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

    /// 执行 WebSocket 连接
    async fn do_connect(
        url: &str,
        token: Option<&str>,
    ) -> Result<
        tokio_tungstenite::WebSocketStream<
            tokio_tungstenite::MaybeTlsStream<tokio::net::TcpStream>,
        >,
        String,
    > {
        use tokio_tungstenite::tungstenite::client::IntoClientRequest;

        // 首先检查 HTTP 服务是否就绪
        let http_url = url
            .replace("ws://", "http://")
            .replace("wss://", "https://")
            .replace("/ws/logs", "/health");
        let mut service_ready = false;

        for attempt in 0..3 {
            match reqwest::get(&http_url).await {
                Ok(response) if response.status().is_success() => {
                    service_ready = true;
                    break;
                }
                _ => {
                    if attempt < 2 {
                        log::info!("服务尚未就绪，等待 500ms 后重试...");
                        tokio::time::sleep(Duration::from_millis(500)).await;
                    }
                }
            }
        }

        if !service_ready {
            return Err("服务未就绪，无法建立 WebSocket 连接".to_string());
        }

        let url_with_token = if let Some(t) = token {
            format!("{}?token={}", url, t)
        } else {
            url.to_string()
        };

        let request = url_with_token
            .into_client_request()
            .map_err(|e| format!("创建请求失败: {}", e))?;

        let (ws_stream, _) = tokio_tungstenite::connect_async(request)
            .await
            .map_err(|e| format!("连接失败: {}", e))?;

        Ok(ws_stream)
    }

    /// 处理 WebSocket 消息
    async fn handle_ws_message(
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
                        Self::emit_state_change(app_handle, ConnectionState::Subscribed).await;
                    }
                    WsMessage::LogsUnsubscribed => {
                        *state.write().await = ConnectionState::Connected;
                        Self::emit_state_change(app_handle, ConnectionState::Connected).await;
                    }
                    WsMessage::Connected => {
                        // 服务端确认连接成功
                        *state.write().await = ConnectionState::Connected;
                        Self::emit_state_change(app_handle, ConnectionState::Connected).await;
                        log::info!("WebSocket 连接已确认");
                    }
                    WsMessage::Pong { .. } => {
                        // 心跳响应，无需处理
                    }
                    WsMessage::Error { error } => {
                        Self::emit_error(app_handle, &error).await;
                    }
                    _ => {}
                }
            }
            Err(e) => {
                log::warn!("解析 WebSocket 消息失败: {}", e);
            }
        }
    }

    /// 发送状态变化事件
    async fn emit_state_change(app_handle: &AppHandle, state: ConnectionState) {
        let _ = app_handle.emit("log:state-change", state);
    }

    /// 发送错误事件
    async fn emit_error(app_handle: &AppHandle, error: &str) {
        let _ = app_handle.emit("log:error", error);
    }
}

// 引入 StreamExt 和 SinkExt trait
use futures::{SinkExt, StreamExt};
