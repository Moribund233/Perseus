/**
 * Windows Redis服务管理模块
 *
 * 管理Redis作为Windows服务的安装、卸载、启动和停止
 * 同时管理PATH环境变量的添加和移除
 */
use std::path::Path;
use std::process::Command;

use crate::core::config;
use crate::models::WindowsServiceResponse;

/// Redis服务名称
const REDIS_SERVICE_NAME: &str = "Redis";

/**
 * 解码Windows命令行输出
 * Windows命令行使用GBK编码，需要转换为UTF-8
 *
 * @param bytes 原始字节
 * @return 解码后的字符串
 */
fn decode_windows_output(bytes: &[u8]) -> String {
    // 首先尝试UTF-8解码
    if let Ok(s) = String::from_utf8(bytes.to_vec()) {
        return s;
    }
    // 如果失败，尝试GBK解码
    let (s, _) = encoding_rs::GBK.decode_without_bom_handling(bytes);
    s.to_string()
}

/**
 * 安装Redis为Windows服务
 *
 * @param exe_dir Redis可执行文件目录
 * @return 操作响应
 */
pub fn install_redis_service(exe_dir: &str) -> WindowsServiceResponse {
    let redis_server_path = Path::new(exe_dir).join("redis-server.exe");

    if !redis_server_path.exists() {
        return WindowsServiceResponse {
            success: false,
            message: format!("redis-server.exe不存在: {}", redis_server_path.display()),
            is_installed: false,
        };
    }

    // 检查服务是否已存在
    if is_redis_service_installed() {
        return WindowsServiceResponse {
            success: true,
            message: "Redis服务已安装".to_string(),
            is_installed: true,
        };
    }

    // 使用redis-server --service-install安装服务
    let config_path = Path::new(exe_dir).join("redis.conf");
    let config_arg = if config_path.exists() {
        config_path.to_string_lossy().to_string()
    } else {
        // 创建基本配置文件
        match create_basic_config(exe_dir) {
            Ok(path) => path,
            Err(e) => {
                return WindowsServiceResponse {
                    success: false,
                    message: format!("创建配置文件失败: {}", e),
                    is_installed: false,
                }
            }
        }
    };

    match Command::new(&redis_server_path)
        .args(["--service-install", &config_arg, "--loglevel", "verbose"])
        .output()
    {
        Ok(output) => {
            if output.status.success() {
                // 添加目录到PATH
                if let Err(e) = add_to_path(exe_dir) {
                    return WindowsServiceResponse {
                        success: false,
                        message: format!("服务安装成功但添加PATH失败: {}", e),
                        is_installed: true,
                    };
                }

                // 更新配置
                if let Ok(mut client_config) = config::load_config() {
                    client_config.redis.is_windows_service = true;
                    let _ = config::save_config(&client_config);
                }

                WindowsServiceResponse {
                    success: true,
                    message: "Redis服务安装成功".to_string(),
                    is_installed: true,
                }
            } else {
                let stderr = String::from_utf8_lossy(&output.stderr);
                WindowsServiceResponse {
                    success: false,
                    message: format!("安装服务失败: {}", stderr),
                    is_installed: false,
                }
            }
        }
        Err(e) => WindowsServiceResponse {
            success: false,
            message: format!("执行安装命令失败: {}", e),
            is_installed: false,
        },
    }
}

/**
 * 卸载Redis Windows服务
 *
 * @return 操作响应
 */
pub fn uninstall_redis_service() -> WindowsServiceResponse {
    if !is_redis_service_installed() {
        return WindowsServiceResponse {
            success: true,
            message: "Redis服务未安装".to_string(),
            is_installed: false,
        };
    }

    // 先停止服务
    let _ = stop_redis_service(REDIS_SERVICE_NAME);

    // 获取Redis目录用于从PATH移除
    let exe_dir = config::load_config().ok().and_then(|c| c.redis.exe_dir);

    // 使用sc命令卸载服务
    match Command::new("sc")
        .args(["delete", REDIS_SERVICE_NAME])
        .output()
    {
        Ok(output) => {
            if output.status.success() {
                // 从PATH移除
                if let Some(dir) = &exe_dir {
                    let _ = remove_from_path(dir);
                }

                // 更新配置
                if let Ok(mut client_config) = config::load_config() {
                    client_config.redis.is_windows_service = false;
                    let _ = config::save_config(&client_config);
                }

                WindowsServiceResponse {
                    success: true,
                    message: "Redis服务已卸载".to_string(),
                    is_installed: false,
                }
            } else {
                let stderr = String::from_utf8_lossy(&output.stderr);
                WindowsServiceResponse {
                    success: false,
                    message: format!("卸载服务失败: {}", stderr),
                    is_installed: true,
                }
            }
        }
        Err(e) => WindowsServiceResponse {
            success: false,
            message: format!("执行卸载命令失败: {}", e),
            is_installed: true,
        },
    }
}

/**
 * 启动Redis服务
 *
 * @param service_name 服务名称
 * @return 操作结果
 */
pub fn start_redis_service(service_name: &str) -> Result<(), String> {
    match Command::new("net").args(["start", service_name]).output() {
        Ok(output) => {
            if output.status.success() {
                Ok(())
            } else {
                // Windows命令行使用GBK编码，需要转换
                let stderr = decode_windows_output(&output.stderr);

                // 检查是否是权限错误（系统错误5）
                if stderr.contains("系统错误 5") || stderr.contains("拒绝访问") {
                    Err("启动服务失败: 需要管理员权限。请右键点击应用程序选择'以管理员身份运行'，或使用服务管理器手动启动服务。".to_string())
                } else {
                    Err(format!("启动服务失败: {}", stderr))
                }
            }
        }
        Err(e) => Err(format!("执行启动命令失败: {}", e)),
    }
}

