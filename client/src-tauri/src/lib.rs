/**
 * Tauri 应用库入口
 *
 * 导出所有模块并初始化应用
 */
pub mod api_client;
pub mod commands;
pub mod config;
pub mod local_auth;
pub mod models;
pub mod nginx_manager;
pub mod process_manager;
pub mod secure_config;

use tauri::{Manager, RunEvent};

/// 运行 Tauri 应用
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            // 初始化日志插件
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // 初始化应用状态
            app.manage(commands::AppState::default());

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // 服务控制
            commands::get_service_status,
            commands::start_service,
            commands::stop_service,
            commands::restart_service,
            commands::is_service_running,
            // 性能监控
            commands::get_performance_data,
            commands::get_system_resources,
            commands::get_server_process_info,
            // 日志管理
            commands::get_log_info,
            commands::get_log_content,
            commands::cleanup_logs,
            // 配置管理
            commands::get_app_config,
            commands::update_app_config,
            commands::reset_app_config,
            commands::validate_app_config,
            // 客户端配置
            commands::get_client_config,
            commands::save_client_config,
            commands::update_server_url,
            commands::update_auth_token,
            commands::get_server_url,
            // 健康检查
            commands::check_connection,
            commands::get_health_status,
            // 本地系统信息
            commands::get_local_system_info,
            // 本地认证
            commands::get_local_token,
            // Nginx管理
            commands::get_nginx_status,
            commands::load_nginx,
            commands::start_nginx,
            commands::stop_nginx,
            commands::restart_nginx,
            commands::download_and_extract_nginx,
            commands::get_nginx_download_url,
            commands::update_nginx_download_url,
            commands::validate_nginx,
            commands::get_nginx_proxy_config,
            commands::save_nginx_proxy_config,
            commands::get_nginx_platform_info,
            // 引导页面
            commands::check_server_path,
            commands::validate_and_save_server_path,
            commands::check_git_installation,
            commands::mark_guide_completed,
            commands::is_guide_completed,
            commands::has_user_config_file,
            commands::reset_client_config,
            // 安全配置
            commands::set_security_password,
            commands::verify_security_password,
            commands::has_security_password,
            commands::get_debug_mode,
            commands::update_debug_mode,
            commands::reset_all_tokens,
            commands::is_elevated,
            commands::get_jwt_secret_key,
            // 数据库迁移
            commands::migrate_database,
            commands::test_database_connection,
            // 压力测试和数据库配置
            commands::get_stress_test,
            commands::update_stress_test,
            commands::get_database_urls,
            commands::get_database_url,
            commands::get_database_type,
            commands::switch_database_type,
            commands::update_database_url,
            commands::get_database_status_from_api,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    // 运行应用并处理退出事件
    app.run(|_app_handle, event| {
        if let RunEvent::ExitRequested { .. } = event {
            log::info!("应用退出请求，执行清理...");

            // 检查 Nginx 是否在运行，只有在运行中才尝试停止
            let nginx_status = nginx_manager::get_nginx_status();
            if nginx_status.status == "running" {
                log::info!(
                    "Nginx 正在运行中 (PID: {:?})，执行停止操作...",
                    nginx_status.pid
                );
                let nginx_result = nginx_manager::stop_nginx();
                if !nginx_result.success {
                    log::warn!("停止 Nginx 失败: {}", nginx_result.message);
                } else {
                    log::info!("Nginx 已停止");
                }
            } else {
                log::info!("Nginx 未在运行，跳过停止操作");
            }

            // 停止服务端进程
            if let Err(e) = process_manager::stop_server() {
                log::warn!("停止服务端失败: {}", e);
            }

            log::info!("清理完成");
        }
    });
}
