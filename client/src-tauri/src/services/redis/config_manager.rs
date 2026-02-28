/**
 * Redis配置管理模块
 *
 * 管理Redis配置的读取、修改和保存
 * 使用redis-cli命令进行跨平台的配置管理
 */
use std::collections::HashMap;
use std::path::Path;
use std::process::Command;

use crate::core::config;
use crate::models::{
    RedisActionResponse, RedisConfigSaveResponse, RedisConfigUpdateRequest, RedisRuntimeConfig,
    RedisRuntimeConfigBatchUpdateRequest, RedisRuntimeConfigResponse,
    RedisRuntimeConfigUpdateRequest, RedisRuntimeConfigUpdateResponse,
};

// ============================================================================
// 基础工具函数
// ============================================================================

/**
 * 检查是否为Windows平台
 *
 * @return 是否为Windows平台
 */
fn is_windows() -> bool {
    cfg!(target_os = "windows")
}

/**
 * 获取redis-cli路径
 *
 * @return redis-cli路径
 */
fn get_redis_cli_path() -> Result<std::path::PathBuf, String> {
    let client_config = config::load_config().map_err(|e| format!("加载配置失败: {}", e))?;
    let redis_config = client_config.redis;

    if !redis_config.is_loaded {
        return Err("Redis未载入".to_string());
    }

    let exe_dir = redis_config.exe_dir.ok_or("Redis目录未设置")?;
    let redis_cli_path = Path::new(&exe_dir).join(if is_windows() {
        "redis-cli.exe"
    } else {
        "redis-cli"
    });

    if !redis_cli_path.exists() {
        return Err(format!("redis-cli不存在: {}", redis_cli_path.display()));
    }

    Ok(redis_cli_path)
}

/**
 * 获取Redis连接参数
 *
 * @return (端口, 密码)
 */
fn get_redis_connection_args() -> Result<(u16, Option<String>), String> {
    let client_config = config::load_config().map_err(|e| format!("加载配置失败: {}", e))?;
    let redis_config = client_config.redis;

    if !redis_config.is_loaded {
        return Err("Redis未载入".to_string());
    }

    Ok((redis_config.port, redis_config.password))
}

/**
 * 执行redis-cli命令
 *
 * @param args 命令参数
 * @return 命令输出
 */
fn execute_redis_cli(args: &[&str]) -> Result<String, String> {
    let redis_cli_path = get_redis_cli_path()?;
    let (port, password) = get_redis_connection_args()?;

    let mut cmd = Command::new(&redis_cli_path);
    cmd.arg("-p").arg(port.to_string());

    // 如果有密码，添加认证
    if let Some(pwd) = password {
        cmd.arg("-a").arg(pwd);
    }

    cmd.args(args);

    match cmd.output() {
        Ok(output) => {
            if output.status.success() {
                let stdout = String::from_utf8_lossy(&output.stdout);
                Ok(stdout.trim().to_string())
            } else {
                let stderr = String::from_utf8_lossy(&output.stderr);
                Err(format!("redis-cli执行失败: {}", stderr))
            }
        }
        Err(e) => Err(format!("执行redis-cli失败: {}", e)),
    }
}

// ============================================================================
// 目录和版本管理
// ============================================================================

/**
 * 检查Windows平台Redis目录是否有效
 *
 * @param exe_dir Redis可执行文件目录
 * @return 是否有效
 */
fn is_valid_redis_dir(exe_dir: &str) -> bool {
    let path = Path::new(exe_dir);

    if !path.exists() || !path.is_dir() {
        return false;
    }

    // 检查必要的可执行文件是否存在
    let redis_server = if is_windows() {
        path.join("redis-server.exe")
    } else {
        path.join("redis-server")
    };

    let redis_cli = if is_windows() {
        path.join("redis-cli.exe")
    } else {
        path.join("redis-cli")
    };

    redis_server.exists() && redis_cli.exists()
}

/**
 * 获取Redis版本信息（通过可执行文件）
 *
 * @param exe_dir Redis可执行文件目录
 * @return 版本信息
 */
