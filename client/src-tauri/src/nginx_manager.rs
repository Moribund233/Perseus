/**
 * Nginx管理模块
 *
 * 管理Nginx的生命周期、配置和下载
 * 支持Windows和Linux平台
 */
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::Mutex;

use crate::config;
use crate::models::{NginxActionResponse, NginxConfig, NginxPlatformInfo, NginxStatusResponse};

/// 检查是否为Windows平台
pub fn is_windows() -> bool {
    cfg!(target_os = "windows")
}

/// 检查是否为Linux平台
pub fn is_linux() -> bool {
    cfg!(target_os = "linux")
}

/**
 * 获取Nginx平台信息
 *
 * @return 平台信息
 */
pub fn get_nginx_platform_info() -> NginxPlatformInfo {
    let platform = std::env::consts::OS.to_string();

    match platform.as_str() {
        "windows" => NginxPlatformInfo {
            platform,
            supports_manual_load: true,
            supports_download: true,
            uses_package_manager: false,
            package_manager: None,
            package_version: None,
            config_path: None,
        },
        "linux" => {
            let (package_manager, package_version, config_path) = detect_linux_nginx();
            NginxPlatformInfo {
                platform,
                supports_manual_load: false,
                supports_download: false,
                uses_package_manager: true,
                package_manager,
                package_version,
                config_path,
            }
        }
        _ => NginxPlatformInfo {
            platform,
            supports_manual_load: false,
            supports_download: false,
            uses_package_manager: false,
            package_manager: None,
            package_version: None,
            config_path: None,
        },
    }
}

/**
 * 检测Linux系统上的Nginx信息
 *
 * @return (包管理器, 版本, 配置文件路径)
 */
fn detect_linux_nginx() -> (Option<String>, Option<String>, Option<String>) {
    // 检测包管理器
    let package_manager = detect_package_manager();

    // 获取Nginx版本
    let version = get_linux_nginx_version();

    // 检测配置文件路径
    let config_path = detect_nginx_config_path();

    (package_manager, version, config_path)
}

/**
 * 检测Linux包管理器
 *
 * @return 包管理器名称
 */
fn detect_package_manager() -> Option<String> {
    // 检测常见的包管理器
    let managers = vec![
        ("/usr/bin/apt", "apt"),
        ("/usr/bin/apt-get", "apt"),
        ("/usr/bin/yum", "yum"),
        ("/usr/bin/dnf", "dnf"),
        ("/usr/bin/pacman", "pacman"),
        ("/sbin/apk", "apk"),
    ];

    for (path, name) in managers {
        if Path::new(path).exists() {
            return Some(name.to_string());
        }
    }

    None
}

/**
 * 获取Linux系统上Nginx的版本
 *
 * @return 版本信息
 */
fn get_linux_nginx_version() -> Option<String> {
    // 尝试执行nginx -v
    if let Ok(output) = Command::new("nginx").arg("-v").output() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);

        let version_info = if stderr.contains("nginx") {
            stderr.to_string()
        } else if stdout.contains("nginx") {
            stdout.to_string()
        } else {
            return None;
        };

        return version_info.lines().next().map(|s| s.trim().to_string());
    }

    None
}

/**
 * 检测Nginx配置文件路径
 *
 * @return 配置文件路径
 */
fn detect_nginx_config_path() -> Option<String> {
    // 常见的Nginx配置文件路径
    let common_paths = vec![
        "/etc/nginx/nginx.conf",
        "/usr/local/nginx/conf/nginx.conf",
        "/opt/nginx/conf/nginx.conf",
    ];

    for path in common_paths {
        if Path::new(path).exists() {
            return Some(path.to_string());
        }
    }

    None
}

/// Nginx管理器状态
pub struct NginxManagerState {
    pub config: Mutex<NginxConfig>,
}

impl Default for NginxManagerState {
    fn default() -> Self {
        let config = config::load_config().map(|c| c.nginx).unwrap_or_default();
        Self {
            config: Mutex::new(config),
        }
    }
}

/// 构建成功响应
fn success_response_with_status(
    message: impl Into<String>,
    status: impl Into<String>,
    pid: Option<u32>,
) -> NginxActionResponse {
    NginxActionResponse {
        success: true,
        message: message.into(),
        status: Some(status.into()),
        pid,
    }
}

/// 构建错误响应
fn error_response(message: impl Into<String>) -> NginxActionResponse {
    NginxActionResponse {
        success: false,
        message: message.into(),
        status: None,
        pid: None,
    }
}

/// 构建带状态的错误响应
fn error_response_with_status(
    message: impl Into<String>,
    status: impl Into<String>,
    pid: Option<u32>,
) -> NginxActionResponse {
    NginxActionResponse {
        success: false,
        message: message.into(),
        status: Some(status.into()),
        pid,
    }
}

