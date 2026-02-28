/**
 * Nginx 相关模型
 *
 * 定义 Nginx 配置、状态、代理配置等数据结构
 */
use serde::{Deserialize, Serialize};

/// Nginx配置
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

/// Nginx状态响应
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

/// Nginx操作响应
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

/// Nginx代理配置
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
    /// 连接超时时间（秒）
    #[serde(default = "default_connect_timeout")]
    pub connect_timeout: u32,
    /// 发送超时时间（秒）
    #[serde(default = "default_send_timeout")]
    pub send_timeout: u32,
    /// 读取超时时间（秒）
    #[serde(default = "default_read_timeout")]
    pub read_timeout: u32,
    /// 启用长连接
    #[serde(default = "default_enable_keepalive")]
    pub enable_keepalive: bool,
    /// 长连接池大小
    #[serde(default = "default_keepalive_connections")]
    pub keepalive_connections: u32,
    /// worker进程数（auto表示自动）
    #[serde(default = "default_worker_processes")]
    pub worker_processes: String,
    /// 启用性能优化
    #[serde(default = "default_enable_performance")]
    pub enable_performance: bool,
}

fn default_connect_timeout() -> u32 {
    30
}
fn default_send_timeout() -> u32 {
    30
}
fn default_read_timeout() -> u32 {
    30
}
fn default_enable_keepalive() -> bool {
    true
}
fn default_keepalive_connections() -> u32 {
    32
}
fn default_worker_processes() -> String {
    String::from("auto")
}
fn default_enable_performance() -> bool {
    true
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
            connect_timeout: default_connect_timeout(),
            send_timeout: default_send_timeout(),
            read_timeout: default_read_timeout(),
            enable_keepalive: default_enable_keepalive(),
            keepalive_connections: default_keepalive_connections(),
            worker_processes: default_worker_processes(),
            enable_performance: default_enable_performance(),
        }
    }
}

/// Nginx配置保存请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NginxConfigSaveRequest {
    /// 代理配置
    pub proxy: NginxProxyConfig,
}

/// Nginx配置保存响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NginxConfigSaveResponse {
    /// 是否成功
    pub success: bool,
    /// 消息
    pub message: String,
    /// 是否需要重启
    pub need_restart: bool,
}

/// Nginx下载配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NginxDownloadConfig {
    /// 下载URL
    pub url: String,
    /// 解压目标目录
    pub target_dir: Option<String>,
}
