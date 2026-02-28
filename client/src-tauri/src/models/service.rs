/**
 * 服务相关模型
 *
 * 定义服务端状态、进程信息、请求统计等数据结构
 */
use serde::{Deserialize, Serialize};

/// 服务状态响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceStatus {
    pub status: String,
    pub debug_mode: bool,
    pub uptime_seconds: i64,
    pub uptime_formatted: String,
    pub version: String,
    pub server_time: String,
    pub process: ServerProcessInfo,
    pub requests: RequestStats,
    pub git_operations: GitOperations,
}

/// 服务端进程信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerProcessInfo {
    pub pid: i32,
    pub memory_mb: f64,
    pub cpu_percent: f64,
    pub threads: i32,
    pub connections: i32,
}

/// 请求统计信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestStats {
    pub total: i64,
    pub success: i64,
    pub failed: i64,
    pub avg_response_time_ms: f64,
    pub requests_per_minute: f64,
}

/// Git操作状态
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitOperations {
    pub active_clones: i32,
    pub active_pushes: i32,
    pub queue_size: i32,
}

/// 性能数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceData {
    pub cpu: f64,
    pub memory: f64,
    pub uptime: i64,
    pub requests: i64,
}

/// 操作响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionResponse {
    pub success: bool,
    pub message: String,
}

/// 配置响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigResponse {
    pub success: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<serde_json::Value>,
    #[serde(default)]
    pub errors: Vec<String>,
    #[serde(default)]
    pub hints: Vec<String>,
}

/// 配置更新请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigUpdateRequest {
    pub config: serde_json::Value,
}

/// 服务端检查结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerCheckResult {
    /// 是否找到服务端
    pub found: bool,
    /// 服务端路径
    pub path: Option<String>,
    /// 服务端版本
    pub version: Option<String>,
    /// 是否自动检测到
    pub auto_detected: bool,
}

/// Git检查结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitCheckResult {
    /// 是否已安装Git
    pub installed: bool,
    /// Git版本
    pub version: Option<String>,
    /// Git路径
    pub path: Option<String>,
    /// git-http-backend是否可用
    pub http_backend_available: bool,
}

/// TCP连接测试结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TcpTestResult {
    /// 是否成功
    pub success: bool,
    /// 错误信息
    pub error: Option<String>,
}
