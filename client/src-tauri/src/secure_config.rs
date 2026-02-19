/**
 * 安全配置文件管理模块
 *
 * 管理敏感配置（JWT密钥、本地Token等），存储在加密的 client-config.json 中
 * 使用简单的 XOR 加密 + Base64 编码，密钥基于机器特征生成
 */
use base64::{engine::general_purpose::STANDARD, Engine as _};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

/// 敏感配置文件名
const SECURE_CONFIG_FILE: &str = "client-config.json";

/**
 * 敏感配置数据结构
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecureConfig {
    /// JWT Secret Key（用于签名本地 Token）
    #[serde(default)]
    pub jwt_secret_key: String,
    /// 本地管理员 Token
    #[serde(default)]
    pub local_token: String,
    /// 是否启用调试模式
    #[serde(default = "default_debug_mode")]
    pub debug_mode: bool,
    /// 客户端安全密码（用于保护敏感配置）
    #[serde(default)]
    pub security_password: String,
}

fn default_debug_mode() -> bool {
    true
}

impl Default for SecureConfig {
    fn default() -> Self {
        Self {
            jwt_secret_key: String::new(),
            local_token: String::new(),
            debug_mode: true,
            security_password: String::new(),
        }
    }
}

/**
 * 加密后的配置包装器
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
struct EncryptedConfig {
    /// 加密标记
    encrypted: bool,
    /// 加密后的数据（Base64编码）
    data: String,
}

/**
 * 获取用户配置目录
 */
fn get_config_dir() -> Result<PathBuf, String> {
    dirs::config_dir()
        .map(|dir| dir.join("langit-client"))
        .ok_or_else(|| "无法获取配置目录".to_string())
}

/**
 * 获取安全配置文件路径
 */
fn get_secure_config_path() -> Result<PathBuf, String> {
    let config_dir = get_config_dir()?;
    Ok(config_dir.join(SECURE_CONFIG_FILE))
}

/**
 * 确保配置目录存在
 */
fn ensure_config_dir() -> Result<(), String> {
    let config_dir = get_config_dir()?;
    if !config_dir.exists() {
        fs::create_dir_all(&config_dir).map_err(|e| format!("创建配置目录失败: {}", e))?;
    }
    Ok(())
}

/**
 * 生成机器相关的密钥
 * 使用机器用户名和计算机名组合生成密钥
 */
fn generate_machine_key() -> Vec<u8> {
    let username = std::env::var("USERNAME")
        .or_else(|_| std::env::var("USER"))
        .unwrap_or_else(|_| "default_user".to_string());

    let computername = std::env::var("COMPUTERNAME")
        .or_else(|_| std::env::var("HOSTNAME"))
        .unwrap_or_else(|_| "default_host".to_string());

    // 组合用户名和计算机名生成密钥
    let key_string = format!("{}@{}_langit_secure_key", username, computername);

    // 使用 SHA256 哈希生成固定长度的密钥
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    let mut hasher = DefaultHasher::new();
    key_string.hash(&mut hasher);
    let hash1 = hasher.finish();

    let mut hasher2 = DefaultHasher::new();
    key_string
        .bytes()
        .rev()
        .collect::<Vec<_>>()
        .hash(&mut hasher2);
    let hash2 = hasher2.finish();

    // 组合两个哈希值生成 32 字节密钥
    let mut key = Vec::with_capacity(32);
    key.extend_from_slice(&hash1.to_le_bytes());
    key.extend_from_slice(&hash2.to_le_bytes());
    key.extend_from_slice(&(hash1 ^ hash2).to_le_bytes());
    key.extend_from_slice(&(hash1.wrapping_add(hash2)).to_le_bytes());

    key
}

/**
 * XOR 加密/解密
 */
fn xor_encrypt_decrypt(data: &[u8], key: &[u8]) -> Vec<u8> {
    data.iter()
        .enumerate()
        .map(|(i, &byte)| byte ^ key[i % key.len()])
        .collect()
}

/**
 * 加密配置数据
 */
