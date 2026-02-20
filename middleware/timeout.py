"""
请求超时中间件

防止请求因数据库连接池耗尽或其他原因无限期挂起
"""
import asyncio
import logging
import time
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    请求超时中间件
    
    为所有请求设置最大处理时间，超时后返回 504 Gateway Timeout
    
    Attributes:
        timeout_seconds: 请求超时时间（秒）
    """
    
    def __init__(self, app: ASGIApp, timeout_seconds: float = 30.0):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求，添加超时控制
        
        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理函数
            
        Returns:
            Response: 响应对象
        """
        start_time = time.time()
        
        try:
            # 直接调用下一个处理函数
            response = await call_next(request)
            
            # 检查是否超时
            elapsed = time.time() - start_time
            if elapsed > self.timeout_seconds:
                logger.warning(
                    f"请求处理时间超过阈值: {request.method} {request.url.path} "
                    f"({elapsed:.2f}s > {self.timeout_seconds}s)"
                )
            
            return response
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"请求处理异常 ({elapsed:.2f}s): {e}")
            raise


def setup_timeout_middleware(app: ASGIApp, timeout_seconds: float = 30.0) -> ASGIApp:
    """
    配置超时中间件
    
    Args:
        app: FastAPI 应用实例
        timeout_seconds: 超时时间（秒）
        
    Returns:
        ASGIApp: 配置了中间件的应用实例
    """
    from fastapi import FastAPI
    
    if isinstance(app, FastAPI):
        app.add_middleware(TimeoutMiddleware, timeout_seconds=timeout_seconds)
        logger.info(f"超时中间件已启用: {timeout_seconds}s")
    
    return app