fn get_redis_version(exe_dir: &str) -> Option<String> {
    let path = Path::new(exe_dir);
    let redis_server = if is_windows() {
        path.join("redis-server.exe")
    } else {
        path.join("redis-server")
    };

    if !redis_server.exists() {
        return None;
    }

    let output = Command::new(&redis_server).arg("--version").output().ok()?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);

    let version_info = if stdout.contains("Redis") {
        stdout.to_string()
    } else if stderr.contains("Redis") {
        stderr.to_string()
    } else {
        return None;
    };

    version_info.lines().next().map(|s| s.trim().to_string())
}

/**
 * 检测Redis配置文件路径
 *
 * @param exe_dir Redis可执行文件目录
 * @return 配置文件路径
 */
fn detect_config_path(exe_dir: &str) -> Option<String> {
    let possible_paths = vec![
        Path::new(exe_dir).join("redis.conf"),
        Path::new(exe_dir).join("redis.windows.conf"),
        Path::new(exe_dir).join("redis.windows-service.conf"),
    ];

    for path in possible_paths {
        if path.exists() {
            return Some(path.to_string_lossy().to_string());
        }
    }

    None
}

/**
 * 检测Redis数据目录
 *
 * @param exe_dir Redis可执行文件目录
 * @return 数据目录路径
 */
fn detect_data_dir(exe_dir: &str) -> Option<String> {
    let possible_dirs = vec![
        Path::new(exe_dir).join("data"),
        Path::new(exe_dir).to_path_buf(),
    ];

    for dir in possible_dirs {
        if dir.exists() {
            return Some(dir.to_string_lossy().to_string());
        }
    }

    None
}

// ============================================================================
// Redis载入和状态
// ============================================================================

/**
 * 载入Redis目录
 *
 * @param exe_dir Redis可执行文件目录路径
 * @return 操作响应
 */
pub fn load_redis(exe_dir: String) -> RedisActionResponse {
    use crate::services::redis::response::{error_response, success_response};

    // 验证目录有效性
    if !is_valid_redis_dir(&exe_dir) {
        return error_response(
            "无效的Redis目录，请确保目录包含redis-server和redis-cli可执行文件".to_string(),
        );
    }

    // 获取版本信息
    let version = get_redis_version(&exe_dir);

    // 检测配置文件路径
    let config_path = detect_config_path(&exe_dir);

    // 检测数据目录
    let data_dir = detect_data_dir(&exe_dir);

    // 使用默认配置值（载入时Redis可能未运行，无法通过redis-cli获取）
    // 实际配置值将在Redis启动后通过redis-cli动态获取
    let port = 6379u16;
    let require_pass = false;
    let password: Option<String> = None;

    // 检查是否已作为Windows服务安装
    let is_windows_service = if is_windows() {
        super::windows_service::is_redis_service_installed()
    } else {
        false
    };

    // 保存配置
    match config::load_config() {
        Ok(mut client_config) => {
            client_config.redis.exe_dir = Some(exe_dir.clone());
            client_config.redis.is_loaded = true;
            client_config.redis.version = version.clone();
            client_config.redis.config_path = config_path;
            client_config.redis.data_dir = data_dir;
            client_config.redis.port = port;
            client_config.redis.require_pass = require_pass;
            client_config.redis.password = password;
            client_config.redis.is_windows_service = is_windows_service;

            match config::save_config(&client_config) {
                Ok(_) => success_response(format!(
                    "Redis载入成功{}",
                    version
                        .as_ref()
                        .map(|v| format!(" ({})", v))
                        .unwrap_or_default()
                )),
                Err(e) => error_response(format!("保存配置失败: {}", e)),
            }
        }
        Err(e) => error_response(format!("加载配置失败: {}", e)),
    }
}

/**
 * 获取Redis状态
 *
 * @return 状态响应
 */
pub fn get_redis_status() -> crate::models::RedisStatusResponse {
    use crate::services::redis::lifecycle::check_redis_status;

    match config::load_config() {
        Ok(client_config) => {
            let redis_config = client_config.redis;
            let current_status = check_redis_status();

            crate::models::RedisStatusResponse {
                is_loaded: redis_config.is_loaded,
                status: current_status,
                version: redis_config.version,
                exe_dir: redis_config.exe_dir,
                port: redis_config.port,
                require_pass: redis_config.require_pass,
                config_path: redis_config.config_path,
                data_dir: redis_config.data_dir,
                is_windows_service: redis_config.is_windows_service,
            }
        }
        Err(_) => crate::models::RedisStatusResponse {
            is_loaded: false,
            status: "unknown".to_string(),
            version: None,
            exe_dir: None,
            port: 6379,
            require_pass: false,
            config_path: None,
            data_dir: None,
            is_windows_service: false,
        },
    }
}

