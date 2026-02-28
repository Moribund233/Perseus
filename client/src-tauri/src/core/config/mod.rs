/**
 * 配置管理模块
 *
 * 管理应用程序的配置，包括普通配置和安全配置
 */
// 子模块
pub mod app;
pub mod secure;

// 重新导出 app 模块的公共接口
pub use app::{
    get_auth_token, get_config_path, get_server_url, has_app_dir_config, has_user_config,
    init_default_config, init_secure_config, load_config, load_secure_config, save_config,
    save_secure_config, update_appearance_config, update_auth_token, update_notification_config,
    update_server_config, update_server_url,
};

// 从 models 重新导出 ClientConfig
pub use crate::models::ClientConfig;

// 重新导出 secure 模块的公共接口
pub use secure::{
    get_database_url, get_database_urls, get_debug_mode, get_jwt_secret_key, get_key_version,
    get_local_token, get_stress_test, has_secure_config, init_secure_config as init_secure,
    load_secure_config as load_secure, rotate_keys, save_secure_config as save_secure,
    set_security_password, update_database_url, update_debug_mode, update_jwt_secret_key,
    update_local_token, update_stress_test, verify_security_password, DatabaseType, SecureConfig,
};
