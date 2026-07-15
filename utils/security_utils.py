"""
安全工具模块

提供敏感数据过滤、安全事件记录等安全相关功能
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import uuid

# 敏感字段列表（默认）
DEFAULT_SENSITIVE_FIELDS = [
    'password', 'token', 'secret', 'authorization',
    'api_key', 'access_token', 'refresh_token', 'apikey',
    'private_key', 'secret_key', 'credentials'
]

# 创建安全日志记录器
security_logger = logging.getLogger("security")


def filter_sensitive_data(
    data: Dict[str, Any],
    sensitive_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    过滤敏感字段

    递归遍历字典，将敏感字段的值替换为 '***'

    Args:
        data: 原始数据字典
        sensitive_fields: 敏感字段列表，默认使用 DEFAULT_SENSITIVE_FIELDS

    Returns:
        dict: 过滤后的数据字典
    """
    if not isinstance(data, dict):
        return data

    if sensitive_fields is None:
        sensitive_fields = DEFAULT_SENSITIVE_FIELDS

    filtered = {}
    for key, value in data.items():
        # 检查键名是否包含敏感字段
        if any(field in key.lower() for field in sensitive_fields):
            filtered[key] = '***'
        elif isinstance(value, dict):
            # 递归处理嵌套字典
            filtered[key] = filter_sensitive_data(value, sensitive_fields)
        elif isinstance(value, list):
            # 递归处理列表中的字典
            filtered[key] = [
                filter_sensitive_data(item, sensitive_fields) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            filtered[key] = value

    return filtered


def mask_string(
    value: str,
    visible_start: int = 3,
    visible_end: int = 3,
    mask_char: str = '*'
) -> str:
    """
    遮罩字符串，只显示开头和结尾的部分字符

    Args:
        value: 原始字符串
        visible_start: 开头可见字符数
        visible_end: 结尾可见字符数
        mask_char: 遮罩字符

    Returns:
        str: 遮罩后的字符串
    """
    if not value:
        return value

    if len(value) <= visible_start + visible_end:
        return mask_char * len(value)

    return value[:visible_start] + mask_char * (len(value) - visible_start - visible_end) + value[-visible_end:]


def log_security_event(
    event_type: str,
    description: str,
    user_id: Optional[uuid.UUID] = None,
    client_ip: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    level: str = "warning"
) -> None:
    """
    记录安全事件

    用于记录安全相关事件，如：
    - 认证失败
    - 权限拒绝
    - 异常访问模式
    - 配置变更

    Args:
        event_type: 事件类型（如 AUTH_FAILURE, PERMISSION_DENIED）
        description: 事件描述
        user_id: 相关用户 ID
        client_ip: 客户端 IP
        details: 额外详情
        level: 日志级别（debug, info, warning, error, critical）
    """
    event = {
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        "description": description,
        "user_id": user_id,
        "client_ip": client_ip,
        "details": details or {}
    }

    log_message = f"[SECURITY] {event}"

    # 根据级别记录日志
    level = level.lower()
    if level == "debug":
        security_logger.debug(log_message)
    elif level == "info":
        security_logger.info(log_message)
    elif level == "warning":
        security_logger.warning(log_message)
    elif level == "error":
        security_logger.error(log_message)
    elif level == "critical":
        security_logger.critical(log_message)
    else:
        security_logger.warning(log_message)


def is_sensitive_field(field_name: str, sensitive_fields: Optional[List[str]] = None) -> bool:
    """
    检查字段名是否是敏感字段

    Args:
        field_name: 字段名
        sensitive_fields: 敏感字段列表，默认使用 DEFAULT_SENSITIVE_FIELDS

    Returns:
        bool: 是否是敏感字段
    """
    if sensitive_fields is None:
        sensitive_fields = DEFAULT_SENSITIVE_FIELDS

    field_lower = field_name.lower()
    return any(sensitive in field_lower for sensitive in sensitive_fields)


def sanitize_headers(
    headers: Dict[str, str],
    sensitive_headers: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    清理 HTTP 头中的敏感信息

    Args:
        headers: HTTP 头字典
        sensitive_headers: 敏感头列表，默认包含 authorization, cookie 等

    Returns:
        dict: 清理后的头字典
    """
    if sensitive_headers is None:
        sensitive_headers = ['authorization', 'cookie', 'x-api-key', 'x-auth-token']

    sanitized = {}
    for key, value in headers.items():
        if any(sh.lower() in key.lower() for sh in sensitive_headers):
            sanitized[key] = '***'
        else:
            sanitized[key] = value

    return sanitized


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    验证密码强度

    Args:
        password: 密码

    Returns:
        dict: 包含验证结果和强度评分
    """
    result = {
        "is_valid": False,
        "score": 0,
        "errors": []
    }

    if not password:
        result["errors"].append("Password is required")
        return result

    # 检查长度
    if len(password) < 8:
        result["errors"].append("Password must be at least 8 characters long")
    else:
        result["score"] += 1

    # 检查大写字母
    if not any(c.isupper() for c in password):
        result["errors"].append("Password must contain at least one uppercase letter")
    else:
        result["score"] += 1

    # 检查小写字母
    if not any(c.islower() for c in password):
        result["errors"].append("Password must contain at least one lowercase letter")
    else:
        result["score"] += 1

    # 检查数字
    if not any(c.isdigit() for c in password):
        result["errors"].append("Password must contain at least one digit")
    else:
        result["score"] += 1

    # 检查特殊字符
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        result["errors"].append("Password must contain at least one special character")
    else:
        result["score"] += 1

    result["is_valid"] = len(result["errors"]) == 0
    return result