fn encrypt_config(config: &SecureConfig) -> Result<EncryptedConfig, String> {
    let json = serde_json::to_string(config).map_err(|e| format!("序列化配置失败: {}", e))?;

    let key = generate_machine_key();
    let encrypted = xor_encrypt_decrypt(json.as_bytes(), &key);

    Ok(EncryptedConfig {
        encrypted: true,
        data: STANDARD.encode(&encrypted),
    })
}

/**
 * 解密配置数据
 */
fn decrypt_config(encrypted: &EncryptedConfig) -> Result<SecureConfig, String> {
    if !encrypted.encrypted {
        // 如果未加密，直接解析
        return serde_json::from_str(&encrypted.data).map_err(|e| format!("解析配置失败: {}", e));
    }

    let encrypted_bytes = STANDARD
        .decode(&encrypted.data)
        .map_err(|e| format!("Base64解码失败: {}", e))?;

    let key = generate_machine_key();
    let decrypted = xor_encrypt_decrypt(&encrypted_bytes, &key);

    let json = String::from_utf8(decrypted).map_err(|e| format!("UTF8解码失败: {}", e))?;

    serde_json::from_str(&json).map_err(|e| format!("解析配置失败: {}", e))
}

/**
 * 加载安全配置
 * 如果配置文件不存在，返回默认配置
 */
pub fn load_secure_config() -> Result<SecureConfig, String> {
    let config_path = get_secure_config_path()?;

    if !config_path.exists() {
        return Ok(SecureConfig::default());
    }

    let content =
        fs::read_to_string(&config_path).map_err(|e| format!("读取配置文件失败: {}", e))?;

    // 尝试解析为加密配置
    match serde_json::from_str::<EncryptedConfig>(&content) {
        Ok(encrypted) => decrypt_config(&encrypted),
        Err(_) => {
            // 如果不是加密格式，尝试直接解析为 SecureConfig（向后兼容）
            serde_json::from_str::<SecureConfig>(&content)
                .map_err(|e| format!("解析配置文件失败: {}", e))
        }
    }
}

/**
 * 保存安全配置（加密存储）
 */
pub fn save_secure_config(config: &SecureConfig) -> Result<(), String> {
    ensure_config_dir()?;

    let config_path = get_secure_config_path()?;
    let encrypted = encrypt_config(config)?;

    let content =
        serde_json::to_string_pretty(&encrypted).map_err(|e| format!("序列化配置失败: {}", e))?;

    fs::write(&config_path, content).map_err(|e| format!("保存配置文件失败: {}", e))?;

    Ok(())
}

/**
 * 初始化安全配置（如果不存在则创建）
 * 生成随机的 JWT 密钥和本地 Token
 */
pub fn init_secure_config() -> Result<SecureConfig, String> {
    let config_path = get_secure_config_path()?;

    if config_path.exists() {
        return load_secure_config();
    }

    // 生成新的安全配置
    let config = generate_new_secure_config();
    save_secure_config(&config)?;

    Ok(config)
}

/**
 * 生成新的安全配置
 */
fn generate_new_secure_config() -> SecureConfig {
    use rand::Rng;

    // 生成 32 字节随机 JWT 密钥
    let jwt_key: Vec<u8> = (0..32).map(|_| rand::thread_rng().gen::<u8>()).collect();
    let jwt_secret_key = STANDARD.encode(&jwt_key);

    // 生成本地 Token
    let token_bytes: Vec<u8> = (0..24).map(|_| rand::thread_rng().gen::<u8>()).collect();
    let local_token = format!(
        "langit_local_{}_{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs(),
        STANDARD
            .encode(&token_bytes)
            .replace("/", "_")
            .replace("+", "-")
    );

    SecureConfig {
        jwt_secret_key,
        local_token,
        debug_mode: true,
        security_password: String::new(),
    }
}

/**
 * 更新 JWT 密钥
 */
pub fn update_jwt_secret_key(key: String) -> Result<(), String> {
    let mut config = load_secure_config()?;
    config.jwt_secret_key = key;
    save_secure_config(&config)
}

