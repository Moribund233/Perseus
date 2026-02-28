/**
 * Redis配置管理模块
 *
 * 管理Redis配置的读取、修改和保存
 * 使用redis-cli命令进行跨平台的配置管理
 */
use std::fs;
use std::path::Path;
use std::process::Command;

use crate::core::config;
use crate::models::{RedisActionResponse, RedisConfigSaveResponse, RedisConfigUpdateRequest};

/// 检查是否为Windows平台
fn is_windows() -> bool {
    cfg!(target_os = "windows")
}

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

    // 读取当前配置
    let (port, require_pass, password) = if let Some(ref config_file) = config_path {
        parse_redis_config(config_file)
    } else {
        (6379, false, None)
    };

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

/**
 * 更新Redis配置
 *
 * @param request 配置更新请求
 * @return 保存响应
 */
pub fn update_redis_config(request: RedisConfigUpdateRequest) -> RedisConfigSaveResponse {
    match config::load_config() {
        Ok(mut client_config) => {
            let mut config_reloaded = false;

            // 更新端口
            if let Some(port) = request.port {
                client_config.redis.port = port;
            }

            // 尝试更新配置文件（在移动值之前克隆）
            let config_port = request.port;
            let config_require_pass = request.require_pass;
            let config_password = request.password.clone();
            let config_data_dir = request.data_dir.clone();

            // 更新认证设置
            if let Some(require_pass) = request.require_pass {
                client_config.redis.require_pass = require_pass;
            }

            // 更新密码
            if let Some(password) = request.password {
                client_config.redis.password = Some(password);
            }

            // 更新数据目录
            if let Some(data_dir) = request.data_dir {
                client_config.redis.data_dir = Some(data_dir);
            }

            if let Some(ref config_path) = client_config.redis.config_path {
                if Path::new(config_path).exists() {
                    match modify_redis_config_file(
                        config_path,
                        config_port,
                        config_require_pass,
                        config_password,
                        config_data_dir,
                    ) {
                        Ok(_) => {
                            config_reloaded = true;
                        }
                        Err(e) => {
                            return RedisConfigSaveResponse {
                                success: false,
                                message: format!("修改配置文件失败: {}", e),
                                config_reloaded: false,
                            };
                        }
                    }
                }
            }

            // 保存配置
            match config::save_config(&client_config) {
                Ok(_) => RedisConfigSaveResponse {
                    success: true,
                    message: "配置已保存".to_string(),
                    config_reloaded,
                },
                Err(e) => RedisConfigSaveResponse {
                    success: false,
                    message: format!("保存配置失败: {}", e),
                    config_reloaded: false,
                },
            }
        }
        Err(e) => RedisConfigSaveResponse {
            success: false,
            message: format!("加载配置失败: {}", e),
            config_reloaded: false,
        },
    }
}

/**
 * 使用redis-cli动态修改配置（无需重启）
 *
 * @param config 配置项名称
 * @param value 配置值
 * @return 操作结果
 */
#[allow(dead_code)]
pub fn set_runtime_config(config: &str, value: &str) -> Result<(), String> {
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

    let mut cmd = Command::new(&redis_cli_path);
    cmd.arg("-p")
        .arg(redis_config.port.to_string())
        .arg("CONFIG")
        .arg("SET")
        .arg(config)
        .arg(value);

    // 如果有密码，添加认证
    if redis_config.require_pass {
        if let Some(password) = &redis_config.password {
            cmd.arg("-a").arg(password);
        }
    }

    match cmd.output() {
        Ok(output) => {
            if output.status.success() {
                Ok(())
            } else {
                let stderr = String::from_utf8_lossy(&output.stderr);
                Err(format!("设置配置失败: {}", stderr))
            }
        }
        Err(e) => Err(format!("执行redis-cli失败: {}", e)),
    }
}

/**
 * 使用redis-cli获取运行时配置
 *
 * @param config 配置项名称
 * @return 配置值
 */
