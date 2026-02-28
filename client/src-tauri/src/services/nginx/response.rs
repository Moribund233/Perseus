/**
 * 响应构建工具模块
 *
 * 提供统一的响应构建函数
 */
use crate::models::NginxActionResponse;

/// 构建成功响应
pub fn success_response_with_status(
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
pub fn error_response(message: impl Into<String>) -> NginxActionResponse {
    NginxActionResponse {
        success: false,
        message: message.into(),
        status: None,
        pid: None,
    }
}

/// 构建带状态的错误响应
pub fn error_response_with_status(
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