/**
 * 验证Nginx可执行文件是否有效
 *
 * @param exe_path Nginx可执行文件路径
 * @return 验证结果，成功返回版本信息
 */
pub fn validate_nginx(exe_path: &str) -> Result<String, String> {
    let path = Path::new(exe_path);

    // 检查文件是否存在
    if !path.exists() {
        return Err(format!("Nginx可执行文件不存在: {}", exe_path));
    }

    // 检查是否是文件
    if !path.is_file() {
        return Err(format!("路径不是文件: {}", exe_path));
    }

    // 执行nginx -v获取版本信息
    let output = Command::new(exe_path)
        .arg("-v")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|e| format!("执行Nginx验证失败: {}", e))?;

    // Nginx将版本信息输出到stderr
    let version_output = String::from_utf8_lossy(&output.stderr);
    let stdout_output = String::from_utf8_lossy(&output.stdout);

    let version_info = if version_output.contains("nginx") {
        version_output.to_string()
    } else if stdout_output.contains("nginx") {
        stdout_output.to_string()
    } else {
        return Err("无法获取Nginx版本信息，文件可能不是有效的Nginx可执行文件".to_string());
    };

    // 提取版本号
    let version = version_info
        .lines()
        .next()
        .unwrap_or("nginx")
        .trim()
        .to_string();

    Ok(version)
}

/**
 * 从路径推断Nginx配置目录
 *
 * @param exe_path Nginx可执行文件路径
 * @return 配置目录路径
 */
pub fn infer_config_dir(exe_path: &str) -> Option<String> {
    let path = Path::new(exe_path);

    // 尝试从可执行文件所在目录的父目录查找conf目录
    if let Some(parent) = path.parent() {
        // 尝试 ../conf
        let conf_dir = parent.join("conf");
        if conf_dir.exists() && conf_dir.is_dir() {
            return Some(conf_dir.to_string_lossy().to_string());
        }

        // 尝试 ../../conf (如果exe在sbin或bin目录)
        if let Some(grandparent) = parent.parent() {
            let conf_dir = grandparent.join("conf");
            if conf_dir.exists() && conf_dir.is_dir() {
                return Some(conf_dir.to_string_lossy().to_string());
            }
        }
    }

    None
}

/**
 * 载入Nginx
 *
 * @param exe_path Nginx可执行文件路径
 * @return 操作响应
 */
pub fn load_nginx(exe_path: String) -> NginxActionResponse {
    let version = match validate_nginx(&exe_path) {
        Ok(v) => v,
        Err(e) => return error_response(e),
    };

    let config_dir = infer_config_dir(&exe_path);
    let mut client_config = match config::load_config() {
        Ok(c) => c,
        Err(e) => return error_response(format!("加载配置失败: {}", e)),
    };

    client_config.nginx.exe_path = Some(exe_path.clone());
    client_config.nginx.config_dir = config_dir;
    client_config.nginx.is_loaded = true;
    client_config.nginx.version = Some(version.clone());

    // 检查Nginx是否已经在运行
    if let Some(pid) = find_nginx_process(&exe_path) {
        client_config.nginx.status = "running".to_string();
        client_config.nginx.pid = Some(pid);
    } else {
        client_config.nginx.status = "stopped".to_string();
        client_config.nginx.pid = None;
    }

    if let Err(e) = config::save_config(&client_config) {
        return error_response(format!("保存配置失败: {}", e));
    }

    success_response_with_status(
        format!("Nginx载入成功: {}", version),
        client_config.nginx.status,
        client_config.nginx.pid,
    )
}

/// 从进程列表中查找主进程（没有父进程或父进程不在列表中的进程）
fn find_master_process(processes: &[(u32, Option<u32>)]) -> Option<u32> {
    for (pid, parent_pid) in processes {
        let is_master = parent_pid.map_or(true, |ppid| !processes.iter().any(|(p, _)| *p == ppid));
        if is_master {
            return Some(*pid);
        }
    }
    processes.first().map(|(pid, _)| *pid)
}

/**
 * 查找Nginx进程
 *
 * @param exe_path Nginx可执行文件路径（Windows）或空字符串（Linux使用系统命令）
 * @return 进程ID
 */
