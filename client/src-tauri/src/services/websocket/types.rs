/**
 * WebSocket 类型定义模块
 *
 * 定义 WebSocket 通信中使用的所有数据结构
 */
use serde::{Deserialize, Serialize};

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
pub enum WsMessage {
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
pub enum InternalCommand {
    Connect { url: String, token: Option<String> },
    Disconnect,
    Subscribe(SubscribeOptions),
    Unsubscribe,
    GetStats,
}
