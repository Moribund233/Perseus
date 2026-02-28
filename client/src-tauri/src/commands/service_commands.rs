/**
 * 服务控制命令模块
 *
 * 提供服务端启动、停止、重启和状态查询功能
 */
use crate::core::api_client;
use crate::core::process_manager;
use crate::models::{ActionResponse, ServiceStatus};

/**
 * 获取服务状态
 *
 * @return 服务状态
 */
#[tauri::command]
pub async fn get_service_status() -> Result<ServiceStatus, String> {
    api_client::get_service_status().await
}

/**
 * 启动服务
 *
 * @return 操作响应
 */
#[tauri::command]
pub async fn start_service() -> Result<ActionResponse, String> {
    match process_manager::start_server() {
        Ok(pid) => Ok(ActionResponse {
            success: true,
            message: format!("服务已启动 (PID: {})", pid),
        }),
        Err(e) => Ok(ActionResponse {
            success: false,
            message: e,
        }),
    }
}

/**
 * 停止服务
 *
 * 先尝试通过API优雅关闭，失败则强制停止进程
 * @return 操作响应
 */
#[tauri::command]
pub async fn stop_service() -> Result<ActionResponse, String> {
    // 先尝试通过 API 优雅关闭（使用3秒短超时，避免服务端挂起时长时间等待）
    match api_client::stop_service_with_timeout(3).await {
        Ok(response) => {
            if response.success {
                // 等待一段时间后检查进程是否已停止
                tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
            }
        }
        Err(e) => {
            // API 调用失败，记录日志后直接强制停止
            log::warn!("优雅关闭失败（{}），将强制停止进程", e);
        }
    }

    // 强制停止进程
    match process_manager::stop_server() {
        Ok(_) => Ok(ActionResponse {
            success: true,
            message: "服务已停止".to_string(),
        }),
        Err(e) => Ok(ActionResponse {
            success: false,
            message: e,
        }),
    }
}

/**
 * 重启服务
 *
 * @return 操作响应
 */
#[tauri::command]
pub async fn restart_service() -> Result<ActionResponse, String> {
    // 先停止服务
    let _ = stop_service().await;

    // 等待一段时间
    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

    // 启动服务
    start_service().await
}

/**
 * 检查服务是否运行
 *
 * @return 是否运行
 */
#[tauri::command]
pub fn is_service_running() -> bool {
    process_manager::is_server_running()
}

/**
 * 检查服务端连接
 *
 * @return 是否连接成功
 */
#[tauri::command]
pub async fn check_connection() -> Result<bool, String> {
    match api_client::get_service_status().await {
        Ok(_) => Ok(true),
        Err(e) => {
            log::warn!("检查连接失败: {}", e);
            Ok(false)
        }
    }
}

/**
 * 获取健康状态（不需要认证）
 *
 * @return 健康状态JSON
 */
#[tauri::command]
pub async fn get_health_status() -> Result<serde_json::Value, String> {
    let client = api_client::ApiClient::new_without_local_auth()?;
    client.get("/health").await
}
