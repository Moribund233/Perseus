"""
应用管理服务层

提供应用级别的管理功能：
- 应用控制（关机、重启）
- 系统状态监控
- 日志管理

这些功能仅在调试模式或管理员权限下可用
"""
import os
import sys
import signal
import logging
import subprocess
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from core.config import get_config
from core.exception import ValidationException, AuthorizationException, AppServiceException

logger = logging.getLogger(__name__)

_shutdown_requested = False


def _set_shutdown_flag():
    """设置全局关闭标志，通知服务器停止接收新请求"""
    global _shutdown_requested
    _shutdown_requested = True


def _terminate_process():
    """终止当前进程"""
    os.kill(os.getpid(), signal.SIGTERM)


def _build_restart_command(
    orig_argv: Optional[List[str]],
    argv: List[str],
    executable: str,
    frozen: bool,
) -> List[str]:
    """
    构建重启命令（纯函数，便于测试）。

    优先复现原始启动命令行（``sys.orig_argv``），这样无论以
    ``python app.py``、``uvicorn app:app`` 还是 console script 启动，
    都能用相同方式重新拉起。仅当无法取得原始命令行时才回退到
    「解释器 + argv[0]」。

    Args:
        orig_argv: 原始命令行（sys.orig_argv，可能为 None）
        argv: 当前 argv（sys.argv）
        executable: Python 解释器路径（sys.executable）
        frozen: 是否为 PyInstaller 冻结可执行文件

    Returns:
        List[str]: 可直接用于 subprocess 的命令列表
    """
    # PyInstaller 打包的可执行文件：直接重启自身
    if frozen:
        return [executable]

    if orig_argv:
        cmd = [str(a) for a in orig_argv]
        # 首项若为 python 解释器，替换为当前解释器绝对路径，避免 PATH 差异
        if cmd and os.path.basename(cmd[0]).lower().startswith("python"):
            cmd[0] = executable
        return cmd

    # 回退：Python 脚本模式
    script = argv[0] if argv else "app.py"
    return [executable, script]


def _get_restart_command() -> List[str]:
    """
    获取重启命令（读取当前进程的启动信息）。

    Returns:
        List[str]: 命令列表，可直接用于 subprocess
    """
    return _build_restart_command(
        getattr(sys, "orig_argv", None),
        list(sys.argv),
        sys.executable,
        getattr(sys, "frozen", False),
    )


