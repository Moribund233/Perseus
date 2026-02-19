"""
审计日志中间件

记录所有 HTTP 请求和响应的关键信息，用于安全审计
"""
import json
import time
import uuid
from datetime import datetime
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from utils.logging import get_audit_logger
from utils.security_utils import filter_sensitive_data


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
        "/api/repositories",  # 仓库管理
        "/login",
        "/logout",
        "/auth"
    ]

    # 敏感操作 HTTP 方法
    SENSITIVE_METHODS = ["POST", "PUT", "DELETE", "PATCH"]

    # 默认排除的路径（健康检查、监控、文档等）
    DEFAULT_EXCLUDE_PATHS = [
        "/health",
        "/docs",
        "/openapi.json",
        "/api/app/status",      # 应用状态监控
        "/api/app/metrics",     # 指标监控
        "/api/app/health",      # 健康检查
    ]

    def __init__(
        self,
        app,
        log_request_body: bool = False,
        log_response_body: bool = False,
        exclude_paths: Optional[list] = None,
        enabled: bool = True
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        # 合并默认排除路径和用户自定义路径
        self.exclude_paths = self.DEFAULT_EXCLUDE_PATHS + (exclude_paths or [])
        self.enabled = enabled
        # 使用新的简化版审计日志记录器
        self._audit_logger = get_audit_logger()

    def _should_log(self, path: str) -> bool:
        """检查是否应该记录该路径"""
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        return True

    def _is_sensitive_operation(self, method: str, path: str) -> bool:
        """检查是否是敏感操作"""
        is_sensitive_method = method in self.SENSITIVE_METHODS
        is_sensitive_path = any(sensitive_path in path for sensitive_path in self.SENSITIVE_PATHS)
        return is_sensitive_method or is_sensitive_path

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP 地址"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"

    def _get_user_info(self, request: Request) -> dict:
        """获取用户信息"""
        user_info = {"user_id": None, "username": None, "auth_type": None}

        if hasattr(request.state, "user"):
            user = request.state.user
            user_info["user_id"] = getattr(user, "id", None)
            user_info["username"] = getattr(user, "username", None)
            user_info["auth_type"] = "token"

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            user_info["auth_type"] = "basic"
        elif auth_header.startswith("Bearer "):
            user_info["auth_type"] = "bearer"

        return user_info

    async def dispatch(self, request: Request, call_next):
        """处理请求并记录审计日志"""
        if not self.enabled:
            return await call_next(request)

        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start_time = time.time()
        method = request.method
        path = request.url.path
        query_params = str(request.query_params)

        if not self._should_log(path):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        user_info = self._get_user_info(request)
        is_sensitive = self._is_sensitive_operation(method, path)

        # 可选：记录请求体
        request_body = None
        if self.log_request_body and method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    body_json = json.loads(body)
                    request_body = filter_sensitive_data(body_json)
            except Exception:
                pass

        # 处理请求
        error_message = None
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            error_message = str(e)
            raise
        finally:
            process_time = (time.time() - start_time) * 1000

            audit_entry = {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "client_ip": client_ip,
                "method": method,
                "path": path,
                "query_params": query_params if query_params else None,
                "user_agent": user_agent[:200],
                "user_id": user_info["user_id"],
                "username": user_info["username"],
                "auth_type": user_info["auth_type"],
                "status_code": status_code,
                "process_time_ms": round(process_time, 2),
                "is_sensitive": is_sensitive,
                "error": error_message
            }

            if request_body:
                audit_entry["request_body"] = request_body

            log_message = json.dumps(audit_entry, ensure_ascii=False, default=str)

            # 根据状态码和操作类型选择日志级别
            if status_code >= 500:
                self._audit_logger.error(log_message)
            elif status_code >= 400:
                self._audit_logger.warning(log_message)
            elif is_sensitive:
                self._audit_logger.info(f"[SENSITIVE] {log_message}")
            else:
                self._audit_logger.info(log_message)

        return response


def setup_audit_logging(app, enabled: bool = True, **kwargs):
    """
    配置审计日志中间件

    Args:
        app: FastAPI 应用实例
        enabled: 是否启用审计日志
        **kwargs: 其他配置参数
    """
    app.add_middleware(
        AuditLoggerMiddleware,
        enabled=enabled,
        **kwargs
    )