// ============================================================================
// 运行时配置管理
// ============================================================================

/**
 * 获取单个配置项
 *
 * @param config_name 配置项名称
 * @return 配置值
 */
pub fn get_config(config_name: &str) -> Result<String, String> {
    execute_redis_cli(&["CONFIG", "GET", config_name])
}

/**
 * 设置单个配置项
 *
 * @param config_name 配置项名称
 * @param value 配置值
 */
pub fn set_config(config_name: &str, value: &str) -> Result<(), String> {
    execute_redis_cli(&["CONFIG", "SET", config_name, value])?;
    Ok(())
}

/**
 * 获取所有配置项
 *
 * @return 所有配置项的HashMap
 */
pub fn get_all_configs() -> Result<HashMap<String, String>, String> {
    let output = execute_redis_cli(&["CONFIG", "GET", "*"])?;
    let mut configs = HashMap::new();

    // 解析输出，格式为：key\nvalue\nkey\nvalue...
    let lines: Vec<&str> = output.lines().collect();
    for i in (0..lines.len()).step_by(2) {
        if i + 1 < lines.len() {
            configs.insert(lines[i].to_string(), lines[i + 1].to_string());
        }
    }

    Ok(configs)
}

/**
 * 获取配置项默认值
 *
 * @param config_name 配置项名称
 * @return 默认值
 */
fn get_config_default(config_name: &str) -> Option<String> {
    match config_name {
        // 网络配置
        "port" => Some("6379".to_string()),
        "bind" => Some("127.0.0.1".to_string()),
        "protected-mode" => Some("yes".to_string()),
        "tcp-backlog" => Some("511".to_string()),
        // 安全配置
        "requirepass" => Some("".to_string()),
        "masterauth" => Some("".to_string()),
        // 性能配置
        "maxclients" => Some("10000".to_string()),
        "timeout" => Some("0".to_string()),
        "tcp-keepalive" => Some("300".to_string()),
        "hz" => Some("10".to_string()),
        // 内存配置
        "maxmemory" => Some("0".to_string()),
        "maxmemory-policy" => Some("noeviction".to_string()),
        "maxmemory-samples" => Some("5".to_string()),
        // 持久化配置
        "save" => Some("3600 1 300 100 60 10000".to_string()),
        "appendonly" => Some("no".to_string()),
        "appendfsync" => Some("everysec".to_string()),
        "auto-aof-rewrite-percentage" => Some("100".to_string()),
        "auto-aof-rewrite-min-size" => Some("64mb".to_string()),
        // 监控配置
        "slowlog-log-slower-than" => Some("10000".to_string()),
        "slowlog-max-len" => Some("128".to_string()),
        "latency-monitor-threshold" => Some("0".to_string()),
        // 常规配置
        "databases" => Some("16".to_string()),
        "loglevel" => Some("notice".to_string()),
        "supervised" => Some("no".to_string()),
        _ => None,
    }
}

/**
 * 获取常用配置项列表
 *
 * @return 常用配置项响应
 */