def _spawn_restart(cmd: List[str], delay: float = 3.0) -> None:
    """
    延迟拉起新进程，等待旧进程释放监听端口后再启动。

    通过一个分离的 Python 助手进程实现跨平台延迟启动：助手进程
    sleep 后以独立会话执行重启命令，因此当前进程随后退出也不会
    影响新进程启动。

    Args:
        cmd: 重启命令
        delay: 延迟秒数
    """
    helper = (
        "import subprocess, sys, time;"
        "time.sleep(float(sys.argv[1]));"
        "subprocess.Popen(sys.argv[2:])"
    )
    kwargs: Dict[str, Any] = {}
    if os.name == "posix":
        kwargs["start_new_session"] = True
    subprocess.Popen(
        [sys.executable, "-c", helper, str(delay)] + list(cmd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **kwargs,
    )


class AppService:
    """
    应用服务类

    提供应用级别的管理功能（配置管理已移至 ConfigService）
    """

    def __init__(self):
        """初始化应用服务"""
        self._start_time = datetime.now()

    def _check_permission(self, is_debug: bool, is_admin: bool) -> None:
        """
        检查操作权限

        Args:
            is_debug: 是否调试模式
            is_admin: 是否管理员

        Raises:
            AuthorizationException: 权限不足
        """
        if not is_debug and not is_admin:
            raise AuthorizationException(
                detail="该操作需要本地认证或调试模式"
            , error_code="app_local_auth_required")

    def shutdown(self, is_debug: bool = False, is_admin: bool = False, force: bool = False) -> bool:
        """
        关闭应用

        支持单进程(Uvicorn)和多进程(Gunicorn)模式：
        - 单进程模式：直接触发关闭流程
        - 多进程模式：通过IPC通知所有worker关闭

        Args:
            is_debug: 是否调试模式
            is_admin: 是否管理员
            force: 是否强制关闭

        Returns:
            bool: 是否成功触发关闭
        """
        self._check_permission(is_debug, is_admin)

        def _shutdown():
            """执行关闭流程"""
            import time
            time.sleep(0.5)

            try:
                from core.lifespan import trigger_graceful_shutdown
                
                # 使用新的生命周期管理接口触发关闭
                # 支持单进程和多进程模式
                success = trigger_graceful_shutdown(reason="api_request")
                
                if not success:
                    logger.error("触发关闭失败，将强制终止")
                    _terminate_process()
                    
            except Exception as e:
                logger.error(f"优雅关闭失败，将强制终止: {e}")
                _terminate_process()

        import threading
        shutdown_thread = threading.Thread(target=_shutdown)
        shutdown_thread.daemon = True
        shutdown_thread.start()

        return True

    def restart(self, is_debug: bool = False, is_admin: bool = False) -> bool:
        """
        重启应用

        Args:
            is_debug: 是否调试模式
            is_admin: 是否管理员

        Returns:
            bool: 是否成功触发重启
        """
        self._check_permission(is_debug, is_admin)

        def _restart():
            """执行重启流程"""
            import time
            import asyncio

            time.sleep(0.5)

            cmd = _get_restart_command()

            try:
                # 延迟拉起新进程，等待本进程释放端口
                _spawn_restart(cmd)

                time.sleep(1)

                try:
                    from core.lifespan import get_lifecycle_manager

                    manager = get_lifecycle_manager()

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(manager.shutdown())
                    loop.close()

                except Exception as e:
                    logger.error(f"优雅关闭失败: {e}")

                _terminate_process()

            except Exception as e:
                logger.error(f"重启失败: {e}")
                raise AppServiceException(f"重启失败: {e}", error_code="app_restart_failed")

        import threading
        restart_thread = threading.Thread(target=_restart)
        restart_thread.daemon = True
        restart_thread.start()

        return True

    def get_status(self, requests_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        获取应用状态

        请求统计信息由调用方传入，避免服务层直接依赖中间件。

        Args:
            requests_info: 可选的请求统计信息，由控制器层传入

        Returns:
            Dict[str, Any]: 应用状态信息
        """
        config = get_config()

        uptime = datetime.now() - self._start_time
        uptime_seconds = int(uptime.total_seconds())

        process_info = self._get_process_info()
        git_info = self._get_git_operations_info()

        return {
            "status": "running",
            "debug_mode": config.app.debug,
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": self._format_uptime(uptime_seconds),
            "version": "1.0.0",
            "server_time": datetime.now().isoformat(),
            "process": process_info,
            "requests": requests_info or self._get_default_requests_info(),
            "git_operations": git_info,
            "schema_state": self._get_schema_info(),
        }

    @staticmethod
    def _get_schema_info() -> Dict[str, Any]:
        """
        获取数据库 schema 版本信息（Alembic applied/head）。

        Returns:
            Dict[str, Any]: schema 信息；查询失败时返回空字典（不影响状态接口可用性）
        """
        try:
            from core.config import get_config
            from utils.db_migrate import get_applied_revision, get_head_revision

            db_url = get_config().database.url
            return {
                "applied": get_applied_revision(db_url),
                "head": get_head_revision(db_url),
            }
        except Exception:
            return {}

    def _get_process_info(self) -> Dict[str, Any]:
        """
        获取当前进程信息

        Returns:
            Dict[str, Any]: 进程信息
        """
        import psutil

        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            return {
                "pid": process.pid,
                "memory_mb": round(memory_info.rss / (1024 * 1024), 2),
                "cpu_percent": round(process.cpu_percent(interval=None) or 0.0, 2),
                "threads": process.num_threads(),
                "connections": len(process.connections()),
            }
        except Exception:
            return {}

    def _format_uptime(self, seconds: int) -> str:
        """
        格式化运行时间

        Args:
            seconds: 运行秒数

        Returns:
            str: 格式化后的时间字符串
        """
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days}天")
        if hours > 0:
            parts.append(f"{hours}小时")
        if minutes > 0:
            parts.append(f"{minutes}分钟")
        if secs > 0 or not parts:
            parts.append(f"{secs}秒")

        return "".join(parts)

    def _get_default_requests_info(self) -> Dict[str, Any]:
        """
        获取默认请求统计信息（当调用方未传入数据时使用）

        Returns:
            Dict[str, Any]: 空请求统计信息
        """
        return {
            "total": 0,
            "success": 0,
            "failed": 0,
            "avg_response_time_ms": 0,
            "requests_per_minute": 0,
        }

    def _get_git_operations_info(self) -> Dict[str, Any]:
        """
        获取Git操作状态信息

        Returns:
            Dict[str, Any]: Git操作状态
        """
        return {
            "active_clones": 0,
            "active_pushes": 0,
            "queue_size": 0,
        }

    def get_log_info(self) -> Dict[str, Any]:
        """
        获取日志系统信息

        Returns:
            Dict[str, Any]: 日志信息
        """
        from utils.logging import get_log_info as get_simple_log_info, LogManager

        info = get_simple_log_info(log_dir=LogManager.DEFAULT_LOG_DIR)

        return {
            "log_dir": info["log_dir"],
            "today_dir": info["today_dir"],
            "today_files": info["files"],
            "available_dates": info["available_dates"],
        }

    @staticmethod
    def _level_matches(line: str, level_upper: Optional[str]) -> bool:
        """
        按格式化器边界匹配日志级别。

        格式为 ``asctime - name - LEVEL - message``，故用 `` - LEVEL - `` 精确匹配，
        避免子串误伤（如 ``INFO`` 命中 ``INFORMATION`` 或含该词的 logger 名）。
        """
        if not level_upper:
            return True
        return f" - {level_upper} - " in line

    def get_log_content(
        self,
        date: Optional[str] = None,
        log_name: str = "perseus",
        lines: int = 100,
        level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取日志内容（将磁盘分片拼接为逻辑流）

        将 ``X.log`` 与其滚动备份 ``X.log.1..N`` 按时间顺序拼接，返回逻辑流末尾
        ``lines`` 行；``segment_starts`` 给出各分片在返回窗口内的起始偏移，
        供前端绘制分片分隔；``truncated`` 表示已达保留上限、更早分片可能被丢弃。

        Args:
            date: 日期字符串 (YYYY-MM-DD)
            log_name: 日志文件基名（不含 .log）
            lines: 返回的行数
            level: 过滤日志级别

        Returns:
            Dict[str, Any]: 日志内容和元数据
        """
        from utils.logging import (
            LogManager,
            resolve_log_segments,
            get_log_retention,
        )

        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValidationException(detail="日期格式无效，应为 YYYY-MM-DD", error_code="app_invalid_date_format")

        segments = resolve_log_segments(LogManager.DEFAULT_LOG_DIR, date, log_name)
        if not segments and log_name != "perseus":
            segments = resolve_log_segments(LogManager.DEFAULT_LOG_DIR, date, "perseus")

        if not segments:
            return {
                "date": date,
                "log_name": log_name,
                "lines": 0,
                "total_lines": 0,
                "content": "",
                "exists": False,
                "window_parts": [],
                "segment_starts": [],
                "truncated": False,
            }

        level_upper = level.upper() if level else None

        # 第一遍：流式统计过滤后总行数（精确 total，不驻留全部内容）
        total_lines = 0
        for _, seg_path in segments:
            try:
                with open(seg_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if self._level_matches(line, level_upper):
                            total_lines += 1
            except OSError as e:
                raise AppServiceException(f"读取日志文件失败: {e}", error_code="app_log_read_failed")

        # 第二遍：从最新分片向前取尾部，凑够 lines 行即停
        chunks: List[Tuple[str, List[str]]] = []
        remaining = lines
        for _, seg_path in segments:  # 新 → 旧
            if remaining <= 0:
                break
            seg_lines: List[str] = []
            try:
                with open(seg_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if self._level_matches(line, level_upper):
                            seg_lines.append(line)
            except OSError as e:
                raise AppServiceException(f"读取日志文件失败: {e}", error_code="app_log_read_failed")
            if len(seg_lines) > remaining:
                seg_lines = seg_lines[-remaining:]
            chunks.append((seg_path.name, seg_lines))
            remaining -= len(seg_lines)

        chunks.reverse()  # 旧 → 新，保证拼接顺序正确
        window: List[str] = []
        segment_starts: List[Dict[str, Any]] = []
        for name, seg_lines in chunks:
            if not seg_lines:
                continue
            segment_starts.append({"name": name, "offset": len(window)})
            window.extend(seg_lines)

        _, backup_count = get_log_retention()
        max_idx = segments[-1][0]
        truncated = backup_count > 0 and max_idx >= backup_count

        return {
            "date": date,
            "log_name": log_name,
            "lines": len(window),
            "total_lines": total_lines,
            "content": "".join(window),
            "exists": True,
            "window_parts": [s["name"] for s in segment_starts],
            "segment_starts": segment_starts,
            "truncated": truncated,
        }

    def cleanup_old_logs(self, keep_days: int = 30, is_debug: bool = False, is_admin: bool = False) -> Dict[str, Any]:
        """
        清理旧日志文件

        Args:
            keep_days: 保留天数
            is_debug: 是否调试模式
            is_admin: 是否管理员

        Returns:
            Dict[str, Any]: 清理结果
        """
        self._check_permission(is_debug, is_admin)

        from utils.logging import cleanup_old_logs, LogManager

        if keep_days < 1:
            raise ValidationException(detail="保留天数必须大于等于1", error_code="app_invalid_retention_days")

        deleted_count = cleanup_old_logs(
            keep_days=keep_days,
            log_dir=LogManager.DEFAULT_LOG_DIR
        )

        return {
            "success": True,
            "deleted_count": deleted_count,
            "keep_days": keep_days,
        }


_app_service: Optional[AppService] = None


def get_app_service() -> AppService:
    """
    获取全局应用服务实例

    Returns:
        AppService: 应用服务实例
    """
    global _app_service
    if _app_service is None:
        _app_service = AppService()
    return _app_service