pub fn find_nginx_process(exe_path: &str) -> Option<u32> {
    use sysinfo::{ProcessRefreshKind, RefreshKind, System};

    let s = System::new_with_specifics(
        RefreshKind::new().with_processes(ProcessRefreshKind::everything()),
    );

    let mut matched_processes: Vec<(u32, Option<u32>)> = Vec::new();

    if is_linux() {
        // Linux平台：直接按进程名查找
        for (pid, process) in s.processes() {
            if process.name().to_lowercase() == "nginx" {
                matched_processes.push((pid.as_u32(), process.parent().map(|p| p.as_u32())));
            }
        }
    } else {
        // Windows平台：使用exe_path匹配
        let exe_path_canonical = if exe_path.is_empty() {
            None
        } else {
            Some(
                std::fs::canonicalize(exe_path)
                    .map(|p| p.to_string_lossy().to_lowercase())
                    .unwrap_or_else(|_| exe_path.to_lowercase()),
            )
        };

        let exe_name = if exe_path.is_empty() {
            "nginx.exe".to_string()
        } else {
            Path::new(exe_path)
                .file_name()
                .map(|n| n.to_string_lossy().to_lowercase())
                .unwrap_or_else(|| "nginx.exe".to_string())
        };

        for (pid, process) in s.processes() {
            let process_exe = process.exe().map(|p| p.to_string_lossy().to_lowercase());
            let process_name = process.name().to_lowercase();

            let matched = match &process_exe {
                Some(pe) => match &exe_path_canonical {
                    Some(canonical) => pe == canonical || pe.contains(&exe_name),
                    None => pe.contains(&exe_name),
                },
                None => process_name == exe_name || process_name == "nginx",
            };

            if matched {
                matched_processes.push((pid.as_u32(), process.parent().map(|p| p.as_u32())));
            }
        }
    }

    find_master_process(&matched_processes)
}

/**
 * 获取Nginx状态
 *
 * @return 状态响应
 */
pub fn get_nginx_status() -> NginxStatusResponse {
    // Linux平台：自动检测Nginx状态
    if is_linux() {
        return get_linux_nginx_status();
    }

    match config::load_config() {
        Ok(client_config) => {
            let nginx = client_config.nginx;

            // 如果已载入，检查进程状态
            let (status, pid) = if nginx.is_loaded {
                if let Some(ref exe_path_ref) = nginx.exe_path {
                    if let Some(found_pid) = find_nginx_process(exe_path_ref) {
                        ("running".to_string(), Some(found_pid))
                    } else {
                        ("stopped".to_string(), None)
                    }
                } else {
                    (nginx.status, nginx.pid)
                }
            } else {
                (nginx.status, nginx.pid)
            };

            NginxStatusResponse {
                is_loaded: nginx.is_loaded,
                status,
                pid,
                version: nginx.version,
                exe_path: nginx.exe_path,
                config_dir: nginx.config_dir,
            }
        }
        Err(_) => NginxStatusResponse {
            is_loaded: false,
            status: "stopped".to_string(),
            pid: None,
            version: None,
            exe_path: None,
            config_dir: None,
        },
    }
}

/**
 * 获取Linux系统上的Nginx状态
 *
 * @return 状态响应
 */
fn get_linux_nginx_status() -> NginxStatusResponse {
    let platform_info = get_nginx_platform_info();

    // 检测Nginx进程
    let pid = find_nginx_process("");
    let is_running = pid.is_some();

    // 获取配置目录（优先使用用户目录下的配置）
    let config_dir = get_nginx_config_dir().or_else(|| {
        platform_info
            .config_path
            .as_ref()
            .and_then(|p| Path::new(p).parent())
            .map(|p| p.to_string_lossy().to_string())
    });

    NginxStatusResponse {
        is_loaded: is_running || platform_info.package_version.is_some(),
        status: if is_running {
            "running".to_string()
        } else {
            "stopped".to_string()
        },
        pid,
        version: platform_info.package_version,
        exe_path: Some("/usr/sbin/nginx".to_string()),
        config_dir,
    }
}

/// 获取Nginx工作目录
fn get_nginx_work_dir(exe_path: &str) -> Option<PathBuf> {
    Path::new(exe_path).parent().map(|parent| {
        if parent
            .file_name()
            .map(|n| n == "sbin" || n == "bin")
            .unwrap_or(false)
        {
            parent.parent().unwrap_or(parent).to_path_buf()
        } else {
            parent.to_path_buf()
        }
    })
}

/**
 * 启动Nginx
 *
 * @return 操作响应
 */
