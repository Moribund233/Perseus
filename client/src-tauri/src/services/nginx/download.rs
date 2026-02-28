/**
 * 下载和解压模块
 *
 * 管理Nginx的下载、解压和安装
 */
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

use crate::core::config;
use crate::models::{NginxActionResponse, NginxConfig};

use super::response::error_response;

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

    let target_path = match target_dir {
        Some(dir) => PathBuf::from(dir),
        None => match dirs::config_dir() {
            Some(dir) => dir.join("langit-client").join("nginx"),
            None => {
                return NginxActionResponse {
                    success: false,
                    message: "无法获取配置目录".to_string(),
                    status: None,
                    pid: None,
                }
            }
        },
    };

    let temp_dir = std::env::temp_dir().join("langit-nginx-download");
    if let Err(e) = fs::create_dir_all(&temp_dir) {
        return NginxActionResponse {
            success: false,
            message: format!("创建临时目录失败: {}", e),
            status: None,
            pid: None,
        };
    }

    let file_name = url
        .split('/')
        .next_back()
        .unwrap_or("nginx.zip")
        .to_string();
    let zip_path = temp_dir.join(&file_name);

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
    log::info!("开始解压Nginx到: {:?}", target_path);

    if let Err(e) = fs::create_dir_all(&target_path) {
        return NginxActionResponse {
            success: false,
            message: format!("创建目标目录失败: {}", e),
            status: None,
            pid: None,
        };
    }

    match extract_zip(&zip_path, &target_path) {
        Ok(nginx_exe_path) => {
            let _ = fs::remove_file(&zip_path);

            match super::loader::validate_nginx(&nginx_exe_path) {
                Ok(version) => {
                    let load_result = super::loader::load_nginx(nginx_exe_path.clone());

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
