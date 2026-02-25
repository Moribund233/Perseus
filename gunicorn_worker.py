"""
自定义Gunicorn Uvicorn Worker

扩展标准UvicornWorker以支持：
- 应用生命周期管理集成
- IPC通信初始化
- 优雅关闭处理

使用方法:
    gunicorn -k gunicorn_worker.LanGitUvicornWorker app:get_app()
"""
import os
import asyncio
import logging
from typing import Any

from uvicorn.workers import UvicornWorker

logger = logging.getLogger(__name__)


class LanGitUvicornWorker(UvicornWorker):
    """
    LanGit自定义Uvicorn Worker
    
    扩展标准UvicornWorker，添加：
    1. 生命周期管理器集成
    2. IPC通信初始化
    3. 优雅关闭支持
    """
    
    CONFIG_KWARGS = {
        "loop": "uvloop" if os.name != 'nt' else "asyncio",
        "http": "httptools" if os.name != 'nt' else "h11",
        "lifespan": "on",
    }
    
    def __init__(self, *args, **kwargs):
        """初始化Worker"""
        super().__init__(*args, **kwargs)
        self._worker_id: int = 0
        self._lifecycle_manager: Any = None
    
    def init_process(self) -> None:
        """
        初始化Worker进程
        
        在父进程中调用fork后，在子进程中执行
        """
        # 获取worker ID（使用pid作为唯一标识）
        self._worker_id = os.getpid()
        
        # 调用父类初始化
        super().init_process()
    
    async def _init_lifecycle_manager(self) -> None:
        """初始化生命周期管理器"""
        try:
            from lifespan import get_lifecycle_manager
            
            self._lifecycle_manager = get_lifecycle_manager()
            master_pid = os.getppid()
            
            # 设置为Worker模式
            self._lifecycle_manager.setup_for_worker(self._worker_id, master_pid)
            
            logger.info(
                f"Worker {self._worker_id} 生命周期管理器初始化完成 "
                f"(Master PID: {master_pid})"
            )
        except Exception as e:
            logger.error(f"Worker {self._worker_id} 生命周期管理器初始化失败: {e}")
    
    def run(self) -> None:
        """
        运行Worker
        
        覆盖父类run方法以添加自定义初始化逻辑
        """
        # 初始化生命周期管理器
        try:
            # 创建临时事件循环来执行异步初始化
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._init_lifecycle_manager())
            loop.close()
        except Exception as e:
            logger.error(f"Worker初始化失败: {e}")
        
        # 调用父类run方法
        super().run()
    
    async def _shutdown_lifecycle_manager(self) -> None:
        """关闭生命周期管理器"""
        if self._lifecycle_manager:
            try:
                await self._lifecycle_manager.shutdown()
                logger.info(f"Worker {self._worker_id} 生命周期管理器已关闭")
            except Exception as e:
                logger.error(f"Worker {self._worker_id} 生命周期管理器关闭失败: {e}")

    def handle_exit(self, sig: int, frame: Any) -> None:
        """
        处理退出信号

        Args:
            sig: 信号编号
            frame: 当前栈帧
        """
        logger.info(f"Worker {self._worker_id} 收到退出信号 {sig}")

        # 执行生命周期关闭
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._shutdown_lifecycle_manager())
            loop.close()
        except Exception as e:
            logger.error(f"Worker {self._worker_id} 关闭处理失败: {e}")

        # 调用父类处理
        super().handle_exit(sig, frame)

    def handle_quit(self, sig: int, frame: Any) -> None:
        """
        处理QUIT信号

        Args:
            sig: 信号编号
            frame: 当前栈帧
        """
        logger.info(f"Worker {self._worker_id} 收到QUIT信号")
        super().handle_quit(sig, frame)

    def handle_term(self, sig: int, frame: Any) -> None:
        """
        处理TERM信号

        Args:
            sig: 信号编号
            frame: 当前栈帧
        """
        logger.info(f"Worker {self._worker_id} 收到TERM信号")
        super().handle_term(sig, frame)

    def handle_int(self, sig: int, frame: Any) -> None:
        """
        处理INT信号

        Args:
            sig: 信号编号
            frame: 当前栈帧
        """
        logger.info(f"Worker {self._worker_id} 收到INT信号")
        super().handle_int(sig, frame)

    def handle_usr1(self, sig: int, frame: Any) -> None:
        """
        处理USR1信号（通常用于日志轮转）

        Args:
            sig: 信号编号
            frame: 当前栈帧
        """
        logger.info(f"Worker {self._worker_id} 收到USR1信号")
        super().handle_usr1(sig, frame)

    def handle_usr2(self, sig: int, frame: Any) -> None:
        """
        处理USR2信号（通常用于优雅重启）

        Args:
            sig: 信号编号
            frame: 当前栈帧
        """
        logger.info(f"Worker {self._worker_id} 收到USR2信号")
        super().handle_usr2(sig, frame)
    
    def handle_winch(self, sig: int, frame: Any) -> None:
        """
        处理WINCH信号（通常用于窗口大小改变）
        
        Args:
            sig: 信号编号
            frame: 当前栈帧
        """
        # Windows不支持WINCH信号
        if os.name != 'nt':
            super().handle_winch(sig, frame)
    
    def load_config(self) -> None:
        """加载配置"""
        # 确保配置中包含我们的自定义设置
        super().load_config()
        
        # 添加额外的配置
        self.config.lifespan = "on"
        
        # 如果是Windows，使用兼容的配置
        if os.name == 'nt':
            self.config.loop = "asyncio"
            self.config.http = "h11"
    
    def get_pid(self) -> int:
        """
        获取Worker PID
        
        Returns:
            int: 进程ID
        """
        return os.getpid()
    
    def get_worker_id(self) -> int:
        """
        获取Worker ID
        
        Returns:
            int: Worker ID
        """
        return self._worker_id