#[allow(dead_code)]
pub fn get_runtime_config(config: &str) -> Result<String, String> {
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

    let mut cmd = Command::new(&redis_cli_path);
    cmd.arg("-p")
        .arg(redis_config.port.to_string())
        .arg("CONFIG")
        .arg("GET")
        .arg(config);

    // 如果有密码，添加认证
    if redis_config.require_pass {
        if let Some(password) = &redis_config.password {
            cmd.arg("-a").arg(password);
        }
    }

    match cmd.output() {
        Ok(output) => {
            if output.status.success() {
                let stdout = String::from_utf8_lossy(&output.stdout);
                Ok(stdout.trim().to_string())
            } else {
                let stderr = String::from_utf8_lossy(&output.stderr);
                Err(format!("获取配置失败: {}", stderr))
            }
        }
        Err(e) => Err(format!("执行redis-cli失败: {}", e)),
    }
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

/**
 * 解析Redis配置文件
 *
 * @param config_path 配置文件路径
 * @return (端口, 是否需要认证, 密码)
 */
fn parse_redis_config(config_path: &str) -> (u16, bool, Option<String>) {
    let content = match fs::read_to_string(config_path) {
        Ok(c) => c,
        Err(_) => return (6379, false, None),
    };

    let mut port = 6379u16;
    let mut require_pass = false;
    let mut password = None;

    for line in content.lines() {
        let line = line.trim();

        // 跳过注释和空行
        if line.starts_with('#') || line.is_empty() {
            continue;
        }

        // 解析端口
        if line.starts_with("port ") {
            if let Some(value) = line.split_whitespace().nth(1) {
                if let Ok(p) = value.parse::<u16>() {
                    port = p;
                }
            }
        }

        // 解析密码
        if line.starts_with("requirepass ") {
            if let Some(value) = line.split_whitespace().nth(1) {
                require_pass = true;
                password = Some(value.to_string());
            }
        }
    }

    (port, require_pass, password)
}

/**
 * 修改Redis配置文件
 *
 * @param config_path 配置文件路径
 * @param port 端口
 * @param require_pass 是否需要认证
 * @param password 密码
 * @param data_dir 数据目录
 * @return 操作结果
 */
fn modify_redis_config_file(
    config_path: &str,
    port: Option<u16>,
    require_pass: Option<bool>,
    password: Option<String>,
    data_dir: Option<String>,
) -> Result<(), String> {
    let content =
        fs::read_to_string(config_path).map_err(|e| format!("读取配置文件失败: {}", e))?;

    let mut new_lines: Vec<String> = Vec::new();
    let mut port_updated = port.is_none();
    let mut pass_updated = require_pass.is_none() && password.is_none();
    let mut dir_updated = data_dir.is_none();

    for line in content.lines() {
        let trimmed = line.trim();

        // 更新端口
        if !port_updated && trimmed.starts_with("port ") {
            if let Some(p) = port {
                new_lines.push(format!("port {}", p));
                port_updated = true;
                continue;
            }
        }

        // 更新密码
        if !pass_updated && trimmed.starts_with("requirepass ") {
            if let Some(req) = require_pass {
                if req {
                    if let Some(ref pwd) = password {
                        new_lines.push(format!("requirepass {}", pwd));
                    } else {
                        new_lines.push(line.to_string());
                    }
                } else {
                    new_lines.push(format!("# {}", line));
                }
                pass_updated = true;
                continue;
            }
        }

        // 更新数据目录
        if !dir_updated && trimmed.starts_with("dir ") {
            if let Some(ref d) = data_dir {
                new_lines.push(format!("dir \"{}\"", d));
                dir_updated = true;
                continue;
            }
        }

        new_lines.push(line.to_string());
    }

    // 如果配置项不存在，添加到文件末尾
    if !port_updated {
        if let Some(p) = port {
            new_lines.push(format!("port {}", p));
        }
    }

    if !pass_updated {
        if let Some(req) = require_pass {
            if req {
                if let Some(ref pwd) = password {
                    new_lines.push(format!("requirepass {}", pwd));
                }
            }
        }
    }

    if !dir_updated {
        if let Some(ref d) = data_dir {
            new_lines.push(format!("dir \"{}\"", d));
        }
    }

    fs::write(config_path, new_lines.join("\n")).map_err(|e| format!("写入配置文件失败: {}", e))?;

    Ok(())
}
