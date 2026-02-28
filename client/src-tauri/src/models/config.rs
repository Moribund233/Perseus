/**
 * 配置相关模型
 *
 * 定义客户端配置、认证配置、服务器配置等数据结构
 */
use serde::{Deserialize, Serialize};

use super::nginx::NginxConfig;
use super::redis::RedisConfig;

/// 平台类型
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum PlatformType {
    Windows,
    Linux,
    MacOS,
    Other,
}

impl Default for PlatformType {
    fn default() -> Self {
        match std::env::consts::OS {
            "windows" => PlatformType::Windows,
            "linux" => PlatformType::Linux,
            "macos" => PlatformType::MacOS,
            _ => PlatformType::Other,
        }
    }
}

impl PlatformType {
    /// 检查是否为Windows平台
    pub fn is_windows(&self) -> bool {
        matches!(self, PlatformType::Windows)
    }

    /// 检查是否为Linux平台
    pub fn is_linux(&self) -> bool {
        matches!(self, PlatformType::Linux)
    }

    /// 检查是否为macOS平台
    pub fn is_macos(&self) -> bool {
        matches!(self, PlatformType::MacOS)
    }

    /// 获取平台名称字符串
    pub fn as_str(&self) -> &'static str {
        match self {
            PlatformType::Windows => "windows",
            PlatformType::Linux => "linux",
            PlatformType::MacOS => "macos",
            PlatformType::Other => "other",
        }
    }
}

/// 平台信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlatformInfo {
    /// 平台类型
    #[serde(default)]
    pub platform_type: PlatformType,
    /// 是否支持手动载入（Windows平台）
    #[serde(default)]
    pub supports_manual_load: bool,
    /// 是否支持下载（Windows平台，用于Nginx）
    #[serde(default)]
    pub supports_download: bool,
    /// 是否使用包管理器（Linux平台）
    #[serde(default)]
    pub uses_package_manager: bool,
    /// 包管理器类型: apt, yum, dnf, pacman, apk等
    pub package_manager: Option<String>,
    /// Nginx版本（通过包管理器获取，Linux）
    pub nginx_package_version: Option<String>,
    /// Nginx配置文件路径（Linux系统路径）
    pub nginx_config_path: Option<String>,
    /// Redis版本（通过包管理器获取，Linux）
    pub redis_package_version: Option<String>,
    /// Redis配置文件路径（Linux系统路径）
    pub redis_config_path: Option<String>,
}

impl Default for PlatformInfo {
    fn default() -> Self {
        let platform_type = PlatformType::default();
        Self {
            platform_type: platform_type.clone(),
            supports_manual_load: platform_type.is_windows(),
            supports_download: platform_type.is_windows(),
            uses_package_manager: platform_type.is_linux(),
            package_manager: None,
            nginx_package_version: None,
            nginx_config_path: None,
            redis_package_version: None,
            redis_config_path: None,
        }
    }
}

impl PlatformInfo {
    /// 检测Linux包管理器
    pub fn detect_package_manager() -> Option<String> {
        let managers = vec![
            ("/usr/bin/apt", "apt"),
            ("/usr/bin/apt-get", "apt"),
            ("/usr/bin/yum", "yum"),
            ("/usr/bin/dnf", "dnf"),
            ("/usr/bin/pacman", "pacman"),
            ("/sbin/apk", "apk"),
        ];

        for (path, name) in managers {
            if std::path::Path::new(path).exists() {
                return Some(name.to_string());
            }
        }

        None
    }

    /// 检测Nginx配置文件路径
    pub fn detect_nginx_config_path() -> Option<String> {
        let common_paths = vec![
            "/etc/nginx/nginx.conf",
            "/usr/local/nginx/conf/nginx.conf",
            "/opt/nginx/conf/nginx.conf",
        ];

        for path in common_paths {
            if std::path::Path::new(path).exists() {
                return Some(path.to_string());
            }
        }

        None
    }

    /// 检测Redis配置文件路径
    pub fn detect_redis_config_path() -> Option<String> {
        let common_paths = vec![
            "/etc/redis/redis.conf",
            "/etc/redis.conf",
            "/usr/local/etc/redis.conf",
            "/opt/redis/redis.conf",
        ];

        for path in common_paths {
            if std::path::Path::new(path).exists() {
                return Some(path.to_string());
            }
        }

        None
    }

    /// 获取Linux系统上Nginx的版本
    pub fn detect_nginx_version() -> Option<String> {
        use std::process::Command;

        if let Ok(output) = Command::new("nginx").arg("-v").output() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            let stdout = String::from_utf8_lossy(&output.stdout);

            let version_info = if stderr.contains("nginx") {
                stderr.to_string()
            } else if stdout.contains("nginx") {
                stdout.to_string()
            } else {
                return None;
            };

            return version_info.lines().next().map(|s| s.trim().to_string());
        }

        None
    }

    /// 获取Linux系统上Redis的版本
    pub fn detect_redis_version() -> Option<String> {
        use std::process::Command;

        if let Ok(output) = Command::new("redis-server").arg("--version").output() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let stderr = String::from_utf8_lossy(&output.stderr);

            let version_info = if stdout.contains("Redis") {
                stdout.to_string()
            } else if stderr.contains("Redis") {
                stderr.to_string()
            } else {
                return None;
            };

            return version_info.lines().next().map(|s| s.trim().to_string());
        }

        None
    }

    /// 检测并填充平台信息
    pub fn detect() -> Self {
        let platform_type = PlatformType::default();

        if platform_type.is_linux() {
            Self {
                platform_type: platform_type.clone(),
                supports_manual_load: false,
                supports_download: false,
                uses_package_manager: true,
                package_manager: Self::detect_package_manager(),
                nginx_package_version: Self::detect_nginx_version(),
                nginx_config_path: Self::detect_nginx_config_path(),
                redis_package_version: Self::detect_redis_version(),
                redis_config_path: Self::detect_redis_config_path(),
            }
        } else {
            Self::default()
        }
    }
}

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
#[derive(Debug, Clone, Serialize, Deserialize)]
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
    /// 平台信息（启动时自动检测）
    #[serde(default)]
    pub platform: PlatformInfo,
    /// 认证令牌（保留用于向后兼容，建议迁移到加密存储）
    #[serde(default)]
    pub auth_token: Option<String>,
    /// Nginx配置
    #[serde(default)]
    pub nginx: NginxConfig,
    /// Redis配置
    #[serde(default)]
    pub redis: RedisConfig,
    /// 数据库类型（sqlite/postgresql/mysql）
    #[serde(default = "default_db_type")]
    pub db_type: String,
}

impl Default for ClientConfig {
    fn default() -> Self {
        Self {
            server: ServerConfig::default(),
            appearance: AppearanceConfig::default(),
            notification: NotificationConfig::default(),
            log: LogConfig::default(),
            advanced: AdvancedConfig::default(),
            platform: PlatformInfo::detect(),
            auth_token: None,
            nginx: NginxConfig::default(),
            redis: RedisConfig::default(),
            db_type: default_db_type(),
        }
    }
}

fn default_db_type() -> String {
    "sqlite".to_string()
}
