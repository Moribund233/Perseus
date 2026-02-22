use crate::config::{get_auth_token, get_server_url};
use crate::models::*;
/**
 * API 客户端模块
 *
 * 封装与后端服务的 HTTP 通信
 */
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
            match crate::local_auth::get_auth_headers() {
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
    let base_url = get_server_url()?;

    // 创建短超时客户端
    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(timeout_secs))
        .build()
        .map_err(|e| format!("创建 HTTP 客户端失败: {}", e))?;

    let url = format!("{}/api/app/shutdown", base_url);

    match client.post(&url).send().await {
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

/// 数据库迁移请求
#[derive(Debug, serde::Serialize)]
pub struct DatabaseMigrateRequest {
    pub source_type: String,
    pub target_type: String,
    pub source_url: String,
    pub target_url: String,
}

/// 数据库迁移响应
#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct DatabaseMigrateResponse {
    pub success: bool,
    pub message: String,
    pub tables: Option<serde_json::Value>,
    pub export_file: Option<String>,
}

/// 数据库状态响应
#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct DatabaseStatusResponse {
    pub current_db_type: Option<String>,
    pub target_db_type: String,
    pub migration_required: bool,
    pub message: String,
}

/// 获取数据库状态
pub async fn get_database_status() -> Result<DatabaseStatusResponse, String> {
    let client = ApiClient::new()?;
    client.get("/api/app/database/status").await
}

/// 执行数据库迁移
pub async fn migrate_database(
    request: DatabaseMigrateRequest,
) -> Result<DatabaseMigrateResponse, String> {
    let client = ApiClient::new()?;
    client.post("/api/app/database/migrate", &request).await
}

/// 测试数据库连接（已弃用，保留用于兼容性）
pub async fn test_database_connection(db_url: String) -> Result<ConfigResponse, String> {
    let client = ApiClient::new()?;
    let body = serde_json::json!({ "db_url": db_url });
    client
        .post("/api/app/database/test-connection", &body)
        .await
}

/// 检查数据库内容和状态
pub async fn check_database(db_url: String) -> Result<ConfigResponse, String> {
    let client = ApiClient::new()?;
    let body = serde_json::json!({ "db_url": db_url });
    client.post("/api/app/database/check", &body).await
}

/// 设置待处理的迁移目标类型
pub async fn set_pending_migration(target_type: String) -> Result<ConfigResponse, String> {
    let client = ApiClient::new()?;
    let body = serde_json::json!({ "target_type": target_type });
    client.post("/api/app/database/pending", &body).await
}

/// 清除待处理的迁移目标类型
pub async fn clear_pending_migration() -> Result<ConfigResponse, String> {
    let client = ApiClient::new()?;
    client.post("/api/app/database/clear-pending", &()).await
}

/// 记录迁移失败
pub async fn record_migration_failed(target_type: String) -> Result<ConfigResponse, String> {
    let client = ApiClient::new()?;
    let body = serde_json::json!({ "target_type": target_type });
    client
        .post("/api/app/database/migration-failed", &body)
        .await
}

/// 清除迁移失败记录
pub async fn clear_migration_failed() -> Result<ConfigResponse, String> {
    let client = ApiClient::new()?;
    client.post("/api/app/database/clear-failed", &()).await
}
