/**
 * Tauri 应用库入口
 *
 * 导出所有模块并初始化应用
 */
pub mod commands;
pub mod core;
pub mod models;
pub mod services;

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

            // 初始化 WebSocket 日志状态
            app.manage(commands::LogWsState::default());

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
            commands::get_platform_info,
            // Redis管理
            commands::get_redis_status,
            commands::load_redis,
            commands::start_redis,
            commands::stop_redis,
            commands::restart_redis,
            commands::update_redis_config,
            commands::get_redis_runtime_configs,
            commands::update_redis_runtime_config,
            commands::batch_update_redis_runtime_configs,
            commands::rewrite_redis_config,
            commands::get_redis_memory_info,
            commands::get_redis_client_info,
            commands::install_redis_service,
            commands::uninstall_redis_service,
            commands::is_redis_service_installed,
            commands::validate_redis_dir,
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
            commands::get_jwt_secret_key,
            // 数据库安装检测
            commands::check_installed_databases,
            // 数据库连接测试（客户端本地）
            commands::check_sqlite_file,
            commands::test_tcp_connection,
            // 压力测试和数据库配置
            commands::get_stress_test,
            commands::update_stress_test,
            commands::get_database_urls,
            commands::get_database_url,
            commands::get_database_type,
            commands::switch_database_type,
            commands::update_database_url,
            // 数据库迁移
            commands::precheck_migration,
            commands::execute_migration,
            commands::switch_database,
            commands::rollback_database_switch,
            commands::get_current_database_info,
            commands::test_database_connection,
            // WebSocket 日志（后端代理）
            commands::init_log_websocket,
            commands::connect_log_websocket,
            commands::disconnect_log_websocket,
            commands::get_log_websocket_state,
            commands::subscribe_logs,
            commands::unsubscribe_logs,
            commands::reset_database,
            commands::reset_config,
            commands::get_debug_status,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    // 运行应用并处理退出事件
    app.run(|_app_handle, event| {
        if let RunEvent::ExitRequested { .. } = event {
            log::info!("应用退出请求，执行清理...");

            // 检查 Nginx 是否在运行，只有在运行中才尝试停止
            let nginx_status = services::nginx::get_nginx_status();
            if nginx_status.status == "running" {
                log::info!(
                    "Nginx 正在运行中 (PID: {:?})，执行停止操作...",
                    nginx_status.pid
                );
                let nginx_result = services::nginx::stop_nginx();
                if !nginx_result.success {
                    log::warn!("停止 Nginx 失败: {}", nginx_result.message);
                } else {
                    log::info!("Nginx 已停止");
                }
            } else {
                log::info!("Nginx 未在运行，跳过停止操作");
            }

            // 检查 Redis 是否在运行，只有在运行中才尝试停止
            let redis_status = services::redis::get_redis_status();
            if redis_status.status == "running" {
                log::info!("Redis 正在运行中，执行停止操作...");
                let redis_result = services::redis::stop_redis();
                if !redis_result.success {
                    log::warn!("停止 Redis 失败: {}", redis_result.message);
                } else {
                    log::info!("Redis 已停止");
                }
            } else {
                log::info!("Redis 未在运行，跳过停止操作");
            }

            // 停止服务端进程
            if let Err(e) = core::process_manager::stop_server() {
                log::warn!("停止服务端失败: {}", e);
            }

            log::info!("清理完成");
        }
    });
}
