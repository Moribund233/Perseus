"""
应用生命周期管理模块

提供完整的应用生命周期管理：
- 启动时初始化：数据库连接池、WebSocket管理器、日志系统
- 关闭时清理：优雅关闭WebSocket连接、释放数据库连接池、停止后台任务

使用 FastAPI 的 lifespan 上下文管理器实现
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI

from models import engine
from api.websocket.manager import manager as websocket_manager

logger = logging.getLogger(__name__)


class AppLifecycleManager:
    """
    应用生命周期管理器
    
    管理应用启动和关闭时的资源初始化和清理工作
    """
    
    def __init__(self):
        self._shutdown_event = asyncio.Event()
        self._websocket_manager = websocket_manager
        self._is_shutting_down = False
    
    async def startup(self) -> None:
        """
        应用启动时执行的初始化操作
        
        包括：
        - 记录启动日志
        - 数据库类型变更检测和迁移检查
        - 验证数据库连接
        - 初始化WebSocket管理器
        """
        logger.info("=" * 60)
        logger.info("应用启动中...")
        logger.info("=" * 60)
        
        # 数据库类型变更检测
        migration_status = await self._check_database_migration()
        if migration_status.get("migration_required"):
            logger.warning(f"检测到数据库类型变更: {migration_status.get('current_db_type')} -> {migration_status.get('target_db_type')}")
            logger.warning("需要执行数据迁移，请通过前端界面确认迁移")
        
        # 验证数据库连接
        await self._verify_database_connection()
        
        # 初始化WebSocket管理器（启动心跳检测任务）
        await self._init_websocket_manager()
        
        logger.info("应用启动完成")
    
    async def _check_database_migration(self) -> Dict[str, Any]:
        """
        检查数据库类型变更和迁移需求
        
        Returns:
            Dict[str, Any]: 迁移状态信息
        """
        try:
            import os
            from config import get_config
            
            config = get_config()
            
            # 从环境变量获取实际数据库类型
            actual_url = os.environ.get("DATABASE_URL", "")
            actual_type = self._parse_db_type(actual_url)
            
            # 获取记录的数据库类型
            recorded_type = config.database.current_db_type
            
            # 首次启动
            if recorded_type is None:
                logger.info(f"首次启动，记录数据库类型: {actual_type}")
                config.database.current_db_type = actual_type
                # 保存配置
                self._save_config(config)
                return {
                    "migration_required": False,
                    "message": "首次启动，初始化数据库记录",
                    "current_db_type": actual_type,
                    "target_db_type": actual_type
                }
            
            # 类型一致
            if actual_type == recorded_type:
                return {
                    "migration_required": False,
                    "message": "数据库类型一致",
                    "current_db_type": recorded_type,
                    "target_db_type": actual_type
                }
            
            # 类型变更，需要检查是否有数据
            logger.info(f"检测到数据库类型变更: {recorded_type} -> {actual_type}")
            
            # 注意：这里需要获取旧数据库的URL来检查数据
            # 但URL是敏感信息，存储在客户端加密配置中
            # 服务端无法直接访问，需要前端提供
            # 这里只返回迁移需求，具体检查由迁移API处理
            
            return {
                "migration_required": True,
                "message": f"检测到数据库类型变更: {recorded_type} -> {actual_type}",
                "current_db_type": recorded_type,
                "target_db_type": actual_type
            }
            
        except Exception as e:
            logger.error(f"数据库迁移检查失败: {e}")
            return {
                "migration_required": False,
                "message": f"检查失败: {str(e)}",
                "current_db_type": None,
                "target_db_type": None
            }
    
    def _parse_db_type(self, url: str) -> str:
        """从数据库URL解析类型"""
        url_lower = url.lower()
        if url_lower.startswith("sqlite"):
            return "sqlite"
        elif url_lower.startswith("postgresql") or url_lower.startswith("postgres"):
            return "postgresql"
        elif url_lower.startswith("mysql"):
            return "mysql"
        else:
            return "unknown"
    
    def _save_config(self, config) -> None:
        """保存配置到文件"""
        try:
            import toml
            from config import ConfigManager
            
            config_manager = ConfigManager()
            config_manager._cache = config
            config_manager._cache_time = 0  # 强制下次重新加载
            
            # 保存到文件
            config_data = {
                "server": config.server.model_dump(),
                "app": config.app.model_dump(),
                "cors": config.cors.model_dump(),
                "proxy": config.proxy.model_dump(),
                "storage": config.storage.model_dump(),
                "security": config.security.model_dump(),
                "logging": config.logging.model_dump(),
                "rate_limit": config.rate_limit.model_dump(),
                "database": {
                    k: v for k, v in config.database.model_dump().items()
                    if k not in ["url", "is_stress_test"]  # 排除环境变量注入的配置
                }
            }
            
            with open(config_manager.config_path, "w", encoding="utf-8") as f:
                toml.dump(config_data, f)
                
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    async def shutdown(self) -> None:
        """
        应用关闭时执行的清理操作
        
        包括：
        - 标记关闭状态，阻止新请求
        - 优雅关闭所有WebSocket连接
        - 释放数据库连接池
        - 清理其他资源
        """
        if self._is_shutting_down:
            logger.warning("关闭流程已在进行中，跳过重复调用")
            return
        
        self._is_shutting_down = True
        logger.info("=" * 60)
        logger.info("应用关闭中...")
        logger.info("=" * 60)
        
        # 触发关闭事件，通知所有监听者
        self._shutdown_event.set()
        
        # 1. 优雅关闭WebSocket连接
        await self._shutdown_websocket_connections()
        
        # 2. 释放数据库连接池
        await self._dispose_database_engine()
        
        logger.info("应用关闭完成")
    
    async def _verify_database_connection(self) -> None:
        """验证数据库连接是否正常"""
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            logger.info("数据库连接验证成功")
        except Exception as e:
            logger.error(f"数据库连接验证失败: {e}")
            raise
    
    async def _init_websocket_manager(self) -> None:
        """初始化WebSocket管理器"""
        try:
            # 启动WebSocket心跳检测任务
            asyncio.create_task(self._websocket_manager.heartbeat_checker())
            logger.info("WebSocket管理器初始化完成")
        except Exception as e:
            logger.error(f"WebSocket管理器初始化失败: {e}")
            raise
    
    async def _shutdown_websocket_connections(self) -> None:
        """优雅关闭所有WebSocket连接"""
        try:
            logger.info("正在关闭WebSocket连接...")
            
            # 获取所有活跃连接
            active_connections = list(self._websocket_manager.active_connections.values())
            
            if not active_connections:
                logger.info("没有活跃的WebSocket连接")
                return
            
            logger.info(f"需要关闭 {len(active_connections)} 个WebSocket连接")
            
            # 发送关闭通知
            close_message = {
                "type": "system",
                "event": "shutdown",
                "message": "服务器即将关闭，连接将被断开"
            }
            
            # 广播关闭通知给所有连接
            await self._websocket_manager.broadcast(close_message)
            
            # 给客户端一点时间处理关闭通知
            await asyncio.sleep(0.5)
            
            # 关闭所有连接
            for connection in active_connections:
                try:
                    await connection.websocket.close(code=1001, reason="服务器关闭")
                except Exception as e:
                    logger.debug(f"关闭WebSocket连接时出错: {e}")
            
            # 清空连接管理器
            self._websocket_manager.active_connections.clear()
            self._websocket_manager.user_connections.clear()
            
            logger.info("WebSocket连接已关闭")
            
        except Exception as e:
            logger.error(f"关闭WebSocket连接时出错: {e}")
    
    async def _dispose_database_engine(self) -> None:
        """释放数据库连接池"""
        try:
            logger.info("正在释放数据库连接池...")
            
            # 同步引擎使用 run_in_executor 进行异步释放
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, engine.dispose)
            
            logger.info("同步数据库连接池已释放")
        except Exception as e:
            logger.error(f"释放同步数据库连接池时出错: {e}")
        
        # 关闭异步数据库引擎
        try:
            from models.async_db import close_async_engine
            await close_async_engine()
            logger.info("异步数据库连接池已释放")
        except Exception as e:
            logger.error(f"释放异步数据库连接池时出错: {e}")
    
    def is_shutting_down(self) -> bool:
        """检查是否正在关闭"""
        return self._is_shutting_down
    
    async def wait_for_shutdown(self) -> None:
        """等待关闭信号"""
        await self._shutdown_event.wait()


# 全局生命周期管理器实例
_lifecycle_manager: AppLifecycleManager = AppLifecycleManager()


def get_lifecycle_manager() -> AppLifecycleManager:
    """
    获取生命周期管理器实例
    
    Returns:
        AppLifecycleManager: 生命周期管理器实例
    """
    return _lifecycle_manager


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[Dict[str, Any], None]:
    """
    FastAPI lifespan 上下文管理器
    
    用法:
        app = FastAPI(lifespan=app_lifespan)
    
    Args:
        app: FastAPI应用实例
        
    Yields:
        Dict[str, Any]: 应用状态字典
    """
    manager = get_lifecycle_manager()
    
    try:
        # 启动
        await manager.startup()
        yield {"lifecycle_manager": manager}
    finally:
        # 关闭
        await manager.shutdown()


def trigger_graceful_shutdown() -> None:
    """
    触发优雅关闭
    
    可以被外部调用（如shutdown接口）来触发应用关闭流程
    """
    manager = get_lifecycle_manager()
    
    # 在后台任务中执行关闭，避免阻塞当前请求
    asyncio.create_task(_execute_shutdown(manager))


async def _execute_shutdown(manager: AppLifecycleManager) -> None:
    """执行关闭流程"""
    try:
        # 给响应一点时间返回
        await asyncio.sleep(0.5)
        
        # 触发关闭
        await manager.shutdown()
        
        # 终止进程
        import os
        import signal
        import sys
        
        pid = os.getpid()
        logger.info(f"发送终止信号到进程 {pid}")
        
        if os.name == 'nt':  # Windows
            os.kill(pid, signal.SIGTERM)
        else:  # Unix/Linux/Mac
            os.kill(pid, signal.SIGTERM)
            
    except Exception as e:
        logger.error(f"执行关闭流程时出错: {e}")
        # 强制退出
        import sys
        sys.exit(1)
