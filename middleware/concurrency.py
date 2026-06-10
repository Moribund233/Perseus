"""
并发限制中间件

限制同时处理的请求数量，防止服务因过多并发请求而挂起
"""
import asyncio
import logging
import time
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class ConcurrencyLimiter:
    """
    并发限制器

    使用信号量控制同时处理的请求数量

    Attributes:
        max_concurrent: 最大并发请求数
        semaphore: 异步信号量
    """

    def __init__(self, max_concurrent: int = 100):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def acquire(self) -> bool:
        """
        获取执行许可

        Returns:
            bool: 是否成功获取（信号量总是成功获取或阻塞）
        """
        await self.semaphore.acquire()
        return True

    def release(self):
        """释放执行许可"""
        try:
            self.semaphore.release()
        except ValueError:
            # 信号量已经满了，忽略
            pass

    @property
    def current_requests(self) -> int:
        """当前正在处理的请求数（基于信号量剩余许可数推导）"""
        # semaphore._value 是 CPython 内部实现，但作为唯一获取当前许可数的方式被广泛使用
        return self.max_concurrent - self.semaphore._value

    @property
    def available_slots(self) -> int:
        """可用的并发槽位数"""
        return self.semaphore._value


class ConcurrencyMiddleware(BaseHTTPMiddleware):
    """
    并发限制中间件

    限制同时处理的请求数量，超过限制时返回 503 Service Unavailable

    Attributes:
        limiter: 并发限制器实例
        max_wait_time: 最大等待时间（秒），超过此时间返回 503
    """

    def __init__(
        self,
        app: ASGIApp,
        max_concurrent: int = 100,
        max_wait_time: float = 5.0
    ):
        super().__init__(app)
        self.limiter = ConcurrencyLimiter(max_concurrent)
        self.max_wait_time = max_wait_time

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求，添加并发控制

        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 响应对象
        """
        # 健康检查端点不受限制
        if request.url.path == "/health":
            return await call_next(request)

        start_time = time.time()

        try:
            # 使用 wait_for 限制等待时间
            await asyncio.wait_for(
                self.limiter.acquire(),
                timeout=self.max_wait_time
            )
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.warning(
                f"并发限制: 请求等待超时 "
                f"({request.method} {request.url.path}, "
                f"等待时间: {elapsed:.2f}s, "
                f"当前并发: {self.limiter.current_requests})"
            )
            return self._create_503_response(
                f"服务器繁忙，当前并发请求数: {self.limiter.current_requests}"
            )
        except Exception as e:
            logger.error(f"并发限制异常: {e}")
            return self._create_503_response(f"并发控制异常: {str(e)}")

        try:
            # 执行请求
            response = await call_next(request)

            # 添加并发信息头（调试用）
            response.headers["X-Current-Concurrency"] = str(self.limiter.current_requests)
            response.headers["X-Available-Slots"] = str(self.limiter.available_slots)

            return response

        finally:
            # 释放执行许可
            self.limiter.release()

    def _create_503_response(self, message: str) -> JSONResponse:
        """
        创建 503 响应

        Args:
            message: 错误消息

        Returns:
            JSONResponse: 503 响应对象
        """
        return JSONResponse(
            status_code=503,
            content={
                "detail": "服务器繁忙",
                "error": {
                    "type": "service_unavailable",
                    "message": message,
                    "current_concurrency": self.limiter.current_requests,
                    "max_concurrency": self.limiter.max_concurrent
                }
            },
            headers={
                "Retry-After": "5"  # 建议客户端 5 秒后重试
            }
        )


def setup_concurrency_middleware(
    app: ASGIApp,
    max_concurrent: int = 100,
    max_wait_time: float = 5.0
) -> ASGIApp:
    """
    配置并发限制中间件

    Args:
        app: FastAPI 应用实例
        max_concurrent: 最大并发请求数
        max_wait_time: 最大等待时间（秒）

    Returns:
        ASGIApp: 配置了中间件的应用实例
    """
    from fastapi import FastAPI

    if isinstance(app, FastAPI):
        app.add_middleware(
            ConcurrencyMiddleware,
            max_concurrent=max_concurrent,
            max_wait_time=max_wait_time
        )
        logger.info(f"并发限制中间件已启用: max_concurrent={max_concurrent}, max_wait_time={max_wait_time}s")

    return app
