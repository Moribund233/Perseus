/**
 * 进程管理模块
 *
 * 管理Nginx进程的查找、监控和状态获取
 */
use std::fs;
use std::path::Path;

use sysinfo::{ProcessRefreshKind, RefreshKind, System};

use super::config_paths::get_nginx_config_dir;
use super::platform::is_linux;

/// 从进程列表中查找主进程
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
 * 从PID文件读取Nginx进程ID
 *
 * @return 进程ID
 */
fn read_pid_from_file() -> Option<u32> {
    let config_dir = get_nginx_config_dir()?;
    let pid_file = Path::new(&config_dir).join("logs").join("nginx.pid");

    if !pid_file.exists() {
        return None;
    }

    match fs::read_to_string(&pid_file) {
        Ok(content) => content.trim().parse::<u32>().ok(),
        Err(e) => {
            log::warn!("读取PID文件失败: {}", e);
            None
        }
    }
}

/**
 * 查找Nginx进程
 *
 * @param exe_path Nginx可执行文件路径（Windows）或空字符串（Linux使用系统命令）
 * @return 进程ID
 */
pub fn find_nginx_process(exe_path: &str) -> Option<u32> {
    // Linux平台：首先尝试从PID文件读取
    if is_linux() {
        if let Some(pid) = read_pid_from_file() {
            let s = System::new_with_specifics(
                RefreshKind::new().with_processes(ProcessRefreshKind::everything()),
            );

            if let Some(process) = s.process((pid as usize).into()) {
                let process_name = process.name().to_lowercase();
                if process_name == "nginx" {
                    return Some(pid);
                }
            }
        }
    }

    let s = System::new_with_specifics(
        RefreshKind::new().with_processes(ProcessRefreshKind::everything()),
    );

    let mut matched_processes: Vec<(u32, Option<u32>)> = Vec::new();

    if is_linux() {
        find_linux_nginx_processes(&s, &mut matched_processes);
    } else {
        find_windows_nginx_processes(&s, exe_path, &mut matched_processes);
    }

    find_master_process(&matched_processes)
}

/// 查找Linux上的Nginx进程
fn find_linux_nginx_processes(s: &System, matched_processes: &mut Vec<(u32, Option<u32>)>) {
    use super::config_paths::get_nginx_config_path;

    let config_path = get_nginx_config_path();
    let config_path_str = config_path
        .as_ref()
        .map(|p| p.to_string_lossy().to_string());

    for (pid, process) in s.processes() {
        let process_name = process.name().to_lowercase();
        if process_name == "nginx" {
            let cmd = process.cmd();
            let is_our_nginx = if let Some(ref our_config) = config_path_str {
                cmd.iter().any(|arg| arg.contains(our_config))
            } else {
                let exe = process
                    .exe()
                    .map(|e| e.to_string_lossy().to_lowercase())
                    .unwrap_or_default();
                !exe.contains("openresty")
            };

            if is_our_nginx {
                matched_processes.push((pid.as_u32(), process.parent().map(|p| p.as_u32())));
            }
        }
    }
}

/// 查找Windows上的Nginx进程
fn find_windows_nginx_processes(
    s: &System,
    exe_path: &str,
    matched_processes: &mut Vec<(u32, Option<u32>)>,
) {
    use std::path::Path;

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