pub fn start_nginx() -> NginxActionResponse {
    if is_linux() {
        return start_linux_nginx();
    }

    let config = match config::load_config() {
        Ok(c) => c.nginx,
        Err(e) => return error_response(format!("加载配置失败: {}", e)),
    };

    if !config.is_loaded {
        return error_response_with_status("Nginx未载入，请先载入Nginx", "stopped", None);
    }

    let exe_path = match &config.exe_path {
        Some(p) => p.clone(),
        None => return error_response_with_status("Nginx可执行文件路径未设置", "stopped", None),
    };

    if let Some(pid) = find_nginx_process(&exe_path) {
        return success_response_with_status(
            format!("Nginx已经在运行中 (PID: {})", pid),
            "running",
            Some(pid),
        );
    }

    let mut cmd = Command::new(&exe_path);

    if let Some(work_dir) = get_nginx_work_dir(&exe_path) {
        cmd.current_dir(work_dir);
    }

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NEW_PROCESS_GROUP: u32 = 0x00000200;
        const DETACHED_PROCESS: u32 = 0x00000008;
        cmd.creation_flags(CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS);
    }

    match cmd.stdout(Stdio::null()).stderr(Stdio::null()).spawn() {
        Ok(_) => {
            std::thread::sleep(std::time::Duration::from_millis(800));

            match find_nginx_process(&exe_path) {
                Some(pid) => {
                    if let Ok(mut client_config) = config::load_config() {
                        client_config.nginx.status = "running".to_string();
                        client_config.nginx.pid = Some(pid);
                        let _ = config::save_config(&client_config);
                    }
                    success_response_with_status(
                        format!("Nginx启动成功 (PID: {})", pid),
                        "running",
                        Some(pid),
                    )
                }
                None => error_response_with_status("Nginx进程启动后未检测到运行", "error", None),
            }
        }
        Err(e) => error_response_with_status(format!("启动Nginx失败: {}", e), "error", None),
    }
}

/**
 * 启动Linux系统上的Nginx
 *
 * @return 操作响应
 */
fn start_linux_nginx() -> NginxActionResponse {
    if let Some(pid) = find_nginx_process("") {
        return success_response_with_status(
            format!("Nginx已经在运行中 (PID: {})", pid),
            "running",
            Some(pid),
        );
    }

    let mut cmd = Command::new("nginx");
    cmd.stdout(Stdio::null()).stderr(Stdio::null());

    if let Some(ref conf_path) = get_nginx_config_path() {
        if conf_path.exists() {
            cmd.arg("-c").arg(conf_path);
        }
    }

    match cmd.spawn() {
        Ok(_) => {
            std::thread::sleep(std::time::Duration::from_millis(800));
            match find_nginx_process("") {
                Some(pid) => success_response_with_status(
                    format!("Nginx启动成功 (PID: {})", pid),
                    "running",
                    Some(pid),
                ),
                None => error_response_with_status("Nginx进程启动后未检测到运行", "error", None),
            }
        }
        Err(e) => error_response_with_status(format!("启动Nginx失败: {}", e), "error", None),
    }
}

/// 更新Nginx状态到配置
fn update_nginx_status(status: &str, pid: Option<u32>) {
    if let Ok(mut client_config) = config::load_config() {
        client_config.nginx.status = status.to_string();
        client_config.nginx.pid = pid;
        let _ = config::save_config(&client_config);
    }
}

/**
 * 停止Nginx
 *
 * @return 操作响应
 */
pub fn stop_nginx() -> NginxActionResponse {
    if is_linux() {
        return stop_linux_nginx();
    }

    let config = match config::load_config() {
        Ok(c) => c.nginx,
        Err(e) => return error_response(format!("加载配置失败: {}", e)),
    };

    let exe_path = match &config.exe_path {
        Some(p) => p.clone(),
        None => return error_response_with_status("Nginx可执行文件路径未设置", "stopped", None),
    };

    if find_nginx_process(&exe_path).is_none() {
        update_nginx_status("stopped", None);
        return success_response_with_status("Nginx未在运行", "stopped", None);
    }

    let mut quit_cmd = Command::new(&exe_path);
    quit_cmd.arg("-s").arg("quit");

    if let Some(work_dir) = get_nginx_work_dir(&exe_path) {
        quit_cmd.current_dir(work_dir);
    }

    match quit_cmd.output() {
        Ok(_) => {
            for _ in 0..10 {
                std::thread::sleep(std::time::Duration::from_millis(500));
                if find_nginx_process(&exe_path).is_none() {
                    update_nginx_status("stopped", None);
                    return success_response_with_status("Nginx已停止", "stopped", None);
                }
            }
            NginxActionResponse {
                success: false,
                message: "Nginx停止命令已发送，但进程仍在运行".to_string(),
                status: Some("running".to_string()),
                pid: find_nginx_process(&exe_path),
            }
        }
        Err(e) => {
            log::error!("执行Nginx停止命令失败: {}", e);
            error_response_with_status(
                format!("停止Nginx失败: {}", e),
                "running",
                find_nginx_process(&exe_path),
            )
        }
    }
}

/**
 * 停止Linux系统上的Nginx
 *
 * @return 操作响应
 */
