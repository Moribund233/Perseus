"""
请求统计中间件

统计 HTTP 请求的数量、响应时间、成功率等指标
"""
import time
import threading
from typing import Dict, Any, Optional
from collections import deque
from datetime import datetime, timedelta

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestStats:
    """请求统计类（线程安全）"""
    
    def __init__(self, window_minutes: int = 5):
        self.window_minutes = window_minutes
        self._lock = threading.Lock()
        self._total = 0
        self._success = 0
        self._failed = 0
        self._response_times = deque(maxlen=10000)  # 保留最近10000个响应时间
        self._requests_per_minute = deque(maxlen=window_minutes)  # 每分钟请求数
        self._last_minute = datetime.now()
        self._current_minute_count = 0
    
    def record_request(self, response_time_ms: float, success: bool):
        """记录一个请求"""
        with self._lock:
            self._total += 1
            if success:
                self._success += 1
            else:
                self._failed += 1
            
            self._response_times.append(response_time_ms)
            
            # 更新每分钟请求数
            now = datetime.now()
            current_minute = now.replace(second=0, microsecond=0)
            
            if current_minute > self._last_minute:
                # 新分钟，保存上一分钟的数据
                self._requests_per_minute.append({
                    "minute": self._last_minute.isoformat(),
                    "count": self._current_minute_count
                })
                self._current_minute_count = 0
                self._last_minute = current_minute
            
            self._current_minute_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            avg_response_time = 0.0
            if self._response_times:
                avg_response_time = sum(self._response_times) / len(self._response_times)
            
            # 计算每分钟请求数
            rpm = 0
            if self._requests_per_minute:
                rpm = sum(r["count"] for r in self._requests_per_minute) / len(self._requests_per_minute)
            elif self._current_minute_count > 0:
                rpm = self._current_minute_count
            
            return {
                "total": self._total,
                "success": self._success,
                "failed": self._failed,
                "avg_response_time_ms": round(avg_response_time, 2),
                "requests_per_minute": round(rpm, 2)
            }
    
    def reset(self):
        """重置统计"""
        with self._lock:
            self._total = 0
            self._success = 0
            self._failed = 0
            self._response_times.clear()
            self._requests_per_minute.clear()
            self._current_minute_count = 0


# 全局统计实例
_request_stats: Optional[RequestStats] = None


def get_request_stats() -> RequestStats:
    """获取全局请求统计实例"""
    global _request_stats
    if _request_stats is None:
        _request_stats = RequestStats()
    return _request_stats


class RequestStatsMiddleware(BaseHTTPMiddleware):
    """
    请求统计中间件
    
    统计所有 HTTP 请求的性能指标
    """
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
        self.stats = get_request_stats()
    
    def _should_record(self, path: str) -> bool:
        """检查是否应该记录该路径"""
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        return True
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        if not self._should_record(request.url.path):
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # 计算响应时间（毫秒）
            response_time_ms = (time.time() - start_time) * 1000
            
            # 记录请求（2xx 和 3xx 视为成功）
            success = 200 <= response.status_code < 400
            self.stats.record_request(response_time_ms, success)
            
            return response
        except Exception as e:
            # 记录失败的请求
            response_time_ms = (time.time() - start_time) * 1000
            self.stats.record_request(response_time_ms, False)
            raise
