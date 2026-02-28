/**
 * Redis管理命令模块
 *
 * 提供Redis状态查询、启动、停止、配置管理等功能
 */
use crate::models::{
    RedisActionResponse, RedisConfigSaveResponse, RedisConfigUpdateRequest, RedisStatusResponse,
    WindowsServiceResponse,
};

/**
 * 获取Redis状态
 *
 * @return Redis状态响应
 */
#[tauri::command]
pub fn get_redis_status() -> Result<RedisStatusResponse, String> {
    Ok(crate::services::redis::get_redis_status())
}

/**
 * 载入Redis目录
 *
 * @param exe_dir Redis可执行文件目录路径
 * @return 操作响应
 */
#[tauri::command]
pub fn load_redis(exe_dir: String) -> Result<RedisActionResponse, String> {
    Ok(crate::services::redis::load_redis(exe_dir))
}

/**
 * 启动Redis
 *
 * @return 操作响应
 */
#[tauri::command]
pub fn start_redis() -> Result<RedisActionResponse, String> {
    Ok(crate::services::redis::start_redis())
}

/**
 * 停止Redis
 *
 * @return 操作响应
 */
#[tauri::command]
pub fn stop_redis() -> Result<RedisActionResponse, String> {
    Ok(crate::services::redis::stop_redis())
}

/**
 * 重启Redis
 *
 * @return 操作响应
 */
#[tauri::command]
pub fn restart_redis() -> Result<RedisActionResponse, String> {
    Ok(crate::services::redis::restart_redis())
}

/**
 * 更新Redis配置
 *
 * @param request 配置更新请求
 * @return 保存响应
 */
#[tauri::command]
pub fn update_redis_config(
    request: RedisConfigUpdateRequest,
) -> Result<RedisConfigSaveResponse, String> {
    Ok(crate::services::redis::update_redis_config(request))
}

/**
 * 安装Redis为Windows服务
 *
 * @param exe_dir Redis可执行文件目录
 * @return 操作响应
 */
#[tauri::command]
pub fn install_redis_service(exe_dir: String) -> Result<WindowsServiceResponse, String> {
    Ok(crate::services::redis::install_redis_service(&exe_dir))
}

/**
 * 卸载Redis Windows服务
 *
 * @return 操作响应
 */
#[tauri::command]
pub fn uninstall_redis_service() -> Result<WindowsServiceResponse, String> {
    Ok(crate::services::redis::uninstall_redis_service())
}

/**
 * 检查Redis服务是否已安装
 *
 * @return 是否已安装
 */
#[tauri::command]
pub fn is_redis_service_installed() -> Result<bool, String> {
    Ok(crate::services::redis::is_redis_service_installed())
}

/**
 * 验证Redis目录是否有效
 *
 * @param exe_dir Redis可执行文件目录
 * @return 是否有效
 */
#[tauri::command]
pub fn validate_redis_dir(exe_dir: String) -> Result<bool, String> {
    use std::path::Path;

    let path = Path::new(&exe_dir);

    if !path.exists() || !path.is_dir() {
        return Ok(false);
    }

    // 检查必要的可执行文件是否存在
    let is_windows = cfg!(target_os = "windows");
    let redis_server = if is_windows {
        path.join("redis-server.exe")
    } else {
        path.join("redis-server")
    };

    let redis_cli = if is_windows {
        path.join("redis-cli.exe")
    } else {
        path.join("redis-cli")
    };

    Ok(redis_server.exists() && redis_cli.exists())
}
