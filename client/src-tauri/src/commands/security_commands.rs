/**
 * 安全配置命令模块
 *
 * 提供安全密码、调试模式、数据库URL等安全配置管理
 */
use crate::core::config::secure as secure_config;

/**
 * 设置客户端安全密码
 *
 * @param password 密码
 */
#[tauri::command]
pub fn set_security_password(password: String) -> Result<(), String> {
    secure_config::set_security_password(password)
}

/**
 * 验证客户端安全密码
 *
 * @param password 密码
 * @return 是否验证通过
 */
#[tauri::command]
pub fn verify_security_password(password: String) -> Result<bool, String> {
    secure_config::verify_security_password(&password)
}

/**
 * 检查是否已设置安全密码
 *
 * @return 是否已设置
 */
#[tauri::command]
pub fn has_security_password() -> Result<bool, String> {
    secure_config::has_security_password()
}

/**
 * 获取调试模式状态
 *
 * @return 是否开启调试模式
 */
#[tauri::command]
pub fn get_debug_mode() -> Result<bool, String> {
    secure_config::get_debug_mode()
}

/**
 * 更新调试模式
 *
 * @param debug 是否开启
 */
#[tauri::command]
pub fn update_debug_mode(debug: bool) -> Result<(), String> {
    secure_config::update_debug_mode(debug)
}

/**
 * 重置所有安全令牌
 */
#[tauri::command]
pub fn reset_all_tokens() -> Result<(), String> {
    secure_config::reset_all_tokens()
}

/**
 * 获取 JWT 密钥
 *
 * @return JWT密钥
 */
#[tauri::command]
pub fn get_jwt_secret_key() -> Result<String, String> {
    secure_config::get_jwt_secret_key()
}

/**
 * 获取压力测试模式状态
 *
 * @return 是否开启压力测试
 */
#[tauri::command]
pub fn get_stress_test() -> Result<bool, String> {
    secure_config::get_stress_test()
}

/**
 * 更新压力测试模式
 *
 * @param stress 是否开启
 */
#[tauri::command]
pub fn update_stress_test(stress: bool) -> Result<(), String> {
    secure_config::update_stress_test(stress)
}

/**
 * 获取所有数据库连接 URL
 *
 * @return 数据库类型到URL的映射
 */
#[tauri::command]
pub fn get_database_urls() -> Result<std::collections::HashMap<String, String>, String> {
    secure_config::get_database_urls()
}

/**
 * 获取指定类型的数据库连接 URL
 *
 * @param db_type 数据库类型
 * @return 连接URL
 */
#[tauri::command]
pub fn get_database_url(db_type: String) -> Result<String, String> {
    secure_config::get_database_url(&db_type)
}

/**
 * 获取数据库类型（从 client.toml 读取）
 *
 * @return 数据库类型
 */
#[tauri::command]
pub fn get_database_type() -> Result<String, String> {
    let config = crate::core::config::load_config()?;
    Ok(config.db_type)
}

/**
 * 切换数据库类型（保存到 client.toml）
 *
 * @param db_type 数据库类型
 */
#[tauri::command]
pub fn switch_database_type(db_type: String) -> Result<(), String> {
    let mut config = crate::core::config::load_config()?;
    config.db_type = db_type;
    crate::core::config::save_config(&config)
}

/**
 * 更新指定类型的数据库连接 URL
 *
 * @param db_type 数据库类型
 * @param url 连接URL
 */
#[tauri::command]
pub fn update_database_url(db_type: String, url: String) -> Result<(), String> {
    secure_config::update_database_url(db_type, url)
}
