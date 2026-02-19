/**
 * 本地认证管理模块
 *
 * 管理 Client 与服务端之间的本地认证：
 * 1. 生成和管理 JWT Secret Key
 * 2. 生成本地管理员 Token
 * 3. 为 API 请求提供认证头
 *
 */
use rand::{distributions::Alphanumeric, Rng};
use std::time::{SystemTime, UNIX_EPOCH};

use crate::secure_config::{self, SecureConfig};

/// 本地认证请求头名
pub const LOCAL_AUTH_HEADER: &str = "X-LanGit-Local";
/// 本地认证请求头值
pub const LOCAL_AUTH_HEADER_VALUE: &str = "1";

/**
 * 本地认证配置（用于向后兼容）
 * 实际数据存储在加密的 client-config.json 中
 */
#[derive(Debug, Clone)]
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

impl From<SecureConfig> for LocalAuthConfig {
    fn from(config: SecureConfig) -> Self {
        Self {
            jwt_secret_key: config.jwt_secret_key,
            local_token: config.local_token,
            debug_mode: config.debug_mode,
        }
    }
}

/// 生成随机字符串（用于 Secret Key 或 Token）
fn generate_random_string(length: usize) -> String {
    rand::thread_rng()
        .sample_iter(&Alphanumeric)
        .take(length)
        .map(char::from)
        .collect()
}

/// 生成 JWT Secret Key
pub fn generate_jwt_secret_key() -> String {
    // 生成 32 字节的安全随机字符串（Base64 URL Safe）
    use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine as _};

    let key_bytes: Vec<u8> = rand::thread_rng()
        .sample_iter(&rand::distributions::Standard)
        .take(32)
        .collect();
    URL_SAFE_NO_PAD.encode(&key_bytes)
}

/// 生成本地管理员 Token
/// 格式: langit_local_<timestamp>_<random>
pub fn generate_local_token() -> String {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let random = generate_random_string(16);
    format!("langit_local_{}_{}", timestamp, random)
}

/// 初始化本地认证配置
///
/// 如果配置中不存在 JWT 密钥和 Token，则生成新的
/// 注意：此函数不会覆盖已存在的密钥和 Token
/// 敏感配置存储在加密的 client-config.json 中
pub fn init_local_auth() -> Result<LocalAuthConfig, String> {
    // 初始化安全配置（如果不存在则创建）
    let secure_config = secure_config::init_secure_config()?;

    // 检查是否需要生成新的密钥
    let need_new_key = secure_config.jwt_secret_key.is_empty();
    let need_new_token = secure_config.local_token.is_empty();

    if need_new_key || need_new_token {
        let mut new_config = secure_config;

        if need_new_key {
            new_config.jwt_secret_key = generate_jwt_secret_key();
            log::info!("已生成新的 JWT Secret Key");
        }

        if need_new_token {
            new_config.local_token = generate_local_token();
            log::info!("已生成新的本地管理员 Token");
        }

        // 保存到加密配置
        secure_config::save_secure_config(&new_config)?;

        Ok(LocalAuthConfig::from(new_config))
    } else {
        Ok(LocalAuthConfig::from(secure_config))
    }
}

/// 获取当前本地认证配置
/// 从加密的 client-config.json 加载
pub fn get_local_auth_config() -> Result<LocalAuthConfig, String> {
    let secure_config = secure_config::load_secure_config()?;
    Ok(LocalAuthConfig::from(secure_config))
}

/// 获取本地认证请求头
/// 用于 API 请求时添加认证信息
pub fn get_auth_headers() -> Result<Vec<(String, String)>, String> {
    let auth_config = get_local_auth_config()?;

    log::debug!(
        "获取本地认证头 - Token 长度: {}",
        auth_config.local_token.len()
    );

    if auth_config.local_token.is_empty() {
        log::warn!("本地认证 Token 未初始化");
        return Err("本地认证 Token 未初始化".to_string());
    }

    log::debug!("本地认证头生成成功");
    Ok(vec![
        (
            "Authorization".to_string(),
            format!("Bearer {}", auth_config.local_token),
        ),
        (
            LOCAL_AUTH_HEADER.to_string(),
            LOCAL_AUTH_HEADER_VALUE.to_string(),
        ),
    ])
}

/// 获取用于启动服务端的环境变量
pub fn get_server_env_vars() -> Result<Vec<(String, String)>, String> {
    let auth_config = get_local_auth_config()?;

    if auth_config.jwt_secret_key.is_empty() || auth_config.local_token.is_empty() {
        return Err("本地认证配置未初始化，请先调用 init_local_auth()".to_string());
    }

    Ok(vec![
        (
            "LANGIT_SECURITY_SECRET_KEY".to_string(),
            auth_config.jwt_secret_key.clone(),
        ),
        (
            "LANGIT_LOCAL_TOKEN".to_string(),
            auth_config.local_token.clone(),
        ),
        (
            "LANGIT_APP_DEBUG".to_string(),
            auth_config.debug_mode.to_string(),
        ),
    ])
}

/// 重新生成本地认证凭证
///
/// 用于安全重置或首次设置
/// 警告：此函数会强制覆盖已存在的 JWT 密钥和 Token
pub fn regenerate_credentials() -> Result<LocalAuthConfig, String> {
    let new_config = SecureConfig {
        jwt_secret_key: generate_jwt_secret_key(),
        local_token: generate_local_token(),
        debug_mode: true,
        security_password: String::new(),
    };

    // 保存到加密配置
    secure_config::save_secure_config(&new_config)?;

    log::info!("已重新生成本地认证凭证");
    Ok(LocalAuthConfig::from(new_config))
}

/// 设置调试模式
///
/// 修改后会保存配置，但不会覆盖已存在的 JWT 密钥和 Token
/// 注意：修改 debug_mode 后需要重启客户端才能生效（环境变量注入）
pub fn set_debug_mode(debug: bool) -> Result<(), String> {
    let mut secure_config = secure_config::load_secure_config()?;
    secure_config.debug_mode = debug;
    secure_config::save_secure_config(&secure_config)?;
    log::info!("调试模式已设置为: {}", debug);
    Ok(())
}

/// 检查本地认证是否已初始化
pub fn is_initialized() -> Result<bool, String> {
    let auth_config = get_local_auth_config()?;
    Ok(!auth_config.jwt_secret_key.is_empty() && !auth_config.local_token.is_empty())
}
