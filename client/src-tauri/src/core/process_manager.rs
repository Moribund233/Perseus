use once_cell::sync::Lazy;

/**
 * 进程管理模块
 *
 * 管理服务端进程的生命周期（启动、停止、监控）
 */
use std::process::{Command, Stdio};
use std::sync::Mutex;
use sysinfo::System;

use super::config;

/// 全局进程 ID 存储
static SERVER_PID: Lazy<Mutex<Option<u32>>> = Lazy::new(|| Mutex::new(None));

/// 全局 System 实例，用于持续监控
pub static SYSTEM: Lazy<Mutex<System>> = Lazy::new(|| Mutex::new(System::new_all()));

/// 获取服务端路径配置
fn get_server_path_config() -> crate::models::ServerPathConfig {
    config::load_config()
        .map(|c| c.server.path)
        .unwrap_or_default()
}

/// 获取服务端可执行文件路径
///
/// 查找顺序：
/// 1. 自定义路径（用户手动选择）
/// 2. server/<dir_name>/<exe_name>（默认位置）
pub fn get_server_exe_path() -> Result<std::path::PathBuf, String> {
    let path_config = get_server_path_config();

    // 1. 如果配置了自定义路径，优先使用
    if let Some(custom) = &path_config.custom_path {
        let custom_path = std::path::PathBuf::from(custom);
        if custom_path.exists() {
            return Ok(custom_path);
        }
        return Err(format!("配置的服务端路径不存在: {}", custom));
    }

    let exe_name = &path_config.exe_name;
    let dir_name = &path_config.dir_name;

    // 获取当前可执行文件所在目录
    let current_exe =
        std::env::current_exe().map_err(|e| format!("获取当前可执行文件路径失败: {}", e))?;

    let current_dir = current_exe.parent().ok_or("无法获取当前目录")?;

    // 2. 检查 server/<dir_name>/<exe_name>（默认位置）
    let server_path = current_dir.join("server").join(dir_name).join(exe_name);
    if server_path.exists() {
        return Ok(server_path);
    }

    Err(format!(
        "未配置服务端路径。请在设置中选择服务端可执行文件，或将服务端放置在 {} 目录下",
        server_path.display()
    ))
}

/// 查找服务端进程
pub fn find_server_process() -> Option<u32> {
    let mut system = System::new_all();
    // 刷新进程列表以确保获取最新数据
    system.refresh_processes();

    for (pid, process) in system.processes() {
        let name = process.name().to_lowercase();

        // 检查是否是 langit-server 进程（支持带 .exe 后缀的情况）
        if name.contains("langit-server") || name.contains("langit_server") {
            log::debug!("找到服务端进程: PID={}, Name={}", pid.as_u32(), name);
            return Some(pid.as_u32());
        }
    }

    log::debug!("未找到服务端进程");
    None
}

/// 检查服务是否正在运行
pub fn is_server_running() -> bool {
    // 先检查已记录的 PID
    if let Some(pid) = *SERVER_PID.lock().unwrap() {
        let mut system = System::new_all();
        system.refresh_processes();
        if system.process(sysinfo::Pid::from(pid as usize)).is_some() {
            log::debug!("服务正在运行 (PID: {})", pid);
            return true;
        }
        // PID 记录的进程已不存在，清空记录
        *SERVER_PID.lock().unwrap() = None;
    }

    // 尝试查找进程
    if let Some(pid) = find_server_process() {
        *SERVER_PID.lock().unwrap() = Some(pid);
        log::debug!("找到运行中的服务 (PID: {})", pid);
        return true;
    }

    log::debug!("服务未运行");
    false
}