pub fn get_common_configs() -> RedisRuntimeConfigResponse {
    let common_config_keys = vec![
        // 网络配置
        ("port", "监听端口", "network"),
        ("bind", "绑定地址", "network"),
        ("protected-mode", "保护模式", "network"),
        ("tcp-backlog", "TCP连接队列长度", "network"),
        // 安全配置
        ("requirepass", "访问密码", "security"),
        ("masterauth", "主节点认证密码", "security"),
        // 性能配置
        ("maxclients", "最大客户端连接数", "performance"),
        ("timeout", "连接超时时间(秒)", "performance"),
        ("tcp-keepalive", "TCP保活时间(秒)", "performance"),
        ("hz", "后台任务执行频率", "performance"),
        // 内存配置
        ("maxmemory", "最大内存限制", "memory"),
        ("maxmemory-policy", "内存淘汰策略", "memory"),
        ("maxmemory-samples", "内存淘汰采样数", "memory"),
        // 持久化配置
        ("save", "RDB保存策略", "persistence"),
        ("appendonly", "启用AOF持久化", "persistence"),
        ("appendfsync", "AOF同步策略", "persistence"),
        (
            "auto-aof-rewrite-percentage",
            "AOF重写触发百分比",
            "persistence",
        ),
        (
            "auto-aof-rewrite-min-size",
            "AOF重写最小大小",
            "persistence",
        ),
        // 监控配置
        ("slowlog-log-slower-than", "慢查询阈值(微秒)", "monitoring"),
        ("slowlog-max-len", "慢查询日志长度", "monitoring"),
        ("latency-monitor-threshold", "延迟监控阈值", "monitoring"),
        // 常规配置
        ("databases", "数据库数量", "general"),
        ("loglevel", "日志级别", "general"),
        ("supervised", "进程管理器", "general"),
    ];

    match get_all_configs() {
        Ok(all_configs) => {
            let mut configs = Vec::new();

            for (key, desc, config_type) in common_config_keys {
                // 获取配置值，优先使用当前值，其次使用默认值，最后使用空字符串
                let value = all_configs
                    .get(key)
                    .cloned()
                    .filter(|v| !v.is_empty())
                    .or_else(|| get_config_default(key))
                    .unwrap_or_default();
                configs.push(RedisRuntimeConfig {
                    name: key.to_string(),
                    value,
                    description: desc.to_string(),
                    config_type: config_type.to_string(),
                });
            }

            RedisRuntimeConfigResponse {
                success: true,
                message: "获取配置成功".to_string(),
                configs,
            }
        }
        Err(e) => RedisRuntimeConfigResponse {
            success: false,
            message: format!("获取配置失败: {}", e),
            configs: Vec::new(),
        },
    }
}

/**
 * 更新单个配置项
 *
 * @param request 更新请求
 * @return 更新响应
 */
pub fn update_config(request: RedisRuntimeConfigUpdateRequest) -> RedisRuntimeConfigUpdateResponse {
    let mut updated = Vec::new();
    let mut failed = Vec::new();

    match set_config(&request.name, &request.value) {
        Ok(_) => {
            updated.push(request.name);
        }
        Err(e) => {
            failed.push((request.name, e));
        }
    }

    let success = !updated.is_empty();
    let message = if success {
        "配置更新成功".to_string()
    } else {
        "配置更新失败".to_string()
    };

    RedisRuntimeConfigUpdateResponse {
        success,
        message,
        updated_configs: updated,
        failed_configs: failed,
    }
}

/**
 * 批量更新配置项
 *
 * @param request 批量更新请求
 * @return 更新响应
 */
pub fn batch_update_configs(
    request: RedisRuntimeConfigBatchUpdateRequest,
) -> RedisRuntimeConfigUpdateResponse {
    let mut updated = Vec::new();
    let mut failed = Vec::new();

    for config in request.configs {
        match set_config(&config.name, &config.value) {
            Ok(_) => {
                updated.push(config.name);
            }
            Err(e) => {
                failed.push((config.name, e));
            }
        }
    }

    let success = !updated.is_empty() && failed.is_empty();
    let message = if failed.is_empty() {
        "所有配置更新成功".to_string()
    } else if updated.is_empty() {
        "所有配置更新失败".to_string()
    } else {
        format!(
            "部分配置更新成功: {}/{}失败",
            failed.len(),
            failed.len() + updated.len()
        )
    };

    RedisRuntimeConfigUpdateResponse {
        success,
        message,
        updated_configs: updated,
        failed_configs: failed,
    }
}

/**
 * 将运行时配置写入配置文件
 *
 * @return 操作结果
 */
pub fn rewrite_config_file() -> Result<(), String> {
    execute_redis_cli(&["CONFIG", "REWRITE"])?;
    Ok(())
}

/**
 * 获取内存使用情况
 *
 * @return 内存信息HashMap
 */
pub fn get_memory_info() -> Result<HashMap<String, String>, String> {
    let output = execute_redis_cli(&["INFO", "memory"])?;
    let mut info = HashMap::new();

    for line in output.lines() {
        if let Some(pos) = line.find(':') {
            let key = &line[..pos];
            let value = &line[pos + 1..];
            info.insert(key.to_string(), value.to_string());
        }
    }

    Ok(info)
}

/**
 * 获取客户端连接信息
 *
 * @return 客户端信息列表
 */
