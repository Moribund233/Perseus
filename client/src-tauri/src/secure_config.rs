/**
 * 安全配置文件管理模块
 *
 * 管理敏感配置（JWT密钥、本地Token等），存储在加密的 client-config.json 中
 * 使用 AES-256-GCM 加密，密钥基于机器特征和 PBKDF2 派生
 */
use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use base64::{engine::general_purpose::STANDARD, Engine as _};
use pbkdf2::pbkdf2_hmac;
use serde::{Deserialize, Serialize};
use sha2::Sha256;
use std::fs;
use std::path::PathBuf;

/// 敏感配置文件名
const SECURE_CONFIG_FILE: &str = "client-config.json";
/// 加密版本号，用于向后兼容
const CURRENT_ENCRYPTION_VERSION: u32 = 2;
/// PBKDF2 迭代次数
const PBKDF2_ITERATIONS: u32 = 100_000;
/// 盐值长度
const SALT_LENGTH: usize = 32;
/// Nonce 长度
const NONCE_LENGTH: usize = 12;

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
    /// 密钥版本（用于轮换）
    #[serde(default)]
    pub key_version: u32,
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
            key_version: 0,
        }
    }
}

/**
 * 加密后的配置包装器
 */
#[derive(Debug, Clone, Serialize, Deserialize)]
struct EncryptedConfig {
    /// 加密版本号
    version: u32,
    /// 加密标记
    encrypted: bool,
    /// 加密后的数据（Base64编码）
    data: String,
    /// 盐值（Base64编码）
    salt: String,
    /// Nonce（Base64编码）
    nonce: String,
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
 * 生成机器相关的原始密钥材料
 * 使用机器用户名、计算机名和硬件信息组合
 */
fn generate_machine_key_material() -> Vec<u8> {
    let username = std::env::var("USERNAME")
        .or_else(|_| std::env::var("USER"))
        .unwrap_or_else(|_| "default_user".to_string());

    let computername = std::env::var("COMPUTERNAME")
        .or_else(|_| std::env::var("HOSTNAME"))
        .unwrap_or_else(|_| "default_host".to_string());

    // 获取系统临时目录路径作为额外的机器特征
    let temp_dir = std::env::var("TEMP")
        .or_else(|_| std::env::var("TMP"))
        .unwrap_or_else(|_| "/tmp".to_string());

    // 组合多个机器特征
    let key_material = format!(
        "{}@{}_{}_langit_secure_key_v2",
        username, computername, temp_dir
    );

    // 使用 SHA256 生成固定长度的密钥材料
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(key_material.as_bytes());
    hasher.finalize().to_vec()
}

/**
 * 使用 PBKDF2 派生加密密钥
 */
fn derive_key(key_material: &[u8], salt: &[u8]) -> Vec<u8> {
    let mut key = vec![0u8; 32]; // AES-256 需要 32 字节密钥
    pbkdf2_hmac::<Sha256>(key_material, salt, PBKDF2_ITERATIONS, &mut key);
    key
}

/**
 * 生成随机盐值
 */
fn generate_salt() -> Vec<u8> {
    use rand::Rng;
    (0..SALT_LENGTH)
        .map(|_| rand::thread_rng().gen::<u8>())
        .collect()
}

/**
 * 生成随机 Nonce
 */
fn generate_nonce() -> Vec<u8> {
    use rand::Rng;
    (0..NONCE_LENGTH)
        .map(|_| rand::thread_rng().gen::<u8>())
        .collect()
}

/**
 * 使用 AES-256-GCM 加密数据
 */
fn aes_gcm_encrypt(plaintext: &[u8], key: &[u8], nonce: &[u8]) -> Result<Vec<u8>, String> {
    let cipher = Aes256Gcm::new_from_slice(key).map_err(|e| format!("创建加密器失败: {:?}", e))?;

    let nonce = Nonce::from_slice(nonce);

    cipher
        .encrypt(nonce, plaintext)
        .map_err(|e| format!("加密失败: {:?}", e))
}

/**
 * 使用 AES-256-GCM 解密数据
 */
fn aes_gcm_decrypt(ciphertext: &[u8], key: &[u8], nonce: &[u8]) -> Result<Vec<u8>, String> {
    let cipher = Aes256Gcm::new_from_slice(key).map_err(|e| format!("创建解密器失败: {:?}", e))?;

    let nonce = Nonce::from_slice(nonce);

    cipher
        .decrypt(nonce, ciphertext)
        .map_err(|e| format!("解密失败: {:?}", e))
}

/**
 * 使用 AES-256-GCM 加密配置数据
 */
fn encrypt_config(config: &SecureConfig) -> Result<EncryptedConfig, String> {
    let json = serde_json::to_string(config).map_err(|e| format!("序列化配置失败: {}", e))?;

    // 生成随机盐值和 nonce
    let salt = generate_salt();
    let nonce = generate_nonce();

    // 派生加密密钥
    let key_material = generate_machine_key_material();
    let key = derive_key(&key_material, &salt);

    // 加密数据
    let encrypted = aes_gcm_encrypt(json.as_bytes(), &key, &nonce)?;

    Ok(EncryptedConfig {
        version: CURRENT_ENCRYPTION_VERSION,
        encrypted: true,
        data: STANDARD.encode(&encrypted),
        salt: STANDARD.encode(&salt),
        nonce: STANDARD.encode(&nonce),
    })
}

/**
 * 使用 AES-256-GCM 解密配置数据
 */
fn decrypt_config(encrypted: &EncryptedConfig) -> Result<SecureConfig, String> {
    // 检查版本号
    if encrypted.version != CURRENT_ENCRYPTION_VERSION {
        return Err(format!(
            "不支持的加密版本: {}，当前支持版本: {}",
            encrypted.version, CURRENT_ENCRYPTION_VERSION
        ));
    }

    if !encrypted.encrypted {
        // 如果未加密，直接解析
        return serde_json::from_str(&encrypted.data).map_err(|e| format!("解析配置失败: {}", e));
    }

    // 解码数据
    let encrypted_bytes = STANDARD
        .decode(&encrypted.data)
        .map_err(|e| format!("Base64解码失败: {}", e))?;
    let salt = STANDARD
        .decode(&encrypted.salt)
        .map_err(|e| format!("盐值解码失败: {}", e))?;
    let nonce = STANDARD
        .decode(&encrypted.nonce)
        .map_err(|e| format!("Nonce解码失败: {}", e))?;

    // 派生解密密钥
    let key_material = generate_machine_key_material();
    let key = derive_key(&key_material, &salt);

    // 解密数据
    let decrypted = aes_gcm_decrypt(&encrypted_bytes, &key, &nonce)?;

    let json = String::from_utf8(decrypted).map_err(|e| format!("UTF8解码失败: {}", e))?;

    serde_json::from_str(&json).map_err(|e| format!("解析配置失败: {}", e))
}

/**
 * 使用旧版 XOR 解密（向后兼容）
 */
fn decrypt_config_legacy(encrypted: &EncryptedConfig) -> Result<SecureConfig, String> {
    // XOR 解密实现（保留用于迁移）
    fn xor_encrypt_decrypt(data: &[u8], key: &[u8]) -> Vec<u8> {
        data.iter()
            .enumerate()
            .map(|(i, &byte)| byte ^ key[i % key.len()])
            .collect()
    }

    fn generate_machine_key_legacy() -> Vec<u8> {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let username = std::env::var("USERNAME")
            .or_else(|_| std::env::var("USER"))
            .unwrap_or_else(|_| "default_user".to_string());

        let computername = std::env::var("COMPUTERNAME")
            .or_else(|_| std::env::var("HOSTNAME"))
            .unwrap_or_else(|_| "default_host".to_string());

        let key_string = format!("{}@{}_langit_secure_key", username, computername);

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

        let mut key = Vec::with_capacity(32);
        key.extend_from_slice(&hash1.to_le_bytes());
        key.extend_from_slice(&hash2.to_le_bytes());
        key.extend_from_slice(&(hash1 ^ hash2).to_le_bytes());
        key.extend_from_slice(&(hash1.wrapping_add(hash2)).to_le_bytes());

        key
    }

    let encrypted_bytes = STANDARD
        .decode(&encrypted.data)
        .map_err(|e| format!("Base64解码失败: {}", e))?;

    let key = generate_machine_key_legacy();
    let decrypted = xor_encrypt_decrypt(&encrypted_bytes, &key);

    let json = String::from_utf8(decrypted).map_err(|e| format!("UTF8解码失败: {}", e))?;

    serde_json::from_str(&json).map_err(|e| format!("解析配置失败: {}", e))
}

/**
 * 加载安全配置
 * 如果配置文件不存在，返回默认配置
 * 支持自动迁移旧版加密配置
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
        Ok(encrypted) => {
            // 根据版本号选择解密方式
            if encrypted.version == CURRENT_ENCRYPTION_VERSION {
                decrypt_config(&encrypted)
            } else if encrypted.version == 0 || encrypted.version == 1 {
                // 旧版本配置，尝试解密并迁移
                log::info!("检测到旧版加密配置，正在迁移...");
                let config = decrypt_config_legacy(&encrypted)?;
                // 保存为新版本
                save_secure_config(&config)?;
                log::info!("配置迁移完成");
                Ok(config)
            } else {
                Err(format!("不支持的加密版本: {}", encrypted.version))
            }
        }
        Err(_) => {
            // 如果不是加密格式，尝试直接解析为 SecureConfig（向后兼容）
            serde_json::from_str::<SecureConfig>(&content)
                .map_err(|e| format!("解析配置文件失败: {}", e))
        }
    }
}

/**
 * 保存安全配置（使用 AES-256-GCM 加密存储）
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

    // 生成本地 Token（增加长度至 32 字节）
    let token_bytes: Vec<u8> = (0..32).map(|_| rand::thread_rng().gen::<u8>()).collect();
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
        key_version: 1, // 初始密钥版本
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
 * 轮换密钥
 * 生成新的 JWT 密钥和本地 Token，并增加密钥版本
 */
pub fn rotate_keys() -> Result<SecureConfig, String> {
    let mut config = load_secure_config()?;

    use rand::Rng;

    // 生成新的 JWT 密钥
    let jwt_key: Vec<u8> = (0..32).map(|_| rand::thread_rng().gen::<u8>()).collect();
    config.jwt_secret_key = STANDARD.encode(&jwt_key);

    // 生成新的本地 Token
    let token_bytes: Vec<u8> = (0..32).map(|_| rand::thread_rng().gen::<u8>()).collect();
    config.local_token = format!(
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

    // 增加密钥版本
    config.key_version += 1;

    save_secure_config(&config)?;

    log::info!("密钥轮换完成，新版本: {}", config.key_version);
    Ok(config)
}

/**
 * 获取当前密钥版本
 */
pub fn get_key_version() -> Result<u32, String> {
    let config = load_secure_config()?;
    Ok(config.key_version)
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
 * 获取调试模式
 */
pub fn get_debug_mode() -> Result<bool, String> {
    let config = load_secure_config()?;
    Ok(config.debug_mode)
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
 * 重置所有令牌
 * 生成新的 JWT 密钥和本地 Token
 */
pub fn reset_all_tokens() -> Result<(), String> {
    rotate_keys()?;
    log::info!("所有令牌已重置");
    Ok(())
}

/**
 * 检查配置文件是否存在
 */
pub fn has_secure_config() -> Result<bool, String> {
    let config_path = get_secure_config_path()?;
    Ok(config_path.exists())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encrypt_decrypt() {
        let config = SecureConfig {
            jwt_secret_key: "test_jwt_key".to_string(),
            local_token: "test_local_token".to_string(),
            debug_mode: false,
            security_password: "test_password".to_string(),
            key_version: 1,
        };

        // 加密
        let encrypted = encrypt_config(&config).unwrap();
        assert!(encrypted.encrypted);
        assert_eq!(encrypted.version, CURRENT_ENCRYPTION_VERSION);

        // 解密
        let decrypted = decrypt_config(&encrypted).unwrap();
        assert_eq!(decrypted.jwt_secret_key, config.jwt_secret_key);
        assert_eq!(decrypted.local_token, config.local_token);
        assert_eq!(decrypted.debug_mode, config.debug_mode);
        assert_eq!(decrypted.key_version, config.key_version);
    }

    #[test]
    fn test_key_derivation() {
        let key_material = b"test_key_material";
        let salt = b"test_salt";

        let key1 = derive_key(key_material, salt);
        let key2 = derive_key(key_material, salt);

        assert_eq!(key1, key2);
        assert_eq!(key1.len(), 32);
    }
}
