/**
 * WebSocket 连接模块
 *
 * 处理 WebSocket 连接的建立和重连逻辑
 */
use std::time::Duration;
use tokio_tungstenite::tungstenite::client::IntoClientRequest;

use super::types::{LogFilters, WsMessage};

/// WebSocket 流类型
pub type WebSocketStream =
    tokio_tungstenite::WebSocketStream<tokio_tungstenite::MaybeTlsStream<tokio::net::TcpStream>>;

/**
 * 执行 WebSocket 连接
 *
 * 首先检查 HTTP 服务是否就绪，然后建立 WebSocket 连接
 *
 * @param url WebSocket URL
 * @param token 认证令牌（可选）
 * @return WebSocket 流
 */
pub async fn connect(url: &str, token: Option<&str>) -> Result<WebSocketStream, String> {
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

/**
 * 尝试重连
 *
 * @param url WebSocket URL
 * @param token 认证令牌（可选）
 * @param attempt 当前重试次数
 * @param max_attempts 最大重试次数
 * @return 重连结果
 */
pub async fn try_reconnect(
    url: &str,
    token: Option<&str>,
    attempt: u32,
    max_attempts: u32,
) -> Option<WebSocketStream> {
    if attempt >= max_attempts {
        log::error!("WebSocket 重连失败，已达到最大重试次数");
        return None;
    }

    let reconnect_interval = Duration::from_secs(3);
    tokio::time::sleep(reconnect_interval).await;

    match connect(url, token).await {
        Ok(stream) => {
            log::info!("WebSocket 重连成功");
            Some(stream)
        }
        Err(e) => {
            log::error!("WebSocket 重连失败: {}", e);
            None
        }
    }
}

/**
 * 发送订阅消息
 *
 * @param stream WebSocket 流
 * @param filters 日志过滤器
 * @param history_count 历史日志数量
 */
pub async fn send_subscribe(
    stream: &mut WebSocketStream,
    filters: LogFilters,
    history_count: usize,
) -> Result<(), String> {
    use futures::SinkExt;
    use tokio_tungstenite::tungstenite::Message;

    let msg = WsMessage::SubscribeLogs {
        filters,
        history_count,
    };

    if let Ok(json) = serde_json::to_string(&msg) {
        stream
            .send(Message::Text(json))
            .await
            .map_err(|e| format!("发送订阅消息失败: {}", e))?;
    }
    Ok(())
}

/**
 * 发送取消订阅消息
 *
 * @param stream WebSocket 流
 */
pub async fn send_unsubscribe(stream: &mut WebSocketStream) -> Result<(), String> {
    use futures::SinkExt;
    use tokio_tungstenite::tungstenite::Message;

    let msg = WsMessage::UnsubscribeLogs;
    if let Ok(json) = serde_json::to_string(&msg) {
        stream
            .send(Message::Text(json))
            .await
            .map_err(|e| format!("发送取消订阅消息失败: {}", e))?;
    }
    Ok(())
}

/**
 * 发送心跳消息
 *
 * @param stream WebSocket 流
 */
pub async fn send_ping(stream: &mut WebSocketStream) -> Result<(), String> {
    use futures::SinkExt;
    use tokio_tungstenite::tungstenite::Message;

    let ping_msg = WsMessage::Ping {
        timestamp: chrono::Utc::now().timestamp_millis(),
    };
    if let Ok(json) = serde_json::to_string(&ping_msg) {
        stream
            .send(Message::Text(json))
            .await
            .map_err(|e| format!("发送心跳失败: {}", e))?;
    }
    Ok(())
}
