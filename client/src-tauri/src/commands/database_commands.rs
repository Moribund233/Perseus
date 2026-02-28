/**
 * 数据库命令模块
 *
 * 提供数据库安装检测、连接测试、迁移等功能
 */
use crate::core::api_client;
use crate::models::{DatabaseSwitchResponse, MigrationResponse, PrecheckResponse, TcpTestResult};
use tokio::net::TcpStream;
use tokio::time::{timeout, Duration};

/**
 * 检测系统中已安装的数据库
 *
 * 返回已安装的数据库类型列表：["sqlite", "postgresql", "mysql"]
 * - SQLite: 总是可用（内置于 Python）
 * - PostgreSQL: 检查 psql/pg_isready 命令是否存在
 * - MySQL: 检查 mysql/mysqld 命令是否存在
 *
 * @return 已安装的数据库类型列表
 */
#[tauri::command]
pub async fn check_installed_databases() -> Result<Vec<String>, String> {
    let mut installed = vec!["sqlite".to_string()];

    // 检查 PostgreSQL (psql 或 pg_isready)
    if check_any_command_exists(&["psql", "pg_isready"]).await {
        installed.push("postgresql".to_string());
        log::info!("PostgreSQL 已安装");
    }

    // 检查 MySQL (mysql 或 mysqld)
    if check_any_command_exists(&["mysql", "mysqld"]).await {
        installed.push("mysql".to_string());
        log::info!("MySQL 已安装");
    }

    log::info!("已安装的数据库: {:?}", installed);
    Ok(installed)
}

/**
 * 检查任一命令是否存在
 *
 * @param commands 命令列表
 * @return 是否存在
 */
async fn check_any_command_exists(commands: &[&str]) -> bool {
    for cmd in commands {
        if check_command_exists(cmd).await.unwrap_or(false) {
            return true;
        }
    }
    false
}

/**
 * 检查命令是否存在
 *
 * @param command 命令名
 * @return 是否存在
 */
#[cfg(target_os = "windows")]
async fn check_command_exists(command: &str) -> Result<bool, std::io::Error> {
    tokio::process::Command::new("where")
        .arg(command)
        .output()
        .await
        .map(|output| output.status.success())
}

#[cfg(not(target_os = "windows"))]
async fn check_command_exists(command: &str) -> Result<bool, std::io::Error> {
    tokio::process::Command::new("which")
        .arg(command)
        .output()
        .await
        .map(|output| output.status.success())
}

/**
 * 检查 SQLite 数据库文件是否存在
 * 相对路径基于服务端可执行文件所在目录解析
 *
 * @param file_path 文件路径
 * @return 是否存在
 */
#[tauri::command]
pub fn check_sqlite_file(file_path: String) -> Result<bool, String> {
    use crate::core::process_manager::get_server_exe_path;
    use std::path::Path;

    let path = Path::new(&file_path);

    // 获取服务端可执行文件所在目录
    let server_dir = get_server_exe_path()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()));

    // 构建完整路径
    let full_path = if path.is_relative() {
        match &server_dir {
            Some(dir) => dir.join(path),
            None => path.to_path_buf(),
        }
    } else {
        path.to_path_buf()
    };

    let exists = full_path.exists();
    let is_file = full_path.is_file();

    Ok(exists && is_file)
}

/**
 * 测试 TCP 连接（用于 PostgreSQL/MySQL）
 *
 * @param host 主机地址
 * @param port 端口号
 * @return TCP测试结果
 */
#[tauri::command]
pub async fn test_tcp_connection(host: String, port: u16) -> Result<TcpTestResult, String> {
    let addr = format!("{}:{}", host, port);

    // 5秒超时
    let result = timeout(Duration::from_secs(5), TcpStream::connect(&addr)).await;

    match result {
        Ok(Ok(_)) => Ok(TcpTestResult {
            success: true,
            error: None,
        }),
        Ok(Err(e)) => Ok(TcpTestResult {
            success: false,
            error: Some(format!("连接失败: {}", e)),
        }),
        Err(_) => Ok(TcpTestResult {
            success: false,
            error: Some("连接超时".to_string()),
        }),
    }
}