fn stop_linux_nginx() -> NginxActionResponse {
    if find_nginx_process("").is_none() {
        return success_response_with_status("Nginx未在运行", "stopped", None);
    }

    // 首先尝试使用 quit 命令优雅停止
    match Command::new("nginx").arg("-s").arg("quit").output() {
        Ok(_) => {
            for _ in 0..10 {
                std::thread::sleep(std::time::Duration::from_millis(500));
                if find_nginx_process("").is_none() {
                    return success_response_with_status("Nginx已停止", "stopped", None);
                }
            }

            // 如果 quit 命令未能停止，尝试使用 stop 命令强制停止
            log::info!("Nginx -s quit 未能停止进程，尝试使用 -s stop");
            if let Err(e) = Command::new("nginx").arg("-s").arg("stop").output() {
                log::error!("执行Nginx stop命令失败: {}", e);
            } else {
                // 等待进程停止
                for _ in 0..5 {
                    std::thread::sleep(std::time::Duration::from_millis(500));
                    if find_nginx_process("").is_none() {
                        return success_response_with_status("Nginx已停止", "stopped", None);
                    }
                }
            }

            NginxActionResponse {
                success: false,
                message: "Nginx停止命令已发送，但进程仍在运行".to_string(),
                status: Some("running".to_string()),
                pid: find_nginx_process(""),
            }
        }
        Err(e) => {
            log::error!("执行Nginx停止命令失败: {}", e);
            error_response_with_status(
                format!("停止Nginx失败: {}", e),
                "running",
                find_nginx_process(""),
            )
        }
    }
}

/**
 * 重启Nginx
 *
 * @return 操作响应
 */
pub fn restart_nginx() -> NginxActionResponse {
    let _ = stop_nginx();
    std::thread::sleep(std::time::Duration::from_secs(1));
    let start_result = start_nginx();

    NginxActionResponse {
        success: start_result.success,
        message: format!(
            "Nginx重启{}: {}",
            if start_result.success {
                "成功"
            } else {
                "失败"
            },
            start_result.message
        ),
        status: start_result.status,
        pid: start_result.pid,
    }
}

/**
 * 更新Nginx下载URL
 *
 * @param url 新的下载URL
 * @return 操作响应
 */
pub fn update_nginx_download_url(url: String) -> NginxActionResponse {
    let mut client_config = match config::load_config() {
        Ok(c) => c,
        Err(e) => return error_response(format!("加载配置失败: {}", e)),
    };

    client_config.nginx.download_url = url;

    match config::save_config(&client_config) {
        Ok(_) => NginxActionResponse {
            success: true,
            message: "下载URL已更新".to_string(),
            status: None,
            pid: None,
        },
        Err(e) => error_response(format!("保存配置失败: {}", e)),
    }
}

/**
 * 获取Nginx下载URL
 *
 * @return 下载URL
 */
pub fn get_nginx_download_url() -> String {
    match config::load_config() {
        Ok(client_config) => client_config.nginx.download_url,
        Err(_) => NginxConfig::default().download_url,
    }
}

/**
 * 下载并解压Nginx
 *
 * @param url 下载URL
 * @param target_dir 目标目录（可选，默认为用户配置目录）
 * @return 操作响应，包含解压后的Nginx路径
 */
