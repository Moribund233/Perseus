"""
进程间通信管理模块 (IPC Manager)

提供多进程环境下的进程间通信机制，支持：
- 基于文件的进程状态共享
- 跨进程的信号通知
- 优雅关闭协调

主要用于Gunicorn多进程模式下管理所有worker的生命周期
"""
import os
import json
import time
import signal
import logging
import tempfile
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timedelta
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class IPCManager:
    """
    进程间通信管理器
    
    使用文件锁和共享状态文件实现跨进程通信，
    支持Gunicorn多进程环境下的生命周期管理。
    """
    
    SHUTDOWN_FILE = "langit_shutdown.flag"
    STATUS_FILE = "langit_status.json"
    LOCK_FILE = "langit_ipc.lock"
    
    def __init__(self, ipc_dir: Optional[str] = None):
        """
        初始化IPC管理器
        
        Args:
            ipc_dir: IPC文件存放目录，默认为系统临时目录
        """
        if ipc_dir:
            self.ipc_dir = Path(ipc_dir)
        else:
            self.ipc_dir = Path(tempfile.gettempdir()) / "langit_ipc"
        
        self.ipc_dir.mkdir(parents=True, exist_ok=True)
        
        self._shutdown_file = self.ipc_dir / self.SHUTDOWN_FILE
        self._status_file = self.ipc_dir / self.STATUS_FILE
        self._lock_file = self.ipc_dir / self.LOCK_FILE
        
        self._is_worker = False
        self._worker_id: Optional[int] = None
        self._master_pid: Optional[int] = None
        self._shutdown_callbacks: List[Callable[[], None]] = []
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()
    
    def initialize_master(self, master_pid: int) -> None:
        """
        初始化Master进程
        
        Args:
            master_pid: Master进程PID
        """
        self._master_pid = master_pid
        self._is_worker = False
        self._cleanup_files()
        self._write_status({
            "master_pid": master_pid,
            "start_time": datetime.now().isoformat(),
            "status": "running",
            "workers": []
        })
        logger.info(f"IPC管理器已初始化，Master PID: {master_pid}")
    
    def initialize_worker(self, worker_id: int, master_pid: int) -> None:
        """
        初始化Worker进程
        
        Args:
            worker_id: Worker ID
            master_pid: Master进程PID
        """
        self._worker_id = worker_id
        self._master_pid = master_pid
        self._is_worker = True
        
        # 注册worker到状态文件
        self._register_worker(worker_id)
        
        # 启动监控线程
        self._start_monitor()
        
        logger.info(f"Worker {worker_id} IPC已初始化，Master PID: {master_pid}")
    
    def _cleanup_files(self) -> None:
        """清理旧的IPC文件"""
        for file in [self._shutdown_file, self._status_file, self._lock_file]:
            try:
                if file.exists():
                    file.unlink()
            except Exception as e:
                logger.warning(f"清理IPC文件失败 {file}: {e}")
    
    @contextmanager
    def _file_lock(self, timeout: float = 5.0):
        """
        文件锁上下文管理器
        
        Args:
            timeout: 获取锁的超时时间（秒）
        """
        lock_path = self._lock_file
        start_time = time.time()
        
        while True:
            try:
                # 尝试创建锁文件（原子操作）
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                break
            except FileExistsError:
                if time.time() - start_time > timeout:
                    # 超时，强制删除旧锁
                    try:
                        lock_path.unlink()
                    except:
                        pass
                    continue
                time.sleep(0.01)
        
        try:
            yield
        finally:
            try:
                if lock_path.exists():
                    lock_path.unlink()
            except:
                pass
    
    def _read_status(self) -> Dict[str, Any]:
        """读取状态文件"""
        try:
            if self._status_file.exists():
                with open(self._status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"读取状态文件失败: {e}")
        return {}
    
    def _write_status(self, status: Dict[str, Any]) -> None:
        """写入状态文件"""
        with self._file_lock():
            try:
                with open(self._status_file, 'w', encoding='utf-8') as f:
                    json.dump(status, f, ensure_ascii=False)
            except Exception as e:
                logger.error(f"写入状态文件失败: {e}")
    
    def _register_worker(self, worker_id: int) -> None:
        """注册Worker到状态文件"""
        with self._file_lock():
            status = self._read_status()
            workers = status.get("workers", [])
            worker_info = {
                "worker_id": worker_id,
                "pid": os.getpid(),
                "start_time": datetime.now().isoformat(),
                "status": "running"
            }
            
            # 更新或添加worker信息
            existing = [w for w in workers if w.get("worker_id") == worker_id]
            if existing:
                existing[0].update(worker_info)
            else:
                workers.append(worker_info)
            
            status["workers"] = workers
            self._write_status(status)
    
    def _start_monitor(self) -> None:
        """启动监控线程（Worker中运行）"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self._stop_monitor.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def _monitor_loop(self) -> None:
        """监控循环（在Worker中运行）"""
        while not self._stop_monitor.is_set():
            try:
                # 检查关闭标志
                if self._shutdown_file.exists():
                    logger.info(f"Worker {self._worker_id} 检测到关闭信号")
                    self._handle_shutdown_signal()
                    return
                
                # 检查master是否存活
                if self._master_pid and not self._is_process_alive(self._master_pid):
                    logger.warning(f"Worker {self._worker_id} 检测到Master进程已退出")
                    self._handle_shutdown_signal()
                    return
                    
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
            
            # 每秒检查一次
            self._stop_monitor.wait(1.0)
    
    def _is_process_alive(self, pid: int) -> bool:
        """检查进程是否存活"""
        try:
            if os.name == 'nt':
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(1, False, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
                return False
            else:
                os.kill(pid, 0)
                return True
        except (OSError, ProcessLookupError):
            return False
    
    def _handle_shutdown_signal(self) -> None:
        """处理关闭信号"""
        logger.info(f"Worker {self._worker_id} 开始执行关闭流程")
        
        # 更新worker状态
        self._update_worker_status("shutting_down")
        
        # 执行注册的回调
        for callback in self._shutdown_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"关闭回调执行失败: {e}")
        
        # 退出进程
        self._exit_worker()
    
    def _update_worker_status(self, status: str) -> None:
        """更新Worker状态"""
        if self._worker_id is None:
            return
        
        with self._file_lock():
            state = self._read_status()
            workers = state.get("workers", [])
            for worker in workers:
                if worker.get("worker_id") == self._worker_id:
                    worker["status"] = status
                    worker["update_time"] = datetime.now().isoformat()
                    break
            state["workers"] = workers
            self._write_status(state)
    
    def _exit_worker(self) -> None:
        """退出Worker进程"""
        pid = os.getpid()
        logger.info(f"Worker {self._worker_id} (PID: {pid}) 正在退出")
        
        # 使用SIGTERM优雅退出
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.ExitProcess(0)
        else:
            os.kill(pid, signal.SIGTERM)
    
    def register_shutdown_callback(self, callback: Callable[[], None]) -> None:
        """
        注册关闭回调函数
        
        Args:
            callback: 关闭时执行的回调函数
        """
        self._shutdown_callbacks.append(callback)
    
    def request_shutdown(self, reason: str = "manual") -> bool:
        """
        请求关闭所有进程
        
        Args:
            reason: 关闭原因
            
        Returns:
            bool: 是否成功触发关闭
        """
        try:
            # 创建关闭标志文件
            with self._file_lock():
                shutdown_info = {
                    "requested_at": datetime.now().isoformat(),
                    "reason": reason,
                    "requested_by": os.getpid()
                }
                with open(self._shutdown_file, 'w', encoding='utf-8') as f:
                    json.dump(shutdown_info, f)
            
            # 更新状态
            status = self._read_status()
            status["status"] = "shutting_down"
            status["shutdown_reason"] = reason
            self._write_status(status)
            
            logger.info(f"已发送关闭请求，原因: {reason}")
            
            # 通知master进程（如果知道master PID）
            if self._master_pid:
                try:
                    if os.name == 'nt':
                        # Windows下使用SIGTERM
                        os.kill(self._master_pid, signal.SIGTERM)
                    else:
                        os.kill(self._master_pid, signal.SIGTERM)
                    logger.info(f"已通知Master进程 (PID: {self._master_pid})")
                except Exception as e:
                    logger.warning(f"通知Master进程失败: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"发送关闭请求失败: {e}")
            return False
    
    def is_shutdown_requested(self) -> bool:
        """
        检查是否已请求关闭
        
        Returns:
            bool: 是否已请求关闭
        """
        return self._shutdown_file.exists()
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取当前状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        return self._read_status()
    
    def stop_monitor(self) -> None:
        """停止监控线程"""
        self._stop_monitor.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
    
    def cleanup(self) -> None:
        """清理IPC资源"""
        self.stop_monitor()
        if not self._is_worker:
            # Master进程清理所有文件
            self._cleanup_files()


# 全局IPC管理器实例
_ipc_manager: Optional[IPCManager] = None


def get_ipc_manager(ipc_dir: Optional[str] = None) -> IPCManager:
    """
    获取IPC管理器实例（单例模式）
    
    Args:
        ipc_dir: IPC文件存放目录
        
    Returns:
        IPCManager: IPC管理器实例
    """
    global _ipc_manager
    if _ipc_manager is None:
        _ipc_manager = IPCManager(ipc_dir)
    return _ipc_manager


def reset_ipc_manager() -> None:
    """重置IPC管理器实例（用于测试）"""
    global _ipc_manager
    if _ipc_manager:
        _ipc_manager.cleanup()
    _ipc_manager = None
