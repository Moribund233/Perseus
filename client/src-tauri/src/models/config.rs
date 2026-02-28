/**
 * 配置相关模型
 *
 * 定义客户端配置、认证配置、服务器配置等数据结构
 */
use serde::{Deserialize, Serialize};

use super::nginx::NginxConfig;

/// 应用配置（旧版，用于向后兼容）
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

/// 服务端路径配置
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

/// 服务器配置
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

/// 外观配置
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

/// 通知配置
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

/// 日志配置
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

/// 高级配置
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
    /// 数据库类型（sqlite/postgresql/mysql）
    #[serde(default = "default_db_type")]
    pub db_type: String,
}

fn default_db_type() -> String {
    "sqlite".to_string()
}