/// 启动服务端进程
pub fn start_server() -> Result<u32, String> {
    // 检查是否已经在运行
    if is_server_running() {
        return Err("服务已经在运行中".to_string());
    }

    // 确保本地认证已初始化
    if !super::local_auth::is_initialized()? {
        super::local_auth::init_local_auth()?;
    }

    // 获取服务端可执行文件路径
    let server_exe = get_server_exe_path()?;

    // 获取服务端工作目录（可执行文件所在目录）
    let server_dir = server_exe
        .parent()
        .ok_or("无法获取服务端目录")?
        .to_path_buf();

    // 获取环境变量配置
    let env_vars = super::local_auth::get_server_env_vars()?;

    // 构建启动命令
    let mut cmd = Command::new(&server_exe);
    cmd.current_dir(&server_dir)
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    // Windows: 隐藏控制台窗口，后台运行
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    // 注入环境变量
    for (key, value) in env_vars {
        cmd.env(key, value);
    }

    // 启动进程
    let mut child = cmd.spawn().map_err(|e| format!("启动服务失败: {}", e))?;

    let pid = child.id();

    // 保存 PID
    *SERVER_PID.lock().unwrap() = Some(pid);

    // 在后台线程中等待子进程，防止产生僵尸进程
    std::thread::spawn(move || {
        let _ = child.wait();
        // 进程退出后清空 PID 记录
        if let Ok(mut server_pid) = SERVER_PID.lock() {
            if server_pid.map(|p| p == pid).unwrap_or(false) {
                *server_pid = None;
            }
        }
    });

    Ok(pid)
}

/// 停止服务端进程
pub fn stop_server() -> Result<(), String> {
    let pid = SERVER_PID.lock().unwrap().take();

    if let Some(pid) = pid {
        let system = System::new_all();

        if let Some(process) = system.process(sysinfo::Pid::from(pid as usize)) {
            // 尝试优雅终止
            if !process.kill_with(sysinfo::Signal::Term).unwrap_or(false) {
                // 如果优雅终止失败，强制终止
                process.kill();
            }
        }
    }

    // 也尝试查找并停止其他服务端进程
    if let Some(pid) = find_server_process() {
        let system = System::new_all();
        if let Some(process) = system.process(sysinfo::Pid::from(pid as usize)) {
            process.kill();
        }
    }

    Ok(())
}

/// 获取服务端进程信息
pub fn get_server_info() -> Option<ProcessInfo> {
    let pid = if let Some(pid) = *SERVER_PID.lock().unwrap() {
        pid
    } else if let Some(pid) = find_server_process() {
        *SERVER_PID.lock().unwrap() = Some(pid);
        pid
    } else {
        return None;
    };

    let mut system = SYSTEM.lock().unwrap();

    // 刷新进程和CPU信息
    system.refresh_process(sysinfo::Pid::from(pid as usize));
    system.refresh_cpu();

    system
        .process(sysinfo::Pid::from(pid as usize))
        .map(|process| ProcessInfo {
            pid: pid as i32,
            name: process.name().to_string(),
            cpu_usage: process.cpu_usage(),
            memory_mb: (process.memory() as f64) / 1024.0 / 1024.0,
            status: format!("{:?}", process.status()),
        })
}

/// 进程信息
#[derive(Debug, Clone, serde::Serialize)]
pub struct ProcessInfo {
    pub pid: i32,
    pub name: String,
    pub cpu_usage: f32,
    pub memory_mb: f64,
    pub status: String,
}

/// 获取系统资源使用情况
pub fn get_system_resources() -> SystemResources {
    let mut system = SYSTEM.lock().unwrap();

    // 刷新CPU和内存信息
    system.refresh_cpu();
    system.refresh_memory();

    let total_memory = system.total_memory();
    let used_memory = system.used_memory();

    // 计算平均CPU使用率
    let cpu_usage = if system.cpus().is_empty() {
        0.0
    } else {
        system.cpus().iter().map(|cpu| cpu.cpu_usage()).sum::<f32>() / system.cpus().len() as f32
    };

    SystemResources {
        cpu_usage,
        memory_total_mb: (total_memory as f64) / 1024.0 / 1024.0,
        memory_used_mb: (used_memory as f64) / 1024.0 / 1024.0,
        memory_usage_percent: if total_memory > 0 {
            (used_memory as f64 / total_memory as f64) * 100.0
        } else {
            0.0
        },
    }
}

/// 系统资源信息
#[derive(Debug, Clone, serde::Serialize)]
pub struct SystemResources {
    pub cpu_usage: f32,
    pub memory_total_mb: f64,
    pub memory_used_mb: f64,
    pub memory_usage_percent: f64,
}