pub async fn download_and_extract_nginx(
    url: String,
    target_dir: Option<String>,
) -> NginxActionResponse {
    use reqwest;
    use std::io::Write;

    // 确定目标目录
    let target_path = match target_dir {
        Some(dir) => PathBuf::from(dir),
        None => {
            // 默认使用用户配置目录下的nginx目录
            match dirs::config_dir() {
                Some(dir) => dir.join("langit-client").join("nginx"),
                None => {
                    return NginxActionResponse {
                        success: false,
                        message: "无法获取配置目录".to_string(),
                        status: None,
                        pid: None,
                    }
                }
            }
        }
    };

    // 创建临时目录用于下载
    let temp_dir = std::env::temp_dir().join("langit-nginx-download");
    if let Err(e) = fs::create_dir_all(&temp_dir) {
        return NginxActionResponse {
            success: false,
            message: format!("创建临时目录失败: {}", e),
            status: None,
            pid: None,
        };
    }

    // 从URL中提取文件名
    let file_name = url
        .split('/')
        .next_back()
        .unwrap_or("nginx.zip")
        .to_string();
    let zip_path = temp_dir.join(&file_name);

    // 下载文件
    log::info!("开始下载Nginx: {}", url);

    let client = match reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(300))
        .build()
    {
        Ok(c) => c,
        Err(e) => {
            return NginxActionResponse {
                success: false,
                message: format!("创建HTTP客户端失败: {}", e),
                status: None,
                pid: None,
            }
        }
    };

    let response = match client.get(&url).send().await {
        Ok(r) => r,
        Err(e) => {
            return NginxActionResponse {
                success: false,
                message: format!("下载Nginx失败: {}", e),
                status: None,
                pid: None,
            }
        }
    };

    if !response.status().is_success() {
        return NginxActionResponse {
            success: false,
            message: format!("下载失败，HTTP状态码: {}", response.status()),
            status: None,
            pid: None,
        };
    }

    // 读取响应内容
    let bytes = match response.bytes().await {
        Ok(b) => b,
        Err(e) => {
            return NginxActionResponse {
                success: false,
                message: format!("读取下载内容失败: {}", e),
                status: None,
                pid: None,
            }
        }
    };

    // 保存到临时文件
    let mut file = match fs::File::create(&zip_path) {
        Ok(f) => f,
        Err(e) => {
            return NginxActionResponse {
                success: false,
                message: format!("创建临时文件失败: {}", e),
                status: None,
                pid: None,
            }
        }
    };

    if let Err(e) = file.write_all(&bytes) {
        return NginxActionResponse {
            success: false,
            message: format!("写入临时文件失败: {}", e),
            status: None,
            pid: None,
        };
    }

    log::info!("Nginx下载完成: {:?}", zip_path);

    // 解压文件
    log::info!("开始解压Nginx到: {:?}", target_path);

    if let Err(e) = fs::create_dir_all(&target_path) {
        return NginxActionResponse {
            success: false,
            message: format!("创建目标目录失败: {}", e),
            status: None,
            pid: None,
        };
    }

    // 使用zip crate解压
    match extract_zip(&zip_path, &target_path) {
        Ok(nginx_exe_path) => {
            // 清理临时文件
            let _ = fs::remove_file(&zip_path);

            // 验证解压后的Nginx
            match validate_nginx(&nginx_exe_path) {
                Ok(version) => {
                    // 自动载入Nginx
                    let load_result = load_nginx(nginx_exe_path.clone());

                    if load_result.success {
                        NginxActionResponse {
                            success: true,
                            message: format!("Nginx下载并载入成功: {}", version),
                            status: load_result.status,
                            pid: load_result.pid,
                        }
                    } else {
                        NginxActionResponse {
                            success: true,
                            message: format!(
                                "Nginx下载成功，但载入失败: {}。路径: {}",
                                load_result.message, nginx_exe_path
                            ),
                            status: Some("stopped".to_string()),
                            pid: None,
                        }
                    }
                }
                Err(e) => NginxActionResponse {
                    success: false,
                    message: format!("解压完成但验证失败: {}", e),
                    status: None,
                    pid: None,
                },
            }
        }
        Err(e) => NginxActionResponse {
            success: false,
            message: format!("解压失败: {}", e),
            status: None,
            pid: None,
        },
    }
}

/**
 * 解压ZIP文件
 *
 * @param zip_path ZIP文件路径
 * @param target_dir 目标目录
 * @return Nginx可执行文件路径
 */
fn extract_zip(zip_path: &Path, target_dir: &Path) -> Result<String, String> {
    use zip::ZipArchive;

    let file = fs::File::open(zip_path).map_err(|e| format!("打开ZIP文件失败: {}", e))?;

    let mut archive = ZipArchive::new(file).map_err(|e| format!("读取ZIP文件失败: {}", e))?;

    // 解压所有文件
    for i in 0..archive.len() {
        let mut file = archive
            .by_index(i)
            .map_err(|e| format!("读取ZIP条目失败: {}", e))?;

        let outpath = target_dir.join(file.name());

        if file.name().ends_with('/') {
            fs::create_dir_all(&outpath).map_err(|e| format!("创建目录失败: {}", e))?;
        } else {
            if let Some(parent) = outpath.parent() {
                if !parent.exists() {
                    fs::create_dir_all(parent).map_err(|e| format!("创建父目录失败: {}", e))?;
                }
            }

            let mut outfile =
                fs::File::create(&outpath).map_err(|e| format!("创建文件失败: {}", e))?;
            std::io::copy(&mut file, &mut outfile).map_err(|e| format!("写入文件失败: {}", e))?;
        }
    }

    // 查找Nginx可执行文件
    find_nginx_exe_in_dir(target_dir)
}

/**
 * 在目录中查找Nginx可执行文件
 *
 * @param dir 搜索目录
 * @return Nginx可执行文件路径
 */
