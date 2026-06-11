"""
应用生命周期管理模块

提供应用启动和关闭时的资源初始化和清理工作。

Docker/Uvicorn 单进程模式：
- 启动：验证数据库连接、初始化 WebSocket 心跳
- 关闭：优雅关闭 WebSocket 连接、释放数据库连接池

使用 FastAPI 的 lifespan 上下文管理器实现
"""
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any, Optional

from fastapi import FastAPI

from models.async_db import get_async_engine
from api.websocket.manager import manager as websocket_manager

logger = logging.getLogger(__name__)


class AppLifecycleManager:
    """
    应用生命周期管理器

    管理应用启动和关闭时的资源初始化和清理工作。
    单进程模式（适用于 Uvicorn / Docker）。
    """

    def __init__(self):
        self._websocket_manager = websocket_manager
        self._is_shutting_down = False

    async def startup(self) -> None:
        """
        应用启动时执行的初始化操作

        包括：
        - 初始化数据库引擎
        - 验证数据库连接
        - 初始化 WebSocket 心跳检查

        Raises:
            Exception: 数据库引擎初始化或连接验证失败时抛出异常，
                       阻止应用在不健康状态下启动
        """
        # 初始化异步数据库引擎（延迟加载） — 致命错误，必须阻止启动
        await self._init_async_database()
        await self._verify_database_connection()

        # 初始化 WebSocket 心跳检查 — 非致命错误，打日志即可
        try:
            await self._init_websocket_manager()
        except Exception as e:
            logger.warning(f"WebSocket 管理器初始化失败（不影响服务启动）: {e}")

    async def _init_async_database(self) -> None:
        """初始化异步数据库引擎"""
        from models.async_db import get_async_engine
        engine = get_async_engine()
        if engine is None:
            raise Exception("异步数据库引擎初始化失败")

    async def shutdown(self) -> None:
        """
        应用关闭时执行的清理操作
        """
        if self._is_shutting_down:
            return

        self._is_shutting_down = True

        logger.info("开始执行关闭流程...")

        await self._shutdown_websocket_connections()
        await self._dispose_database_engine()

        logger.info("关闭流程执行完成")

    async def _verify_database_connection(self) -> None:
        """验证数据库连接是否正常"""
        from sqlalchemy import text
        from models.async_db import get_async_engine
        engine = get_async_engine()
        if engine is None:
            raise Exception("异步数据库引擎未初始化")
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.commit()

    async def _init_websocket_manager(self) -> None:
        """初始化 WebSocket 管理器"""
        try:
            asyncio.create_task(self._websocket_manager.heartbeat_checker())
        except Exception as e:
            logger.error(f"WebSocket 管理器初始化失败: {e}")
            raise

    async def _shutdown_websocket_connections(self) -> None:
        """优雅关闭所有 WebSocket 连接"""
        try:
            active_connections = list(self._websocket_manager.active_connections.values())

            if not active_connections:
                return

            close_message = {
                "type": "system",
                "event": "shutdown",
                "message": "服务器即将关闭，连接将被断开"
            }

            await self._websocket_manager.broadcast(close_message)
            await asyncio.sleep(0.5)

            for connection in active_connections:
                try:
                    await connection.websocket.close(code=1001, reason="服务器关闭")
                except Exception:
                    pass

            self._websocket_manager.active_connections.clear()
            self._websocket_manager.user_connections.clear()

        except Exception as e:
            logger.error(f"关闭 WebSocket 连接时出错: {e}")

    async def _dispose_database_engine(self) -> None:
        """释放数据库连接池"""
        try:
            from models.async_db import close_async_engine
            await close_async_engine()
        except Exception as e:
            logger.error(f"释放异步数据库连接池时出错: {e}")

    def is_shutting_down(self) -> bool:
        """检查是否正在关闭"""
        return self._is_shutting_down


# 全局生命周期管理器实例
_lifecycle_manager: AppLifecycleManager = AppLifecycleManager()


def get_lifecycle_manager() -> AppLifecycleManager:
    """
    获取生命周期管理器实例

    Returns:
        AppLifecycleManager: 生命周期管理器实例
    """
    return _lifecycle_manager


def reset_lifecycle_manager() -> None:
    """重置生命周期管理器实例（用于测试）"""
    global _lifecycle_manager
    _lifecycle_manager = AppLifecycleManager()


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[Dict[str, Any], None]:
    """
    FastAPI lifespan 上下文管理器

    用法:
        app = FastAPI(lifespan=app_lifespan)

    Args:
        app: FastAPI 应用实例

    Yields:
        Dict[str, Any]: 应用状态字典
    """
    manager = get_lifecycle_manager()

    try:
        await manager.startup()
        yield {"lifecycle_manager": manager}
    finally:
        await manager.shutdown()


def trigger_graceful_shutdown(reason: str = "manual") -> bool:
    """
    触发优雅关闭

    可以被外部调用（如 shutdown 接口）来触发应用关闭流程。
    单进程模式下直接触发关闭。

    Args:
        reason: 关闭原因

    Returns:
        bool: 是否成功触发关闭
    """
    manager = get_lifecycle_manager()

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(manager.shutdown())
        loop.close()

        # 发送终止信号
        pid = os.getpid()
        logger.info(f"发送终止信号到进程 {pid}")

        import signal
        os.kill(pid, signal.SIGTERM)

        return True
    except Exception as e:
        logger.error(f"执行关闭流程时出错: {e}")
        import sys
        sys.exit(1)


def is_shutdown_requested() -> bool:
    """
    检查是否已请求关闭

    Returns:
        bool: 是否已请求关闭
    """
    return get_lifecycle_manager().is_shutting_down()