pub fn get_client_info() -> Result<Vec<HashMap<String, String>>, String> {
    let output = execute_redis_cli(&["CLIENT", "LIST"])?;
    let mut clients = Vec::new();

    for line in output.lines() {
        let mut client_info = HashMap::new();
        for part in line.split_whitespace() {
            if let Some(pos) = part.find('=') {
                let key = &part[..pos];
                let value = &part[pos + 1..];
                client_info.insert(key.to_string(), value.to_string());
            }
        }
        if !client_info.is_empty() {
            clients.push(client_info);
        }
    }

    Ok(clients)
}

// ============================================================================
// 配置更新（高层接口）
// ============================================================================

/**
 * 更新Redis配置
 *
 * 使用redis-cli动态修改配置，支持跨平台
 * 修改会立即生效，并通过CONFIG REWRITE保存到配置文件
 *
 * @param request 配置更新请求
 * @return 保存响应
 */
pub fn update_redis_config(request: RedisConfigUpdateRequest) -> RedisConfigSaveResponse {
    use crate::services::redis::lifecycle::check_redis_status;

    let client_config = match config::load_config() {
        Ok(c) => c,
        Err(e) => {
            return RedisConfigSaveResponse {
                success: false,
                message: format!("加载配置失败: {}", e),
                config_reloaded: false,
            };
        }
    };

    let redis_config = &client_config.redis;

    if !redis_config.is_loaded {
        return RedisConfigSaveResponse {
            success: false,
            message: "Redis未载入".to_string(),
            config_reloaded: false,
        };
    }

    // 检查Redis是否正在运行（使用实时状态检查）
    let current_status = check_redis_status();
    if current_status != "running" {
        return RedisConfigSaveResponse {
            success: false,
            message: "Redis未运行，请先启动Redis".to_string(),
            config_reloaded: false,
        };
    }

    let mut updated_configs = Vec::new();
    let mut failed_configs = Vec::new();

    // 更新端口
    if let Some(port) = request.port {
        match set_config("port", &port.to_string()) {
            Ok(_) => {
                updated_configs.push("port".to_string());
            }
            Err(e) => {
                failed_configs.push(("port".to_string(), e));
            }
        }
    }

    // 更新密码认证
    if let Some(require_pass) = request.require_pass {
        if require_pass {
            if let Some(ref password) = request.password {
                match set_config("requirepass", password) {
                    Ok(_) => {
                        updated_configs.push("requirepass".to_string());
                    }
                    Err(e) => {
                        failed_configs.push(("requirepass".to_string(), e));
                    }
                }
            }
        } else {
            // 禁用密码认证 - 设置为空字符串
            match set_config("requirepass", "") {
                Ok(_) => {
                    updated_configs.push("requirepass".to_string());
                }
                Err(e) => {
                    failed_configs.push(("requirepass".to_string(), e));
                }
            }
        }
    }

    // 保存到客户端配置
    let mut new_config = client_config.clone();
    if let Some(port) = request.port {
        new_config.redis.port = port;
    }
    if let Some(require_pass) = request.require_pass {
        new_config.redis.require_pass = require_pass;
        if require_pass {
            if let Some(password) = request.password {
                new_config.redis.password = Some(password);
            }
        } else {
            new_config.redis.password = None;
        }
    }
    if let Some(data_dir) = request.data_dir {
        new_config.redis.data_dir = Some(data_dir.clone());
    }

    // 保存配置到文件
    if let Err(e) = config::save_config(&new_config) {
        return RedisConfigSaveResponse {
            success: false,
            message: format!("保存配置失败: {}", e),
            config_reloaded: false,
        };
    }

    // 执行CONFIG REWRITE将配置保存到Redis配置文件
    let config_reloaded = if failed_configs.is_empty() {
        match rewrite_config_file() {
            Ok(_) => true,
            Err(e) => {
                failed_configs.push(("CONFIG REWRITE".to_string(), e));
                false
            }
        }
    } else {
        false
    };

    let message = if failed_configs.is_empty() {
        "配置已更新并保存".to_string()
    } else if updated_configs.is_empty() {
        format!("配置更新失败: {}", failed_configs[0].1)
    } else {
        format!("部分配置更新成功，{}个失败", failed_configs.len())
    };

    RedisConfigSaveResponse {
        success: !updated_configs.is_empty(),
        message,
        config_reloaded,
    }
}
