"""
日志管理模块

提供统一的日志处理功能，包括日志记录、回调管理和日志检索。
"""
import time
import threading
from typing import Callable, List, Optional


class LogManager:
    """
    日志管理器类
    
    负责统一处理日志记录、管理日志回调和提供日志检索功能。
    支持多线程安全的日志操作。
    """
    
    def __init__(self, max_lines: int = 1000):
        """
        初始化日志管理器
        
        Args:
            max_lines: 最大日志行数，超过后自动清理旧日志
        """
        self._log_lines: List[str] = []
        self._max_lines = max_lines
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[str], None]] = []
    
    def add_log(self, message: str) -> None:
        """
        添加日志信息
        
        Args:
            message: 日志消息内容
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_line = f"[{timestamp}] {message}"
        
        with self._lock:
            # 添加新日志
            self._log_lines.append(log_line)
            # 保留最近指定数量的日志
            if len(self._log_lines) > self._max_lines:
                self._log_lines = self._log_lines[-self._max_lines:]
        
        # 通知所有回调函数
        for callback in self._callbacks:
            callback(log_line)
    
    def add_callback(self, callback: Callable[[str], None]) -> None:
        """
        添加日志回调函数
        
        Args:
            callback: 接受日志字符串的回调函数
        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[str], None]) -> None:
        """
        移除日志回调函数
        
        Args:
            callback: 要移除的回调函数
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def get_logs(self, lines: int = 100) -> List[str]:
        """
        获取日志行
        
        Args:
            lines: 获取的日志行数
            
        Returns:
            List[str]: 日志行列表
        """
        with self._lock:
            return self._log_lines[-lines:]
    
    def clear_logs(self) -> None:
        """
        清除所有日志
        """
        with self._lock:
            self._log_lines.clear()
    
    def get_log_count(self) -> int:
        """
        获取当前日志行数
        
        Returns:
            int: 日志行数
        """
        with self._lock:
            return len(self._log_lines)


# 创建全局日志管理器实例
_log_manager: Optional[LogManager] = None


def get_log_manager(max_lines: int = 1000) -> LogManager:
    """
    获取全局日志管理器实例
    
    Args:
        max_lines: 最大日志行数
        
    Returns:
        LogManager: 日志管理器实例
    """
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager(max_lines)
    return _log_manager
