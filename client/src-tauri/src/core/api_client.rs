/**
 * API 客户端模块
 *
 * 封装与后端服务的 HTTP 通信
 */
use super::config::{get_auth_token, get_server_url};
use crate::models::{
    ActionResponse, ConfigResponse, ConfigUpdateRequest, LogCleanupResponse, LogContentResponse,
    LogInfoResponse, ServiceStatus,
};
use reqwest::{header, Client};
use serde::{de::DeserializeOwned, Serialize};

/// API 客户端
pub struct ApiClient {
    client: Client,
    base_url: String,
    use_local_auth: bool,
}

impl ApiClient {
    /// 创建新的 API 客户端
    pub fn new() -> Result<Self, String> {
        let base_url = get_server_url()?;

        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .map_err(|e| format!("创建 HTTP 客户端失败: {}", e))?;

        Ok(Self {
            client,
            base_url,
            use_local_auth: true,
        })
    }

    /// 创建不使用本地认证的客户端（用于外部 API）
    pub fn new_without_local_auth() -> Result<Self, String> {
        let base_url = get_server_url()?;

        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .map_err(|e| format!("创建 HTTP 客户端失败: {}", e))?;

        Ok(Self {
            client,
            base_url,
            use_local_auth: false,
        })
    }

    /// 获取完整 URL
    fn get_url(&self, path: &str) -> String {
        format!("{}{}", self.base_url, path)
    }

    /// 构建请求头
    fn build_headers(&self) -> Result<header::HeaderMap, String> {
        let mut headers = header::HeaderMap::new();

        // 添加 Content-Type
        headers.insert(
            header::CONTENT_TYPE,
            header::HeaderValue::from_static("application/json"),
        );

        log::debug!("构建请求头 - use_local_auth: {}", self.use_local_auth);

        // 优先使用本地认证（如果启用）
        if self.use_local_auth {
            match super::local_auth::get_auth_headers() {
                Ok(auth_headers) => {
                    log::debug!("获取到本地认证头，数量: {}", auth_headers.len());
                    for (key, value) in auth_headers {
                        let header_name = header::HeaderName::from_bytes(key.as_bytes())
                            .map_err(|e| format!("无效的请求头名: {}", e))?;
                        let header_value = header::HeaderValue::from_str(&value)
                            .map_err(|e| format!("无效的请求头值: {}", e))?;
                        headers.insert(header_name, header_value);
                    }
                    return Ok(headers);
                }
                Err(e) => {
                    log::warn!("获取本地认证头失败: {}", e);
                }
            }
        }

        // 回退到普通 JWT 认证
        if let Ok(Some(token)) = get_auth_token() {
            let auth_value = format!("Bearer {}", token);
            let header_value = header::HeaderValue::from_str(&auth_value)
                .map_err(|e| format!("无效的认证令牌: {}", e))?;
            headers.insert(header::AUTHORIZATION, header_value);
        }

        Ok(headers)
    }

    /// 发送 GET 请求
    pub async fn get<T: DeserializeOwned>(&self, path: &str) -> Result<T, String> {
        let headers = self.build_headers()?;
        let url = self.get_url(path);

        let response = self
            .client
            .get(&url)
            .headers(headers)
            .send()
            .await
            .map_err(|e| format!("请求失败: {}", e))?;

        self.handle_response(response).await
    }

    /// 发送 POST 请求
    pub async fn post<T: DeserializeOwned, B: Serialize>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<T, String> {
        let headers = self.build_headers()?;
        let url = self.get_url(path);

        let response = self
            .client
            .post(&url)
            .headers(headers)
            .json(body)
            .send()
            .await
            .map_err(|e| format!("请求失败: {}", e))?;

        self.handle_response(response).await
    }

    /// 发送带超时的 POST 请求
    pub async fn post_with_timeout<B: Serialize>(
        &self,
        path: &str,
        body: &B,
        timeout_secs: u64,
    ) -> Result<reqwest::Response, String> {
        let headers = self.build_headers()?;
        let url = self.get_url(path);

        // 创建短超时客户端
        let timeout_client = Client::builder()
            .timeout(std::time::Duration::from_secs(timeout_secs))
            .build()
            .map_err(|e| format!("创建 HTTP 客户端失败: {}", e))?;

        timeout_client
            .post(&url)
            .headers(headers)
            .json(body)
            .send()
            .await
            .map_err(|e| format!("请求失败: {}", e))
    }

    /// 处理响应
    async fn handle_response<T: DeserializeOwned>(
        &self,
        response: reqwest::Response,
    ) -> Result<T, String> {
        let status = response.status();

        if status.is_success() {
            let data = response
                .json::<T>()
                .await
                .map_err(|e| format!("解析响应失败: {}", e))?;
            Ok(data)
        } else {
            let text = response
                .text()
                .await
                .unwrap_or_else(|_| "未知错误".to_string());
            Err(format!("HTTP {}: {}", status, text))
        }
    }
}

// ==================== 服务管理 API ====================

/// 获取服务状态（不需要认证）
pub async fn get_service_status() -> Result<ServiceStatus, String> {
    let client = ApiClient::new_without_local_auth()?;
    client.get("/api/app/status").await
}