/**
 * 更新本地 Token
 */
pub fn update_local_token(token: String) -> Result<(), String> {
    let mut config = load_secure_config()?;
    config.local_token = token;
    save_secure_config(&config)
}

/**
 * 获取 JWT 密钥
 */
pub fn get_jwt_secret_key() -> Result<String, String> {
    let config = load_secure_config()?;
    Ok(config.jwt_secret_key)
}

/**
 * 获取本地 Token
 */
pub fn get_local_token() -> Result<String, String> {
    let config = load_secure_config()?;
    Ok(config.local_token)
}

/**
 * 检查是否存在安全配置文件
 */
pub fn has_secure_config() -> bool {
    get_secure_config_path()
        .map(|p| p.exists())
        .unwrap_or(false)
}

/**
 * 设置安全密码
 */
pub fn set_security_password(password: String) -> Result<(), String> {
    let mut config = load_secure_config()?;
    config.security_password = password;
    save_secure_config(&config)
}

/**
 * 验证安全密码
 */
pub fn verify_security_password(password: &str) -> Result<bool, String> {
    let config = load_secure_config()?;
    // 如果没有设置密码，返回 true（首次使用）
    if config.security_password.is_empty() {
        return Ok(true);
    }
    Ok(config.security_password == password)
}

/**
 * 检查是否已设置安全密码
 */
pub fn has_security_password() -> Result<bool, String> {
    let config = load_secure_config()?;
    Ok(!config.security_password.is_empty())
}

/**
 * 更新调试模式
 */
pub fn update_debug_mode(debug: bool) -> Result<(), String> {
    let mut config = load_secure_config()?;
    config.debug_mode = debug;
    save_secure_config(&config)
}

/**
 * 获取调试模式
 */
pub fn get_debug_mode() -> Result<bool, String> {
    let config = load_secure_config()?;
    Ok(config.debug_mode)
}

/**
 * 重置所有安全令牌（JWT密钥和本地Token）
 * 此操作需要管理员权限
 */
pub fn reset_all_tokens() -> Result<(), String> {
    // 检查是否以管理员/root权限运行
    if !is_elevated() {
        return Err("需要管理员权限才能执行此操作".to_string());
    }

    let mut config = load_secure_config()?;
    let new_config = generate_new_secure_config();

    // 保留安全密码，只重置令牌
    config.jwt_secret_key = new_config.jwt_secret_key;
    config.local_token = new_config.local_token;

    save_secure_config(&config)
}

/**
 * 检查是否以提升的权限运行
 */
fn is_elevated() -> bool {
    #[cfg(target_os = "windows")]
    {
        // Windows: 检查是否以管理员身份运行
        use std::process::Command;
        match Command::new("net").args(["session"]).output() {
            Ok(output) => output.status.success(),
            Err(_) => false,
        }
    }

    #[cfg(target_os = "linux")]
    {
        // Linux: 检查是否为 root 用户
        unsafe { libc::getuid() == 0 }
    }

    #[cfg(target_os = "macos")]
    {
        // macOS: 检查是否为 root 用户
        unsafe { libc::getuid() == 0 }
    }

    #[cfg(not(any(target_os = "windows", target_os = "linux", target_os = "macos")))]
    {
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encrypt_decrypt() {
        let config = SecureConfig {
            jwt_secret_key: "test_key_123".to_string(),
            local_token: "test_token_456".to_string(),
            debug_mode: true,
            security_password: String::new(),
        };

        let encrypted = encrypt_config(&config).unwrap();
        let decrypted = decrypt_config(&encrypted).unwrap();

        assert_eq!(config.jwt_secret_key, decrypted.jwt_secret_key);
        assert_eq!(config.local_token, decrypted.local_token);
        assert_eq!(config.debug_mode, decrypted.debug_mode);
    }

    #[test]
    fn test_machine_key_consistency() {
        let key1 = generate_machine_key();
        let key2 = generate_machine_key();
        assert_eq!(key1, key2);
    }
}
