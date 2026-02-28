/**
 * 数据模型定义模块
 *
 * 定义与后端 API 交互的数据结构
 */
// 子模块
pub mod config;
pub mod database;
pub mod log;
pub mod nginx;
pub mod redis;
pub mod service;
pub mod system;

// 重新导出常用类型 - 配置相关
pub use config::{
    AdvancedConfig, AppearanceConfig, AppearanceSettings, ClientConfig, LocalAuthConfig, LogConfig,
    NotificationConfig, NotificationSettings, PlatformInfo, PlatformType, ServerConfig,
    ServerPathConfig, ServerSettings,
};

// 重新导出常用类型 - 数据库相关
pub use database::{
    CheckResult, CheckSummary, DatabaseSwitchRequest, DatabaseSwitchResponse, MigrationError,
    MigrationRequest, MigrationResponse, PrecheckRequest, PrecheckResponse, SyncDetails,
    TableProgress,
};

// 重新导出常用类型 - 日志相关
pub use log::{LogCleanupResponse, LogContentResponse, LogFileInfo, LogInfoResponse};

// 重新导出常用类型 - Nginx相关
pub use nginx::{
    NginxActionResponse, NginxConfig, NginxConfigSaveRequest, NginxConfigSaveResponse,
    NginxDownloadConfig, NginxProxyConfig, NginxStatusResponse,
};

// 重新导出常用类型 - Redis相关
pub use redis::{
    RedisActionResponse, RedisConfig, RedisConfigSaveResponse, RedisConfigUpdateRequest,
    RedisStatusResponse, WindowsServiceAction, WindowsServiceResponse,
};

// 重新导出常用类型 - 服务相关
pub use service::{
    ActionResponse, ConfigResponse, ConfigUpdateRequest, GitCheckResult, GitOperations,
    PerformanceData, RequestStats, ServerCheckResult, ServerProcessInfo, ServiceStatus,
    TcpTestResult,
};

// 重新导出常用类型 - 系统相关
pub use system::{NetworkInfo, SystemInfo};