/**
 * 执行迁移预检查
 *
 * @param target_url 目标数据库URL
 * @return 预检查结果
 */
#[tauri::command]
pub async fn precheck_migration(target_url: String) -> Result<PrecheckResponse, String> {
    api_client::precheck_migration(&target_url).await
}

/**
 * 执行数据库迁移
 *
 * @param target_url 目标数据库URL
 * @param batch_size 批量大小（可选）
 * @return 迁移结果
 */
#[tauri::command]
pub async fn execute_migration(
    target_url: String,
    batch_size: Option<i32>,
) -> Result<MigrationResponse, String> {
    api_client::execute_migration(&target_url, batch_size).await
}

/**
 * 切换数据库
 * 完整的切换流程：预检查 -> 迁移（如需要）-> 更新配置
 *
 * @param db_type 数据库类型
 * @param target_url 目标数据库URL
 * @return 切换结果
 */
#[tauri::command]
pub async fn switch_database(
    db_type: String,
    target_url: String,
) -> Result<DatabaseSwitchResponse, String> {
    log::info!("开始切换数据库: {} -> {}", db_type, target_url);

    // 保存原始数据库类型用于回滚
    let original_db_type = super::security_commands::get_database_type()?;

    // 步骤1: 执行预检查
    log::info!("步骤1: 执行预检查...");
    let precheck_result = match api_client::precheck_migration(&target_url).await {
        Ok(result) => result,
        Err(e) => {
            log::error!("预检查失败: {}", e);
            return Ok(DatabaseSwitchResponse {
                success: false,
                message: format!("预检查失败: {}", e),
                need_migration: false,
                migration_result: None,
                need_restart: false,
            });
        }
    };

    // 检查预检查是否通过
    if !precheck_result.passed {
        let error_msg = precheck_result
            .errors
            .iter()
            .map(|e| e.message.clone())
            .collect::<Vec<_>>()
            .join("; ");
        log::error!("预检查未通过: {}", error_msg);
        return Ok(DatabaseSwitchResponse {
            success: false,
            message: format!("预检查未通过: {}", error_msg),
            need_migration: false,
            migration_result: None,
            need_restart: false,
        });
    }

    // 步骤2: 先更新客户端配置中的数据库类型
    log::info!("步骤2: 更新客户端配置...");
    if let Err(e) = super::security_commands::switch_database_type(db_type.clone()) {
        log::error!("更新数据库类型失败: {}", e);
        return Ok(DatabaseSwitchResponse {
            success: false,
            message: format!("更新配置失败: {}", e),
            need_migration: false,
            migration_result: None,
            need_restart: false,
        });
    }

    // 步骤3: 检查是否需要迁移
    let need_migration = !precheck_result.is_synced;
    let mut migration_result: Option<MigrationResponse> = None;

    if need_migration {
        log::info!("步骤3: 需要数据迁移，开始执行...");

        // 执行迁移
        match api_client::execute_migration(&target_url, Some(1000)).await {
            Ok(result) => {
                if result.success {
                    log::info!(
                        "迁移成功: {} 个表, {} 行数据",
                        result.tables_migrated,
                        result.total_rows_migrated
                    );
                    migration_result = Some(result);
                } else {
                    log::error!("迁移失败，开始回滚...");
                    // 迁移失败，回滚数据库类型
                    let _ =
                        super::security_commands::switch_database_type(original_db_type.clone());

                    let error_msg = result
                        .errors
                        .iter()
                        .map(|e| format!("{}: {}", e.table, e.error))
                        .collect::<Vec<_>>()
                        .join("; ");

                    return Ok(DatabaseSwitchResponse {
                        success: false,
                        message: format!("迁移失败: {}", error_msg),
                        need_migration: true,
                        migration_result: Some(result),
                        need_restart: false,
                    });
                }
            }
            Err(e) => {
                log::error!("迁移执行失败: {}，开始回滚...", e);
                // 迁移失败，回滚数据库类型
                let _ = super::security_commands::switch_database_type(original_db_type.clone());

                return Ok(DatabaseSwitchResponse {
                    success: false,
                    message: format!("迁移执行失败: {}", e),
                    need_migration: true,
                    migration_result: None,
                    need_restart: false,
                });
            }
        }
    } else {
        log::info!("步骤3: 数据库已同步，无需迁移");
    }

    // 步骤4: 更新环境变量配置
    log::info!("步骤4: 更新环境变量配置...");
    if let Err(e) = super::security_commands::update_database_url(db_type.clone(), target_url) {
        log::error!("更新数据库URL失败: {}，开始回滚...", e);
        // 回滚数据库类型
        let _ = super::security_commands::switch_database_type(original_db_type.clone());

        return Ok(DatabaseSwitchResponse {
            success: false,
            message: format!("更新数据库URL失败: {}", e),
            need_migration,
            migration_result: migration_result.clone(),
            need_restart: false,
        });
    }

    // 步骤5: 返回成功结果
    let message = if need_migration {
        format!(
            "数据库切换成功，已迁移 {} 个表",
            migration_result
                .as_ref()
                .map(|r| r.tables_migrated)
                .unwrap_or(0)
        )
    } else {
        "数据库已同步，切换成功".to_string()
    };

    log::info!("数据库切换完成: {}", message);

    Ok(DatabaseSwitchResponse {
        success: true,
        message,
        need_migration,
        migration_result,
        need_restart: true, // 需要重启服务才能生效
    })
}