fn find_nginx_exe_in_dir(dir: &Path) -> Result<String, String> {
    let exe_name = if cfg!(windows) { "nginx.exe" } else { "nginx" };

    // 递归搜索nginx可执行文件
    fn search_dir(dir: &Path, exe_name: &str) -> Option<PathBuf> {
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    if let Some(found) = search_dir(&path, exe_name) {
                        return Some(found);
                    }
                } else if path.file_name().map(|n| n == exe_name).unwrap_or(false) {
                    return Some(path);
                }
            }
        }
        None
    }

    match search_dir(dir, exe_name) {
        Some(path) => Ok(path.to_string_lossy().to_string()),
        None => Err(format!("在解压后的目录中未找到 {}", exe_name)),
    }
}

/**
 * 生成Nginx配置文件内容
 *
 * @param config 代理配置
 * @return nginx.conf内容
 */
pub fn generate_nginx_config(config: &crate::models::NginxProxyConfig) -> String {
    let mut nginx_conf = String::new();

    // 基本配置
    nginx_conf.push_str("worker_processes 1;\n\n");
    nginx_conf.push_str("# PID文件路径\n");
    nginx_conf.push_str("pid logs/nginx.pid;\n\n");
    nginx_conf.push_str("events {\n");
    nginx_conf.push_str("    worker_connections 1024;\n");
    nginx_conf.push_str("}\n\n");
    nginx_conf.push_str("http {\n");
    nginx_conf.push_str("    include       mime.types;\n");
    nginx_conf.push_str("    default_type  application/octet-stream;\n\n");
    nginx_conf.push_str("    sendfile        on;\n");
    nginx_conf.push_str("    keepalive_timeout  65;\n\n");

    // 服务器配置
    nginx_conf.push_str("    server {\n");
    nginx_conf.push_str(&format!("        listen {};\n", config.listen_port));
    nginx_conf.push_str(&format!("        server_name {};\n\n", config.server_name));

    // 添加安全头
    if config.add_security_headers {
        nginx_conf.push_str("        # 安全头\n");
        nginx_conf.push_str("        add_header X-Frame-Options \"SAMEORIGIN\" always;\n");
        nginx_conf.push_str("        add_header X-Content-Type-Options \"nosniff\" always;\n");
        nginx_conf.push_str("        add_header X-XSS-Protection \"1; mode=block\" always;\n");
        nginx_conf.push_str(
            "        add_header Referrer-Policy \"strict-origin-when-cross-origin\" always;\n",
        );

        // HSTS
        if config.enable_hsts {
            nginx_conf.push_str(&format!(
                "        add_header Strict-Transport-Security \"max-age={}; includeSubDomains\" always;\n",
                config.hsts_max_age
            ));
        }
        nginx_conf.push('\n');
    }

    // 添加CORS头
    if config.add_cors_headers {
        nginx_conf.push_str("        # CORS配置\n");
        nginx_conf.push_str(&format!(
            "        add_header 'Access-Control-Allow-Origin' '{}' always;\n",
            config.cors_origins
        ));
        nginx_conf
            .push_str("        add_header 'Access-Control-Allow-Credentials' 'true' always;\n");
        nginx_conf.push_str(&format!(
            "        add_header 'Access-Control-Allow-Methods' '{}' always;\n",
            config.cors_methods
        ));
        nginx_conf.push_str(&format!(
            "        add_header 'Access-Control-Allow-Headers' '{}' always;\n",
            config.cors_headers
        ));

        // CORS预检请求处理
        nginx_conf.push('\n');
        nginx_conf.push_str("        location / {\n");
        nginx_conf.push_str("            if ($request_method = 'OPTIONS') {\n");
        nginx_conf.push_str(&format!(
            "                add_header 'Access-Control-Allow-Origin' '{}';\n",
            config.cors_origins
        ));
        nginx_conf
            .push_str("                add_header 'Access-Control-Allow-Credentials' 'true';\n");
        nginx_conf.push_str(&format!(
            "                add_header 'Access-Control-Allow-Methods' '{}';\n",
            config.cors_methods
        ));
        nginx_conf.push_str(&format!(
            "                add_header 'Access-Control-Allow-Headers' '{}';\n",
            config.cors_headers
        ));
        nginx_conf.push_str("                add_header 'Access-Control-Max-Age' 1728000;\n");
        nginx_conf
            .push_str("                add_header 'Content-Type' 'text/plain; charset=utf-8';\n");
        nginx_conf.push_str("                add_header 'Content-Length' 0;\n");
        nginx_conf.push_str("                return 204;\n");
        nginx_conf.push_str("            }\n\n");
        nginx_conf.push_str(&format!("            proxy_pass {};\n", config.backend_url));
        nginx_conf.push_str("            proxy_set_header Host $host;\n");
        nginx_conf.push_str("            proxy_set_header X-Real-IP $remote_addr;\n");
        nginx_conf
            .push_str("            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n");
        nginx_conf.push_str("            proxy_set_header X-Forwarded-Proto $scheme;\n");
        nginx_conf.push_str("        }\n");
    } else {
        // 无CORS配置
        nginx_conf.push_str("        location / {\n");
        nginx_conf.push_str(&format!("            proxy_pass {};\n", config.backend_url));
        nginx_conf.push_str("            proxy_set_header Host $host;\n");
        nginx_conf.push_str("            proxy_set_header X-Real-IP $remote_addr;\n");
        nginx_conf
            .push_str("            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n");
        nginx_conf.push_str("            proxy_set_header X-Forwarded-Proto $scheme;\n");
        nginx_conf.push_str("        }\n");
    }

    nginx_conf.push_str("    }\n");
    nginx_conf.push_str("}\n");

    nginx_conf
}

