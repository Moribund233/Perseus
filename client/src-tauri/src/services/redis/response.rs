/**
 * Redis响应工具模块
 *
 * 提供统一的响应构建函数
 */
use crate::models::RedisActionResponse;

/**
 * 创建成功响应
 *
 * @param message 消息
 * @return 操作响应
 */
pub fn success_response(message: String) -> RedisActionResponse {
    RedisActionResponse {
        success: true,
        message,
        status: None,
    }
}

/**
 * 创建错误响应
 *
 * @param message 错误消息
 * @return 操作响应
 */
pub fn error_response(message: String) -> RedisActionResponse {
    RedisActionResponse {
        success: false,
        message,
        status: None,
    }
}
