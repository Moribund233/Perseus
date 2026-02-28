/**
 * Redis 相关模型
 *
 * 定义 Redis 配置、状态、平台信息等数据结构
 */
use serde::{Deserialize, Serialize};

/// Redis配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisConfig {
    /// Redis可执行文件目录路径（Windows平台用于载入）
    pub exe_dir: Option<String>,
    /// 是否已载入/配置
    pub is_loaded: bool,
    /// 当前状态: stopped, running, error
    pub status: String,
    /// 版本信息
    pub version: Option<String>,
    /// 监听端口
    pub port: u16,
    /// 是否启用认证
    pub require_pass: bool,
    /// 认证密码
    pub password: Option<String>,
    /// 配置文件路径
    pub config_path: Option<String>,
    /// 数据目录路径
    pub data_dir: Option<String>,
    /// 是否作为Windows服务安装
    #[serde(default)]
    pub is_windows_service: bool,
}

impl Default for RedisConfig {
    fn default() -> Self {
        Self {
            exe_dir: None,
            is_loaded: false,
            status: String::from("stopped"),
            version: None,
            port: 6379,
            require_pass: false,
            password: None,
            config_path: None,
            data_dir: None,
            is_windows_service: false,
        }
    }
}

/// Redis状态响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisStatusResponse {
    /// 是否已载入/配置
    pub is_loaded: bool,
    /// 当前状态: stopped, running, error
    pub status: String,
    /// 版本信息
    pub version: Option<String>,
    /// 可执行文件目录路径
    pub exe_dir: Option<String>,
    /// 监听端口
    pub port: u16,
    /// 是否启用认证
    pub require_pass: bool,
    /// 配置文件路径
    pub config_path: Option<String>,
    /// 数据目录路径
    pub data_dir: Option<String>,
    /// 是否作为Windows服务安装
    pub is_windows_service: bool,
}

/// Redis操作响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisActionResponse {
    /// 是否成功
    pub success: bool,
    /// 消息
    pub message: String,
    /// 状态
    pub status: Option<String>,
}

/// Redis配置更新请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisConfigUpdateRequest {
    /// 监听端口
    pub port: Option<u16>,
    /// 是否启用认证
    pub require_pass: Option<bool>,
    /// 认证密码
    pub password: Option<String>,
    /// 数据目录路径
    pub data_dir: Option<String>,
}

/// Redis运行时配置项
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisRuntimeConfig {
    /// 配置项名称
    pub name: String,
    /// 配置项值
    pub value: String,
    /// 配置项描述
    pub description: String,
    /// 配置项类型
    pub config_type: String,
}

/// Redis运行时配置更新请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisRuntimeConfigUpdateRequest {
    /// 配置项名称
    pub name: String,
    /// 配置项值
    pub value: String,
}

/// Redis运行时配置批量更新请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisRuntimeConfigBatchUpdateRequest {
    /// 配置项列表
    pub configs: Vec<RedisRuntimeConfigUpdateRequest>,
}

/// Redis运行时配置响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisRuntimeConfigResponse {
    /// 是否成功
    pub success: bool,
    /// 消息
    pub message: String,
    /// 配置项列表
    pub configs: Vec<RedisRuntimeConfig>,
}

/// Redis运行时配置更新响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisRuntimeConfigUpdateResponse {
    /// 是否成功
    pub success: bool,
    /// 消息
    pub message: String,
    /// 已更新的配置项
    pub updated_configs: Vec<String>,
    /// 失败的配置项及原因
    pub failed_configs: Vec<(String, String)>,
}

/// Redis配置保存响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisConfigSaveResponse {
    /// 是否成功
    pub success: bool,
    /// 消息
    pub message: String,
    /// 配置是否已重新加载
    pub config_reloaded: bool,
}

/// Windows服务操作类型
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum WindowsServiceAction {
    Install,
    Uninstall,
}

/// Windows服务操作响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowsServiceResponse {
    /// 是否成功
    pub success: bool,
    /// 消息
    pub message: String,
    /// 服务是否已安装
    pub is_installed: bool,
}