/**
 * 停止Redis服务
 *
 * @param service_name 服务名称
 * @return 操作结果
 */
pub fn stop_redis_service(service_name: &str) -> Result<(), String> {
    match Command::new("net").args(["stop", service_name]).output() {
        Ok(output) => {
            if output.status.success() {
                Ok(())
            } else {
                // Windows命令行使用GBK编码，需要转换
                let stderr = decode_windows_output(&output.stderr);

                // 检查是否是权限错误（系统错误5）
                if stderr.contains("系统错误 5") || stderr.contains("拒绝访问") {
                    Err("停止服务失败: 需要管理员权限。请右键点击应用程序选择'以管理员身份运行'，或使用服务管理器手动停止服务。".to_string())
                } else {
                    Err(format!("停止服务失败: {}", stderr))
                }
            }
        }
        Err(e) => Err(format!("执行停止命令失败: {}", e)),
    }
}

/**
 * 检查Redis服务是否已安装
 *
 * @return 是否已安装
 */
pub fn is_redis_service_installed() -> bool {
    match Command::new("sc")
        .args(["query", REDIS_SERVICE_NAME])
        .output()
    {
        Ok(output) => output.status.success(),
        Err(_) => false,
    }
}

/**
 * 检查Redis服务是否正在运行
 *
 * @return 是否运行中
 */
pub fn is_redis_service_running() -> Result<bool, String> {
    match Command::new("sc")
        .args(["query", REDIS_SERVICE_NAME])
        .output()
    {
        Ok(output) => {
            if !output.status.success() {
                return Err("服务未安装".to_string());
            }
            let stdout = String::from_utf8_lossy(&output.stdout);
            Ok(stdout.contains("RUNNING"))
        }
        Err(e) => Err(format!("查询服务状态失败: {}", e)),
    }
}

/**
 * 添加目录到系统PATH环境变量
 *
 * @param dir 要添加的目录
 * @return 操作结果
 */
pub fn add_to_path(dir: &str) -> Result<(), String> {
    // 获取当前用户PATH
    let current_path = match Command::new("powershell")
        .args([
            "-Command",
            "[Environment]::GetEnvironmentVariable('PATH', 'User')",
        ])
        .output()
    {
        Ok(output) => String::from_utf8_lossy(&output.stdout).trim().to_string(),
        Err(e) => return Err(format!("获取PATH失败: {}", e)),
    };

    // 检查是否已存在
    let dir_with_sep = format!("{};", dir);
    if current_path.contains(&dir_with_sep) || current_path.ends_with(dir) {
        return Ok(());
    }

    // 添加新目录到PATH
    let new_path = format!("{};{}", current_path, dir);

    match Command::new("powershell")
        .args([
            "-Command",
            &format!(
                "[Environment]::SetEnvironmentVariable('PATH', '{}', 'User')",
                new_path
            ),
        ])
        .output()
    {
        Ok(output) => {
            if output.status.success() {
                Ok(())
            } else {
                let stderr = String::from_utf8_lossy(&output.stderr);
                Err(format!("设置PATH失败: {}", stderr))
            }
        }
        Err(e) => Err(format!("执行PATH设置命令失败: {}", e)),
    }
}

/**
 * 从系统PATH环境变量移除目录
 *
 * @param dir 要移除的目录
 * @return 操作结果
 */
pub fn remove_from_path(dir: &str) -> Result<(), String> {
    // 获取当前用户PATH
    let current_path = match Command::new("powershell")
        .args([
            "-Command",
            "[Environment]::GetEnvironmentVariable('PATH', 'User')",
        ])
        .output()
    {
        Ok(output) => String::from_utf8_lossy(&output.stdout).trim().to_string(),
        Err(e) => return Err(format!("获取PATH失败: {}", e)),
    };

    // 移除目录
    let dir_with_sep = format!("{};", dir);
    let new_path = current_path.replace(&dir_with_sep, "").replace(dir, "");

    // 清理多余的连续分号
    let new_path = new_path.replace(";;", ";");

    match Command::new("powershell")
        .args([
            "-Command",
            &format!(
                "[Environment]::SetEnvironmentVariable('PATH', '{}', 'User')",
                new_path
            ),
        ])
        .output()
    {
        Ok(output) => {
            if output.status.success() {
                Ok(())
            } else {
                let stderr = String::from_utf8_lossy(&output.stderr);
                Err(format!("设置PATH失败: {}", stderr))
            }
        }
        Err(e) => Err(format!("执行PATH设置命令失败: {}", e)),
    }
}

/**
 * 创建基本Redis配置文件
 *
 * @param exe_dir Redis可执行文件目录
 * @return 配置文件路径
 */
fn create_basic_config(exe_dir: &str) -> Result<String, String> {
    let config_path = Path::new(exe_dir).join("redis.conf");

    let config_content = r#"# Redis基本配置文件
# 由LanGit自动生成

# 绑定地址
bind 127.0.0.1

# 监听端口
port 6379

# 保护模式
protected-mode yes

# 数据目录
dir ./

# 日志文件
logfile ""

# 数据库数量
databases 16

# 持久化配置
save 900 1
save 300 10
save 60 10000

# 启用AOF持久化
appendonly yes
appendfilename "appendonly.aof"

# 守护进程模式（Windows服务不需要）
daemonize no
"#;

    std::fs::write(&config_path, config_content).map_err(|e| format!("写入配置文件失败: {}", e))?;

    Ok(config_path.to_string_lossy().to_string())
}
