/**
 * 数据模型定义
 *
 * 定义与后端 API 交互的数据结构
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

/// 系统信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemInfo {
    pub platform: String,
    pub platform_version: String,
    pub architecture: String,
    pub processor: String,
    pub hostname: String,
    pub cpu_count: i32,
    pub cpu_freq_mhz: Option<f64>,
    pub cpu_percent: f64,
    pub memory_total_gb: f64,
    pub memory_used_gb: f64,
    pub memory_percent: f64,
    pub disk_total_gb: f64,
    pub disk_used_gb: f64,
    pub disk_percent: f64,
    pub network: NetworkInfo,
}

/// 网络信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkInfo {
    pub bytes_sent: u64,
    pub bytes_received: u64,
    pub packets_sent: u64,
    pub packets_received: u64,
    pub errors_in: u64,
    pub errors_out: u64,
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

/// 日志信息响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogInfoResponse {
    pub log_dir: String,
    pub today_dir: String,
    pub today_files: Vec<LogFileInfo>,
    pub available_dates: Vec<String>,
}

/// 日志文件信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogFileInfo {
    pub name: String,
    pub size: i64,
    pub size_formatted: String,
    pub modified: String,
}

/// 日志内容响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogContentResponse {
    pub date: String,
    pub log_name: String,
    pub lines: i32,
    pub total_lines: i32,
    pub content: String,
    pub exists: bool,
}

/// 日志清理响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogCleanupResponse {
    pub success: bool,
    pub deleted_count: i32,
    pub keep_days: i32,
}

/// 应用配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppSettings {
    pub server: ServerSettings,
    pub appearance: AppearanceSettings,
    pub notification: NotificationSettings,
}

/// 服务器设置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerSettings {
    pub port: i32,
    pub host: String,
    pub auto_start: bool,
    pub max_connections: i32,
    pub log_level: String,
    pub log_retention: i32,
}

/// 外观设置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppearanceSettings {
    pub theme: String,
    pub language: String,
    pub sidebar_collapsed: bool,
}

/// 通知设置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationSettings {
    pub enabled: bool,
    pub on_error: bool,
    pub on_warning: bool,
    pub on_start_stop: bool,
}

/// 本地认证配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalAuthConfig {
    /// JWT Secret Key（用于签名本地 Token）
    pub jwt_secret_key: String,
    /// 本地管理员 Token
    pub local_token: String,
    /// 是否启用调试模式
    pub debug_mode: bool,
}

impl Default for LocalAuthConfig {
    fn default() -> Self {
        Self {
            jwt_secret_key: String::new(),
            local_token: String::new(),
            debug_mode: true,
        }
    }
}

/**
 * 服务端路径配置
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerPathConfig {
    /// 服务端可执行文件名
    pub exe_name: String,
    /// 服务端目录名（PyInstaller 目录模式）
    pub dir_name: String,
    /// 自定义服务端路径（可选，如果设置则优先使用）
    pub custom_path: Option<String>,
}

impl Default for ServerPathConfig {
    fn default() -> Self {
        Self {
            exe_name: String::from("langit-server.exe"),
            dir_name: String::from("langit-server"),
            custom_path: None,
        }
    }
}

/**
 * 服务器配置
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    /// 服务端地址
    pub url: String,
    /// 是否自动连接
    pub auto_connect: bool,
    /// 是否自动启动服务端
    pub auto_start: bool,
    /// 服务端路径配置
    #[serde(default)]
    pub path: ServerPathConfig,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            url: String::from("http://127.0.0.1:8000"),
            auto_connect: true,
            auto_start: false,
            path: ServerPathConfig::default(),
        }
    }
}

/**
 * 外观配置
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppearanceConfig {
    /// 主题: dark, light, auto
    pub theme: String,
    /// 语言: zh, en
    pub language: String,
    /// 侧边栏是否折叠
    pub sidebar_collapsed: bool,
}

impl Default for AppearanceConfig {
    fn default() -> Self {
        Self {
            theme: String::from("dark"),
            language: String::from("zh"),
            sidebar_collapsed: false,
        }
    }
}

/**
 * 通知配置
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationConfig {
    /// 是否启用通知
    pub enabled: bool,
    /// 错误时通知
    pub on_error: bool,
    /// 警告时通知
    pub on_warning: bool,
    /// 服务启动/停止时通知
    pub on_start_stop: bool,
}

impl Default for NotificationConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            on_error: true,
            on_warning: false,
            on_start_stop: true,
        }
    }
}

/**
 * 日志配置
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogConfig {
    /// 日志级别: debug, info, warning, error
    pub level: String,
    /// 日志保留天数
    pub retention_days: i32,
}

impl Default for LogConfig {
    fn default() -> Self {
        Self {
            level: String::from("info"),
            retention_days: 7,
        }
    }
}

/**
 * 高级配置
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdvancedConfig {
    /// WebSocket 重连间隔（毫秒）
    pub ws_reconnect_interval: u64,
    /// 连接超时（秒）
    pub connection_timeout: u64,
    /// 请求超时（秒）
    pub request_timeout: u64,
}

impl Default for AdvancedConfig {
    fn default() -> Self {
        Self {
            ws_reconnect_interval: 3000,
            connection_timeout: 30,
            request_timeout: 30,
        }
    }
}

/// 客户端配置（新版 TOML 格式）
/// 注意：敏感配置（JWT密钥、本地Token）存储在加密的 client-config.json 中
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ClientConfig {
    /// 服务器配置
    #[serde(default)]
    pub server: ServerConfig,
    /// 外观配置
    #[serde(default)]
    pub appearance: AppearanceConfig,
    /// 通知配置
    #[serde(default)]
    pub notification: NotificationConfig,
    /// 日志配置
    #[serde(default)]
    pub log: LogConfig,
    /// 高级配置
    #[serde(default)]
    pub advanced: AdvancedConfig,
    /// 认证令牌（保留用于向后兼容，建议迁移到加密存储）
    #[serde(default)]
    pub auth_token: Option<String>,
    /// Nginx配置
    #[serde(default)]
    pub nginx: NginxConfig,
}

/**
 * Nginx配置
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NginxConfig {
    /// Nginx可执行文件路径
    pub exe_path: Option<String>,
    /// Nginx配置目录路径
    pub config_dir: Option<String>,
    /// 下载URL（支持自定义镜像站）
    pub download_url: String,
    /// 是否已载入
    pub is_loaded: bool,
    /// 当前状态: stopped, running, error
    pub status: String,
    /// 进程ID
    pub pid: Option<u32>,
    /// 版本信息
    pub version: Option<String>,
    /// 代理配置
    #[serde(default)]
    pub proxy: NginxProxyConfig,
}

impl Default for NginxConfig {
    fn default() -> Self {
        Self {
            exe_path: None,
            config_dir: None,
            download_url: String::from("https://nginx.org/download/nginx-1.24.0.zip"),
            is_loaded: false,
            status: String::from("stopped"),
            pid: None,
            version: None,
            proxy: NginxProxyConfig::default(),
        }
    }
}

/**
 * Nginx状态响应
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NginxStatusResponse {
    /// 是否已载入
    pub is_loaded: bool,
    /// 当前状态: stopped, running, error
    pub status: String,
    /// 进程ID
    pub pid: Option<u32>,
    /// 版本信息
    pub version: Option<String>,
    /// 可执行文件路径
    pub exe_path: Option<String>,
    /// 配置目录路径
    pub config_dir: Option<String>,
}

/**
 * Nginx操作响应
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NginxActionResponse {
    /// 是否成功
    pub success: bool,
    /// 消息
    pub message: String,
    /// 状态
    pub status: Option<String>,
    /// 进程ID
    pub pid: Option<u32>,
}

/**
 * Nginx代理配置
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NginxProxyConfig {
    /// 是否启用反向代理
    pub enabled: bool,
    /// 监听端口
    pub listen_port: u16,
    /// 后端服务URL
    pub backend_url: String,
    /// 是否添加安全头
    pub add_security_headers: bool,
    /// 是否添加CORS头
    pub add_cors_headers: bool,
    /// CORS允许的源
    pub cors_origins: String,
    /// CORS允许的方法
    pub cors_methods: String,
    /// CORS允许的头
    pub cors_headers: String,
    /// 是否启用HSTS
    pub enable_hsts: bool,
    /// HSTS max-age
    pub hsts_max_age: u32,
    /// 服务器名称
    pub server_name: String,
}

impl Default for NginxProxyConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            listen_port: 80,
            backend_url: String::from("http://127.0.0.1:8000"),
            add_security_headers: true,
            add_cors_headers: true,
            cors_origins: String::from("*"),
            cors_methods: String::from("GET, POST, PUT, DELETE, OPTIONS"),
            cors_headers: String::from("Content-Type, Authorization"),
            enable_hsts: false,
            hsts_max_age: 31536000,
            server_name: String::from("_"),
        }
    }
}

/**
 * Nginx配置保存请求
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NginxConfigSaveRequest {
    /// 代理配置
    pub proxy: NginxProxyConfig,
}

/**
 * Nginx配置保存响应
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NginxConfigSaveResponse {
    /// 是否成功
    pub success: bool,
    /// 消息
    pub message: String,
    /// 是否需要重启
    pub need_restart: bool,
}

/**
 * Nginx下载配置
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NginxDownloadConfig {
    /// 下载URL
    pub url: String,
    /// 解压目标目录
    pub target_dir: Option<String>,
}

/**
 * Nginx平台信息
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NginxPlatformInfo {
    /// 当前平台: windows, linux, macos
    pub platform: String,
    /// 是否支持手动载入（Windows）
    pub supports_manual_load: bool,
    /// 是否支持下载（Windows）
    pub supports_download: bool,
    /// 是否使用包管理器（Linux）
    pub uses_package_manager: bool,
    /// 包管理器类型: apt, yum, dnf, pacman, apk等
    pub package_manager: Option<String>,
    /// Nginx版本（通过包管理器获取）
    pub package_version: Option<String>,
    /// 配置文件路径（Linux系统路径）
    pub config_path: Option<String>,
}
