/**
 * 获取本地认证 Token
 * 用于 WebSocket 连接认证
 *
 * @return 本地认证Token
 */
#[tauri::command]
pub fn get_local_token() -> Result<String, String> {
    let auth_config = crate::core::local_auth::get_local_auth_config()?;

    if auth_config.local_token.is_empty() {
        return Err("本地认证 Token 未初始化".to_string());
    }

    Ok(auth_config.local_token)
}