/**
 * 回滚数据库切换
 * 在迁移失败时恢复原来的数据库类型
 *
 * @param original_db_type 原始数据库类型
 */
#[tauri::command]
pub fn rollback_database_switch(original_db_type: String) -> Result<(), String> {
    log::info!("回滚数据库切换到: {}", original_db_type);
    super::security_commands::switch_database_type(original_db_type)
}

/**
 * 获取当前数据库连接信息
 *
 * @return 数据库信息JSON
 */
#[tauri::command]
pub fn get_current_database_info() -> Result<serde_json::Value, String> {
    let db_type = super::security_commands::get_database_type()?;
    let url = crate::core::config::secure::get_database_url(&db_type)?;

    Ok(serde_json::json!({
        "db_type": db_type,
        "url": url
    }))
}

/**
 * 测试数据库连接
 *
 * @param url 数据库连接URL
 * @return 测试结果JSON
 */
#[tauri::command]
pub async fn test_database_connection(url: String) -> Result<serde_json::Value, String> {
    // 根据 URL 类型选择测试方式
    if url.starts_with("sqlite") {
        // SQLite: 检查文件是否存在或能否创建
        let file_path = url.replace("sqlite:///", "");
        let exists = std::path::Path::new(&file_path).exists();

        Ok(serde_json::json!({
            "success": true,
            "message": if exists { "数据库文件存在" } else { "将创建新数据库文件" }
        }))
    } else if url.contains("postgresql") || url.contains("mysql") {
        // PostgreSQL/MySQL: 测试 TCP 连接
        // 解析 host 和 port
        let host_port = url
            .split("@")
            .nth(1)
            .and_then(|s| s.split("/").next())
            .unwrap_or("localhost:5432");

        let parts: Vec<&str> = host_port.split(':').collect();
        let host = parts[0];
        let port = parts.get(1).and_then(|p| p.parse().ok()).unwrap_or(5432u16);

        // 使用 TCP 连接测试
        let addr = format!("{}:{}", host, port);
        let result = timeout(Duration::from_secs(5), TcpStream::connect(&addr)).await;

        match result {
            Ok(Ok(_)) => Ok(serde_json::json!({
                "success": true,
                "message": "数据库连接成功"
            })),
            Ok(Err(e)) => Ok(serde_json::json!({
                "success": false,
                "message": format!("连接失败: {}", e)
            })),
            Err(_) => Ok(serde_json::json!({
                "success": false,
                "message": "连接超时"
            })),
        }
    } else {
        Ok(serde_json::json!({
            "success": false,
            "message": "不支持的数据库类型"
        }))
    }
}
