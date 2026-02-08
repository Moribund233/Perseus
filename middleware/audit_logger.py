"""
审计日志中间件

记录所有 HTTP 请求和响应的关键信息，用于安全审计
"""
import json
import os
import time
import uuid
from datetime import datetime
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from logging.handlers import RotatingFileHandler
import logging

from config import get_config

# 获取配置
_config = get_config()
_logging_config = _config.logging

# 创建审计日志记录器
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# 确保处理器只被添加一次
if not audit_logger.handlers:
    # 获取日志路径
    log_path = _logging_config.audit_log_path

    # 确保日志目录存在
    log_dir = os.path.dirname(log_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 创建轮转文件处理器
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=_logging_config.audit_log_max_size,
        backupCount=_logging_config.audit_log_backup_count,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    audit_logger.addHandler(file_handler)


class AuditLoggerMiddleware(BaseHTTPMiddleware):
    """
    审计日志中间件

    记录以下信息：
    - 请求 ID（用于追踪）
    - 请求时间
    - 客户端 IP 地址
    - 请求方法和路径
    - 用户代理
    - 认证用户
    - 响应状态码
    - 处理时间
    - 敏感操作标记
    """

    # 敏感路径模式（需要特别记录）
    SENSITIVE_PATHS = [
        "/git/",           # Git 操作
        "/api/users",      # 用户管理
        "/api/repositories", # 仓库管理
        "/login",
        "/logout",
        "/auth"
    ]

    # 敏感操作 HTTP 方法
    SENSITIVE_METHODS = ["POST", "PUT", "DELETE", "PATCH"]

    # 敏感字段（需要过滤）
    SENSITIVE_FIELDS = ['password', 'token', 'secret', 'authorization', 'api_key', 'access_token', 'refresh_token']

    def __init__(
        self,
        app,
        log_request_body: bool = False,
        log_response_body: bool = False,
        exclude_paths: Optional[list] = None
    ):
        """
        初始化审计日志中间件

        Args:
            app: FastAPI 应用实例
            log_request_body: 是否记录请求体（可能包含敏感信息）
            log_response_body: 是否记录响应体
            exclude_paths: 排除记录的路径列表
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]

    def _should_log(self, path: str) -> bool:
        """
        检查是否应该记录该路径

        Args:
            path: 请求路径

        Returns:
            bool: 是否应该记录
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        return True

    def _is_sensitive_operation(self, method: str, path: str) -> bool:
        """
        检查是否是敏感操作

        Args:
            method: HTTP 方法
            path: 请求路径

        Returns:
            bool: 是否是敏感操作
        """
        # 检查是否是敏感方法
        is_sensitive_method = method in self.SENSITIVE_METHODS

        # 检查是否是敏感路径
        is_sensitive_path = any(
            sensitive_path in path
            for sensitive_path in self.SENSITIVE_PATHS
        )

        return is_sensitive_method or is_sensitive_path

    def _filter_sensitive_data(self, data: dict) -> dict:
        """
        过滤敏感字段

        Args:
            data: 原始数据字典

        Returns:
            dict: 过滤后的数据字典
        """
        if not isinstance(data, dict):
            return data

        filtered = {}
        for key, value in data.items():
            if any(field in key.lower() for field in self.SENSITIVE_FIELDS):
                filtered[key] = '***'
            elif isinstance(value, dict):
                filtered[key] = self._filter_sensitive_data(value)
            elif isinstance(value, list):
                filtered[key] = [
                    self._filter_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                filtered[key] = value
        return filtered

    def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端真实 IP 地址

        Args:
            request: HTTP 请求对象

        Returns:
            str: 客户端 IP 地址
        """
        # 检查反向代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 直接连接
        if request.client:
            return request.client.host

        return "unknown"

    def _get_user_info(self, request: Request) -> dict:
        """
        获取用户信息

        Args:
            request: HTTP 请求对象

        Returns:
            dict: 用户信息
        """
        user_info = {
            "user_id": None,
            "username": None,
            "auth_type": None
        }

        # 从请求状态中获取用户信息（由认证中间件设置）
        if hasattr(request.state, "user"):
            user = request.state.user
            user_info["user_id"] = getattr(user, "id", None)
            user_info["username"] = getattr(user, "username", None)
            user_info["auth_type"] = "token"

        # 从 Authorization 头解析
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            user_info["auth_type"] = "basic"
        elif auth_header.startswith("Bearer "):
            user_info["auth_type"] = "bearer"

        return user_info

    async def dispatch(self, request: Request, call_next):
        """
        处理请求并记录审计日志

        Args:
            request: HTTP 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: HTTP 响应
        """
        # 如果审计日志被禁用，直接处理请求
        if not _logging_config.audit_log_enabled:
            return await call_next(request)

        # 生成请求 ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # 记录开始时间
        start_time = time.time()

        # 获取请求信息
        method = request.method
        path = request.url.path
        query_params = str(request.query_params)

        # 检查是否应该记录
        if not self._should_log(path):
            return await call_next(request)

        # 获取客户端信息
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        user_info = self._get_user_info(request)

        # 检查是否是敏感操作
        is_sensitive = self._is_sensitive_operation(method, path)

        # 可选：记录请求体
        request_body = None
        if self.log_request_body and method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    body_json = json.loads(body)
                    request_body = self._filter_sensitive_data(body_json)
            except Exception:
                pass  # 如果无法解析请求体，忽略错误

        # 处理请求
        try:
            response = await call_next(request)
            status_code = response.status_code
            error_message = None
        except Exception as e:
            status_code = 500
            error_message = str(e)
            raise
        finally:
            # 计算处理时间
            process_time = (time.time() - start_time) * 1000

            # 构建审计日志条目
            audit_entry = {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "client_ip": client_ip,
                "method": method,
                "path": path,
                "query_params": query_params if query_params else None,
                "user_agent": user_agent[:200],  # 限制长度
                "user_id": user_info["user_id"],
                "username": user_info["username"],
                "auth_type": user_info["auth_type"],
                "status_code": status_code,
                "process_time_ms": round(process_time, 2),
                "is_sensitive": is_sensitive,
                "error": error_message
            }

            # 如果记录了请求体，添加到日志条目
            if request_body:
                audit_entry["request_body"] = request_body

            # 记录日志
            log_message = json.dumps(audit_entry, ensure_ascii=False, default=str)

            # 根据状态码和操作类型选择日志级别
            if status_code >= 500:
                audit_logger.error(log_message)
            elif status_code >= 400:
                audit_logger.warning(log_message)
            elif is_sensitive:
                audit_logger.info(f"[SENSITIVE] {log_message}")
            else:
                audit_logger.info(log_message)

        return response


def log_security_event(
    event_type: str,
    description: str,
    user_id: Optional[int] = None,
    client_ip: Optional[str] = None,
    details: Optional[dict] = None
):
    """
    记录安全事件

    用于在非中间件场景中记录安全相关事件，如：
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
    """
    event = {
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        "description": description,
        "user_id": user_id,
        "client_ip": client_ip,
        "details": details or {}
    }

    log_message = json.dumps(event, ensure_ascii=False, default=str)
    audit_logger.warning(f"[SECURITY] {log_message}")
