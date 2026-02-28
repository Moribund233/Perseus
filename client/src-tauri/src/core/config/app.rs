/**
 * 配置管理模块
 *
 * 管理客户端本地配置，支持从 client.toml 文件读取配置
 *
 */
use std::fs;
use std::path::PathBuf;

use crate::models::ClientConfig;

use super::secure as secure_config;

/// 配置文件名（新版 TOML 格式）- 非敏感配置
const CONFIG_FILE_NAME_TOML: &str = "client.toml";

/// 获取用户配置目录
fn get_config_dir() -> Result<PathBuf, String> {
    dirs::config_dir()
        .map(|dir| dir.join("langit-client"))
        .ok_or_else(|| "无法获取配置目录".to_string())
}

/// 获取用户配置目录中的 TOML 配置文件路径
fn get_user_config_path() -> Result<PathBuf, String> {
    let config_dir = get_config_dir()?;
    Ok(config_dir.join(CONFIG_FILE_NAME_TOML))
}

/// 获取应用程序所在目录的 client.toml 路径（便携模式 - 仅非敏感配置）
fn get_app_dir_config_path() -> Option<PathBuf> {
    std::env::current_exe()
        .ok()?
        .parent()
        .map(|dir| dir.join(CONFIG_FILE_NAME_TOML))
}

/// 确保用户配置目录存在
fn ensure_config_dir() -> Result<(), String> {
    let config_dir = get_config_dir()?;
    if !config_dir.exists() {
        fs::create_dir_all(&config_dir).map_err(|e| format!("创建配置目录失败: {}", e))?;
    }
    Ok(())
}

/// 从 TOML 文件加载配置
fn load_config_from_toml(path: &PathBuf) -> Result<ClientConfig, String> {
    let content = fs::read_to_string(path).map_err(|e| format!("读取 TOML 配置文件失败: {}", e))?;
    let config: ClientConfig =
        toml::from_str(&content).map_err(|e| format!("解析 TOML 配置文件失败: {}", e))?;
    Ok(config)
}

/// 合并两个配置
///
/// 合并规则：
/// - app_dir 配置用于非敏感配置
/// - user 配置覆盖非敏感配置
fn merge_configs(
    user_config: Option<ClientConfig>,
    app_dir_config: Option<ClientConfig>,
) -> ClientConfig {
    let mut result = ClientConfig::default();

    // 如果有 app_dir 配置，先使用它的值（非敏感配置）
    if let Some(app) = app_dir_config {
        result.server = app.server;
        result.appearance = app.appearance;
        result.notification = app.notification;
        result.log = app.log;
        result.advanced = app.advanced;
        result.nginx = app.nginx;
        result.redis = app.redis;
        result.db_type = app.db_type;
    }

    // 如果有用户配置，使用它的值（覆盖非敏感配置）
    if let Some(user) = user_config {
        result.server = user.server;
        result.appearance = user.appearance;
        result.notification = user.notification;
        result.log = user.log;
        result.advanced = user.advanced;
        result.nginx = user.nginx;
        result.redis = user.redis;
        result.db_type = user.db_type;
    }

    result
}

/// 加载客户端配置
///
/// 配置加载优先级：
/// 1. 用户配置目录中的 client.toml (非敏感配置)
/// 2. 应用程序目录中的 client.toml (非敏感配置, 便携模式)
/// 3. 默认配置
///
/// 敏感配置（JWT密钥、Token）从加密的 client-config.json 加载
pub fn load_config() -> Result<ClientConfig, String> {
    // 1. 尝试从用户配置目录加载 TOML
    let user_config = if let Ok(user_path) = get_user_config_path() {
        if user_path.exists() {
            load_config_from_toml(&user_path).ok()
        } else {
            None
        }
    } else {
        None
    };

    // 2. 尝试从应用程序目录加载 TOML（仅用于非敏感配置）
    let app_dir_config = if let Some(app_path) = get_app_dir_config_path() {
        if app_path.exists() && app_path != get_user_config_path().unwrap_or_default() {
            load_config_from_toml(&app_path).ok()
        } else {
            None
        }
    } else {
        None
    };

    // 如果任一配置存在，合并它们
    if user_config.is_some() || app_dir_config.is_some() {
        return Ok(merge_configs(user_config, app_dir_config));
    }

    // 3. 返回默认配置
    Ok(ClientConfig::default())
}

