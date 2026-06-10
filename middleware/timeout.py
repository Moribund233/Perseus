"""
请求耗时日志中间件

记录请求处理时间，当超过阈值时发出警告
"""
import logging
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestTimeLoggerMiddleware(BaseHTTPMiddleware):
    """
    请求耗时日志中间件

    记录所有请求的处理时间，当超过阈值时发出警告日志

    Attributes:
        threshold_seconds: 请求处理时间警告阈值（秒）
    """

    def __init__(self, app: ASGIApp, threshold_seconds: float = 30.0):
        super().__init__(app)
        self.threshold_seconds = threshold_seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求，记录处理时间

        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 响应对象
        """
        start_time = time.time()

        try:
            response = await call_next(request)

            elapsed = time.time() - start_time
            if elapsed > self.threshold_seconds:
                logger.warning(
                    f"请求处理时间超过阈值: {request.method} {request.url.path} "
                    f"({elapsed:.2f}s > {self.threshold_seconds}s)"
                )

            return response

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"请求处理异常 ({elapsed:.2f}s): {e}")
            raise


def setup_request_time_logger_middleware(app: ASGIApp, threshold_seconds: float = 30.0) -> ASGIApp:
    """
    配置请求耗时日志中间件

    Args:
        app: FastAPI 应用实例
        threshold_seconds: 处理时间警告阈值（秒）

    Returns:
        ASGIApp: 配置了中间件的应用实例
    """
    from fastapi import FastAPI

    if isinstance(app, FastAPI):
        app.add_middleware(RequestTimeLoggerMiddleware, threshold_seconds=threshold_seconds)
        logger.info(f"请求耗时日志中间件已启用，阈值: {threshold_seconds}s")

    return app


# 保留旧名称的别名，用于向后兼容
TimeoutMiddleware = RequestTimeLoggerMiddleware
setup_timeout_middleware = setup_request_time_logger_middleware