/// 启动服务
pub async fn start_service() -> Result<ActionResponse, String> {
    // 注意：实际启动服务是通过本地进程管理，不是 HTTP API
    // 这里返回模拟响应
    Ok(ActionResponse {
        success: true,
        message: "服务启动命令已发送".to_string(),
    })
}

/// 停止服务（带超时）
pub async fn stop_service_with_timeout(timeout_secs: u64) -> Result<ActionResponse, String> {
    // 使用 ApiClient 发送请求，会自动添加本地认证头
    let client = ApiClient::new()?;

    match client
        .post_with_timeout("/api/app/shutdown", &serde_json::json!({}), timeout_secs)
        .await
    {
        Ok(response) => {
            let status = response.status();
            if status.is_success() {
                response
                    .json::<ActionResponse>()
                    .await
                    .map_err(|e| format!("解析响应失败: {}", e))
            } else {
                Err(format!("请求失败: HTTP {}", status))
            }
        }
        Err(e) => Err(format!("请求失败: {}", e)),
    }
}

/// 停止服务（默认30秒超时）
pub async fn stop_service() -> Result<ActionResponse, String> {
    stop_service_with_timeout(30).await
}

/// 重启服务
pub async fn restart_service() -> Result<ActionResponse, String> {
    let client = ApiClient::new()?;
    client
        .post("/api/app/restart", &serde_json::json!({}))
        .await
}

// ==================== 日志管理 API ====================

/// 获取日志信息
pub async fn get_log_info() -> Result<LogInfoResponse, String> {
    let client = ApiClient::new()?;
    client.get("/api/app/logs").await
}

/// 获取日志内容
pub async fn get_log_content(
    date: Option<String>,
    log_name: String,
    lines: i32,
    level: Option<String>,
) -> Result<LogContentResponse, String> {
    let client = ApiClient::new()?;

    let mut url = format!(
        "/api/app/logs/content?log_name={}&lines={}",
        log_name, lines
    );

    if let Some(d) = date {
        url.push_str(&format!("&date={}", d));
    }

    if let Some(l) = level {
        url.push_str(&format!("&level={}", l));
    }

    client.get(&url).await
}

/// 清理旧日志
pub async fn cleanup_logs(keep_days: i32) -> Result<LogCleanupResponse, String> {
    let client = ApiClient::new()?;
    let url = format!("/api/app/logs/cleanup?keep_days={}", keep_days);
    client.post(&url, &serde_json::json!({})).await
}

// ==================== 配置管理 API ====================

/// 获取应用配置
pub async fn get_app_config(section: Option<String>) -> Result<ConfigResponse, String> {
    let client = ApiClient::new()?;

    let url = if let Some(s) = section {
        format!("/api/app/config?section={}", s)
    } else {
        "/api/app/config".to_string()
    };

    client.get(&url).await
}

/// 更新应用配置
pub async fn update_app_config(config: serde_json::Value) -> Result<ConfigResponse, String> {
    let client = ApiClient::new()?;
    let request = ConfigUpdateRequest { config };
    client.post("/api/app/config", &request).await
}

/// 重置应用配置
pub async fn reset_app_config() -> Result<ConfigResponse, String> {
    let client = ApiClient::new()?;
    client
        .post("/api/app/config/reset", &serde_json::json!({}))
        .await
}

/// 验证应用配置
pub async fn validate_app_config(
    config: Option<serde_json::Value>,
) -> Result<ConfigResponse, String> {
    let client = ApiClient::new()?;
    client.post("/api/app/config/validate", &config).await
}

// ==================== 数据库迁移 API ====================

/// 执行迁移预检查
pub async fn precheck_migration(
    target_url: &str,
) -> Result<crate::models::PrecheckResponse, String> {
    let client = ApiClient::new()?;
    let request = crate::models::PrecheckRequest {
        target_url: target_url.to_string(),
    };
    client.post("/api/v1/migration/precheck", &request).await
}

/// 执行数据库迁移
pub async fn execute_migration(
    target_url: &str,
    batch_size: Option<i32>,
) -> Result<crate::models::MigrationResponse, String> {
    let client = ApiClient::new()?;
    let request = crate::models::MigrationRequest {
        target_url: target_url.to_string(),
        batch_size,
        tables: None,
    };
    client.post("/api/v1/migration/execute", &request).await
}

// ==================== Debug 端点 API ====================

/// 重置数据库
pub async fn reset_database(
    force: bool,
    create_test_data: bool,
) -> Result<serde_json::Value, String> {
    let client = ApiClient::new()?;
    client
        .post(
            &format!(
                "/api/v1/debug/initdb?force={}&create_test_data={}",
                force, create_test_data
            ),
            &serde_json::json!({}),
        )
        .await
}

/// 重置配置文件
pub async fn reset_config(force: bool, backup: bool) -> Result<serde_json::Value, String> {
    let client = ApiClient::new()?;
    client
        .post(
            &format!("/api/v1/debug/initconf?force={}&backup={}", force, backup),
            &serde_json::json!({}),
        )
        .await
}

/// 获取调试状态
pub async fn get_debug_status() -> Result<serde_json::Value, String> {
    let client = ApiClient::new()?;
    client.get("/api/v1/debug/status").await
}