/// 保存客户端配置到 TOML 文件（用户配置目录）
///
/// 注意：此函数只保存非敏感配置，敏感配置保存在加密的 client-config.json 中
pub fn save_config(config: &ClientConfig) -> Result<(), String> {
    ensure_config_dir()?;

    let config_path = get_user_config_path()?;

    // 创建用于保存的配置（不包含敏感信息）
    let config_to_save = config.clone();

    let content =
        toml::to_string_pretty(&config_to_save).map_err(|e| format!("序列化配置失败: {}", e))?;

    fs::write(&config_path, content).map_err(|e| format!("保存配置文件失败: {}", e))?;

    Ok(())
}

/// 更新服务端地址
pub fn update_server_url(url: String) -> Result<(), String> {
    let mut config = load_config()?;
    config.server.url = url;
    save_config(&config)
}

/// 更新服务器配置
pub fn update_server_config(server_config: crate::models::ServerConfig) -> Result<(), String> {
    let mut config = load_config()?;
    config.server = server_config;
    save_config(&config)
}

/// 更新外观配置
pub fn update_appearance_config(
    appearance_config: crate::models::AppearanceConfig,
) -> Result<(), String> {
    let mut config = load_config()?;
    config.appearance = appearance_config;
    save_config(&config)
}

/// 更新通知配置
pub fn update_notification_config(
    notification_config: crate::models::NotificationConfig,
) -> Result<(), String> {
    let mut config = load_config()?;
    config.notification = notification_config;
    save_config(&config)
}

/// 更新认证令牌
pub fn update_auth_token(token: Option<String>) -> Result<(), String> {
    let mut config = load_config()?;
    config.auth_token = token;
    save_config(&config)
}

/// 获取服务端地址
pub fn get_server_url() -> Result<String, String> {
    let config = load_config()?;
    Ok(config.server.url)
}

/// 获取认证令牌
pub fn get_auth_token() -> Result<Option<String>, String> {
    let config = load_config()?;
    Ok(config.auth_token)
}

/// 检查是否存在 client.toml 配置文件（用户配置目录）
pub fn has_user_config() -> bool {
    get_user_config_path().map(|p| p.exists()).unwrap_or(false)
}

/// 获取用户配置文件路径
pub fn get_config_path() -> Option<PathBuf> {
    get_user_config_path().ok()
}

/// 检查是否存在 client.toml 配置文件（应用程序目录）
pub fn has_app_dir_config() -> bool {
    get_app_dir_config_path()
        .map(|p| p.exists())
        .unwrap_or(false)
}

/// 初始化默认配置文件（如果不存在）
///
/// 注意：敏感配置只保存在加密的 client-config.json 中
pub fn init_default_config() -> Result<(), String> {
    if !has_user_config() {
        let default_config = ClientConfig::default();
        save_config(&default_config)?;
    }
    Ok(())
}

// ==================== 安全配置包装函数 ====================

/**
 * 初始化安全配置（如果不存在则创建）
 * 生成随机的 JWT 密钥和本地 Token，加密存储
 */
pub fn init_secure_config() -> Result<secure_config::SecureConfig, String> {
    secure_config::init_secure_config()
}

/**
 * 加载安全配置
 */
pub fn load_secure_config() -> Result<secure_config::SecureConfig, String> {
    secure_config::load_secure_config()
}

/**
 * 保存安全配置
 */
pub fn save_secure_config(config: &secure_config::SecureConfig) -> Result<(), String> {
    secure_config::save_secure_config(config)
}

/**
 * 获取 JWT 密钥
 */
pub fn get_jwt_secret_key() -> Result<String, String> {
    secure_config::get_jwt_secret_key()
}

/**
 * 获取本地 Token
 */
pub fn get_local_token() -> Result<String, String> {
    secure_config::get_local_token()
}

/**
 * 更新 JWT 密钥
 */
pub fn update_jwt_secret_key(key: String) -> Result<(), String> {
    secure_config::update_jwt_secret_key(key)
}

/**
 * 更新本地 Token
 */
pub fn update_local_token(token: String) -> Result<(), String> {
    secure_config::update_local_token(token)
}

/**
 * 检查是否存在安全配置文件
 */
pub fn has_secure_config() -> bool {
    secure_config::has_secure_config().unwrap_or(false)
}
