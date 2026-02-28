/**
 * 系统和性能命令模块
 *
 * 提供系统信息查询和性能监控功能
 */
use crate::core::process_manager;
use crate::models::{PerformanceData, SystemInfo};
use sysinfo::{Networks, System};

/**
 * 获取性能数据
 *
 * @return 性能数据
 */
#[tauri::command]
pub fn get_performance_data() -> Result<PerformanceData, String> {
    let resources = process_manager::get_system_resources();

    // 获取服务端进程信息
    let server_info = process_manager::get_server_info();

    let memory = if let Some(info) = server_info {
        info.memory_mb
    } else {
        resources.memory_used_mb
    };

    // 这里简化处理，实际应该维护一个请求计数器
    Ok(PerformanceData {
        cpu: resources.cpu_usage as f64,
        memory,
        uptime: 0, // 从服务状态获取
        requests: 0,
    })
}

/**
 * 获取系统资源使用情况
 *
 * @return 系统资源
 */
#[tauri::command]
pub fn get_system_resources() -> Result<process_manager::SystemResources, String> {
    Ok(process_manager::get_system_resources())
}

/**
 * 获取服务端进程信息
 *
 * @return 进程信息（可选）
 */
#[tauri::command]
pub fn get_server_process_info() -> Result<Option<process_manager::ProcessInfo>, String> {
    Ok(process_manager::get_server_info())
}

/**
 * 获取本地系统信息
 *
 * @return 系统信息
 */
#[tauri::command]
pub fn get_local_system_info() -> Result<SystemInfo, String> {
    // 使用全局 SYSTEM 实例，避免每次都重新初始化
    let mut system = process_manager::SYSTEM.lock().unwrap();

    // 刷新CPU和内存信息
    system.refresh_cpu();
    system.refresh_memory();

    // 获取CPU信息
    let cpu_count = system.cpus().len() as i32;
    let cpu_freq_mhz = system.cpus().first().map(|c| c.frequency() as f64);
    // 计算平均CPU使用率
    let cpu_percent = system
        .cpus()
        .iter()
        .map(|c| c.cpu_usage() as f64)
        .sum::<f64>()
        / cpu_count as f64;

    // 获取内存信息（sysinfo 0.30 返回的是字节，转换为GB需要除以 1024 * 1024 * 1024）
    let memory_total_gb = system.total_memory() as f64 / (1024.0 * 1024.0 * 1024.0);
    let memory_used_gb = system.used_memory() as f64 / (1024.0 * 1024.0 * 1024.0);
    let memory_percent = if memory_total_gb > 0.0 {
        (memory_used_gb / memory_total_gb) * 100.0
    } else {
        0.0
    };

    // 获取平台信息
    let platform = std::env::consts::OS.to_string();
    let architecture = std::env::consts::ARCH.to_string();

    // 获取主机名和处理器信息
    // host_name() 和 kernel_version() 是关联函数，不是方法
    let hostname = System::host_name().unwrap_or_else(|| "Unknown".to_string());
    let processor = system
        .cpus()
        .first()
        .map(|c| c.brand().to_string())
        .unwrap_or_else(|| "Unknown".to_string());

    // 获取平台版本（使用内核版本）
    let platform_version = System::kernel_version().unwrap_or_else(|| "Unknown".to_string());

    // 获取磁盘信息（简化处理）
    let disk_total_gb = 0.0;
    let disk_used_gb = 0.0;
    let disk_percent = 0.0;

    // 获取网络信息
    let network_info = get_network_info();

    Ok(SystemInfo {
        platform,
        platform_version,
        architecture,
        processor,
        hostname,
        cpu_count,
        cpu_freq_mhz,
        cpu_percent,
        memory_total_gb,
        memory_used_gb,
        memory_percent,
        disk_total_gb,
        disk_used_gb,
        disk_percent,
        network: network_info,
    })
}

/**
 * 获取网络信息
 *
 * @return 网络信息
 */
fn get_network_info() -> crate::models::NetworkInfo {
    let mut total_bytes_sent = 0u64;
    let mut total_bytes_received = 0u64;
    let mut total_packets_sent = 0u64;
    let mut total_packets_received = 0u64;
    let mut total_errors_in = 0u64;
    let mut total_errors_out = 0u64;

    // 创建 Networks 实例并刷新
    let networks = Networks::new_with_refreshed_list();

    // 遍历所有网络接口，累加统计数据
    for (_, data) in &networks {
        total_bytes_sent += data.total_transmitted();
        total_bytes_received += data.total_received();
        total_packets_sent += data.total_packets_transmitted();
        total_packets_received += data.total_packets_received();
        total_errors_in += data.errors_on_received();
        total_errors_out += data.errors_on_transmitted();
    }

    crate::models::NetworkInfo {
        bytes_sent: total_bytes_sent,
        bytes_received: total_bytes_received,
        packets_sent: total_packets_sent,
        packets_received: total_packets_received,
        errors_in: total_errors_in,
        errors_out: total_errors_out,
    }
}
