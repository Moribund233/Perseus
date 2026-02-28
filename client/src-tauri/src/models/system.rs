/**
 * 系统信息相关模型
 *
 * 定义系统信息、网络信息等数据结构
 */
use serde::{Deserialize, Serialize};

/// 系统信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemInfo {
    pub platform: String,
    pub platform_version: String,
    pub architecture: String,
    pub processor: String,
    pub hostname: String,
    pub cpu_count: i32,
    pub cpu_freq_mhz: Option<f64>,
    pub cpu_percent: f64,
    pub memory_total_gb: f64,
    pub memory_used_gb: f64,
    pub memory_percent: f64,
    pub disk_total_gb: f64,
    pub disk_used_gb: f64,
    pub disk_percent: f64,
    pub network: NetworkInfo,
}

/// 网络信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkInfo {
    pub bytes_sent: u64,
    pub bytes_received: u64,
    pub packets_sent: u64,
    pub packets_received: u64,
    pub errors_in: u64,
    pub errors_out: u64,
}