/**
 * 保存Nginx代理配置
 *
 * @param proxy_config 代理配置
 * @return 保存响应
 */
/**
 * 获取Nginx配置文件保存路径
 *
 * @return 配置文件路径
 */
fn get_nginx_config_path() -> Option<PathBuf> {
    if is_linux() {
        // Linux平台：在用户目录下创建配置文件
        // 避免使用 /etc/nginx 因为需要 root 权限
        dirs::config_dir().map(|dir| dir.join("langit-client").join("nginx").join("nginx.conf"))
    } else {
        // Windows平台：使用配置目录
        match config::load_config() {
            Ok(client_config) => client_config
                .nginx
                .config_dir
                .map(|dir| Path::new(&dir).join("nginx.conf")),
            Err(_) => None,
        }
    }
}

/**
 * 获取Nginx配置目录
 *
 * @return 配置目录路径
 */
pub fn get_nginx_config_dir() -> Option<String> {
    get_nginx_config_path().and_then(|p| {
        p.parent()
            .map(|parent| parent.to_string_lossy().to_string())
    })
}

pub fn save_nginx_proxy_config(
    proxy_config: crate::models::NginxProxyConfig,
) -> crate::models::NginxConfigSaveResponse {
    // 加载当前配置
    let mut client_config = match config::load_config() {
        Ok(config) => config,
        Err(e) => {
            return crate::models::NginxConfigSaveResponse {
                success: false,
                message: format!("加载配置失败: {}", e),
                need_restart: false,
            }
        }
    };

    // 检查Nginx是否正在运行
    let was_running = if is_linux() {
        find_nginx_process("").is_some()
    } else {
        client_config.nginx.status == "running"
    };

    // 更新代理配置
    client_config.nginx.proxy = proxy_config;

    // 保存配置
    match config::save_config(&client_config) {
        Ok(_) => {
            // 生成nginx.conf文件
            let nginx_conf = generate_nginx_config(&client_config.nginx.proxy);

            // 获取配置文件路径
            let conf_path = if is_linux() {
                get_nginx_config_path()
            } else {
                client_config
                    .nginx
                    .config_dir
                    .as_ref()
                    .map(|dir| Path::new(dir).join("nginx.conf"))
            };

            if let Some(conf_path) = conf_path {
                // 确保conf目录存在
                if let Some(parent) = conf_path.parent() {
                    if let Err(e) = fs::create_dir_all(parent) {
                        return crate::models::NginxConfigSaveResponse {
                            success: false,
                            message: format!("创建配置目录失败: {}", e),
                            need_restart: was_running,
                        };
                    }
                }

                // 写入配置文件
                match fs::write(&conf_path, nginx_conf) {
                    Ok(_) => {
                        log::info!("Nginx配置文件已保存到: {:?}", conf_path);
                        crate::models::NginxConfigSaveResponse {
                            success: true,
                            message: "配置已保存".to_string(),
                            need_restart: was_running,
                        }
                    }
                    Err(e) => crate::models::NginxConfigSaveResponse {
                        success: false,
                        message: format!("保存配置文件失败: {}", e),
                        need_restart: was_running,
                    },
                }
            } else {
                crate::models::NginxConfigSaveResponse {
                    success: true,
                    message: "配置已保存（配置文件将在Nginx载入后生成）".to_string(),
                    need_restart: was_running,
                }
            }
        }
        Err(e) => crate::models::NginxConfigSaveResponse {
            success: false,
            message: format!("保存配置失败: {}", e),
            need_restart: false,
        },
    }
}

/**
 * 获取Nginx代理配置
 *
 * @return 代理配置
 */
pub fn get_nginx_proxy_config() -> crate::models::NginxProxyConfig {
    match config::load_config() {
        Ok(client_config) => client_config.nginx.proxy,
        Err(_) => crate::models::NginxProxyConfig::default(),
    }
}
