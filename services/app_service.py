"""
应用管理服务层

提供应用级别的管理功能：
- 配置管理（读取、修改、验证）
- 应用控制（关机、重启）
- 系统状态监控
- 日志管理

这些功能仅在调试模式或管理员权限下可用
"""
import os
import sys
import signal
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from config import get_config
from utils.config_utils import ConfigManager, generate_default_config, get_config_manager
from exception import ValidationException, AuthorizationException, AppServiceException, ConfigValidationException

logger = logging.getLogger(__name__)

# 全局关闭标志
_shutdown_requested = False


def _set_shutdown_flag():
    """设置全局关闭标志，通知服务器停止接收新请求"""
    global _shutdown_requested
    _shutdown_requested = True
    logger.info("Shutdown flag set, server will stop accepting new requests")


def _terminate_process():
    """终止当前进程（跨平台兼容）"""
    pid = os.getpid()
    logger.info(f"Terminating process {pid}")

    if os.name == 'nt':  # Windows
        # Windows 使用 SIGTERM 或 taskkill
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            # 如果 SIGTERM 失败，使用 sys.exit
            sys.exit(0)
    else:  # Unix/Linux/Mac
        os.kill(pid, signal.SIGTERM)


def _get_restart_command() -> List[str]:
    """
    获取重启命令

    Returns:
        List[str]: 命令列表，可直接用于 subprocess
    """
    import psutil

    # 获取当前进程信息
    current_process = psutil.Process()

    # 尝试获取原始命令行
    try:
        cmdline = current_process.cmdline()
        if cmdline and len(cmdline) > 1:
            # 使用原始命令行
            return cmdline
    except Exception:
        pass

    # 回退：构建基本命令
    python = sys.executable
    script = sys.argv[0] if sys.argv else "app.py"

    return [python, script]


class AppService:
    """
    应用服务类

    提供应用级别的管理功能
    """

    def __init__(self):
        """初始化应用服务"""
        self._config_manager: Optional[ConfigManager] = None
        self._start_time = datetime.now()

    def _get_config_manager(self) -> ConfigManager:
        """
        获取配置管理器实例

        Returns:
            ConfigManager: 配置管理器实例
        """
        if self._config_manager is None:
            self._config_manager = get_config_manager()
        return self._config_manager

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
                detail="该操作仅在调试模式或管理员权限下可用"
            )

    def get_config(self, section: Optional[str] = None) -> Dict[str, Any]:
        """
        获取应用配置

        Args:
            section: 配置节名称，为None则返回全部配置

        Returns:
            Dict[str, Any]: 配置数据
        """
        config_manager = self._get_config_manager()
        config = config_manager.load_config()

        if section:
            return config.get(section, {})
        return config

    def _check_restart_required(self, config_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        检查配置修改是否需要重启才能生效

        Args:
            config_data: 新的配置数据

        Returns:
            Tuple[bool, List[str]]: (是否需要重启, 需要重启的配置项列表)
        """
        restart_items = []

        for section, fields in config_data.items():
            if section not in self.RESTART_REQUIRED_CONFIGS:
                continue
            if not isinstance(fields, dict):
                continue

            for field in fields.keys():
                if field in self.RESTART_REQUIRED_CONFIGS[section]:
                    restart_items.append(f"{section}.{field}")

        return len(restart_items) > 0, restart_items

    def update_config(self, config_data: Dict[str, Any], is_debug: bool = False, is_admin: bool = False) -> Tuple[bool, List[str], List[str]]:
        """
        更新应用配置

        Args:
            config_data: 新的配置数据
            is_debug: 是否调试模式
            is_admin: 是否管理员

        Returns:
            Tuple[bool, List[str], List[str]]: (是否成功, 错误信息列表, 重启提示列表)

        Raises:
            AuthorizationException: 权限不足
            ValidationException: 配置验证失败
        """
        self._check_permission(is_debug, is_admin)

        config_manager = self._get_config_manager()

        # 验证配置
        is_valid, errors = self._validate_config_data(config_data)
        if not is_valid:
            raise ValidationException(detail=f"配置验证失败: {'; '.join(errors)}")

        # 检查是否需要重启
        restart_required, restart_items = self._check_restart_required(config_data)

        # 合并配置（保留未修改的部分）
        current_config = config_manager.load_config()
        merged_config = self._merge_config(current_config, config_data)

        # 保存配置
        success = config_manager.save_config(merged_config)
        if not success:
            return False, ["保存配置失败"], []

        # 生成重启提示
        restart_hints = []
        if restart_required:
            restart_hints.append(f"以下配置项修改后需要重启服务才能生效: {', '.join(restart_items)}")

        return True, [], restart_hints

    def reset_config(self, is_debug: bool = False, is_admin: bool = False) -> Tuple[bool, List[str]]:
        """
        重置配置为默认值

        Args:
            is_debug: 是否调试模式
            is_admin: 是否管理员

        Returns:
            Tuple[bool, List[str]]: (是否成功, 错误信息列表)

        Raises:
            AuthorizationException: 权限不足
        """
        self._check_permission(is_debug, is_admin)

        config_manager = self._get_config_manager()
        default_config = generate_default_config()

        success = config_manager.save_config(default_config)
        if not success:
            return False, ["重置配置失败"]

        return True, []

    def validate_config(self, config_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[str]]:
        """
        验证配置数据

        Args:
            config_data: 要验证的配置数据，为None则验证当前配置

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        if config_data is None:
            config_manager = self._get_config_manager()
            config_data = config_manager.load_config()

        return self._validate_config_data(config_data)

    # 允许修改的配置节
    ALLOWED_CONFIG_SECTIONS = {"server", "proxy", "rate_limit"}
    # 禁止修改的配置节（可能导致系统不稳定或安全问题）
    PROTECTED_CONFIG_SECTIONS = {"storage", "security", "app", "logging", "system"}
    # 需要重启才能生效的配置项
    RESTART_REQUIRED_CONFIGS = {
        "server": {"host", "port", "workers"},  # 服务器核心参数需要重启
        "proxy": {"proxy"},  # 代理设置影响中间件加载
    }

    def _validate_config_data(self, config_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证配置数据的内部方法

        只允许修改 server、proxy、rate_limit 配置节
        禁止修改 storage、security、app、logging、system 配置节

        Args:
            config_data: 配置数据

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []

        # 检查是否有禁止修改的配置节
        for section in config_data.keys():
            if section in self.PROTECTED_CONFIG_SECTIONS:
                errors.append(f"配置节 '{section}' 不允许修改")
                continue
            if section not in self.ALLOWED_CONFIG_SECTIONS:
                errors.append(f"未知的配置节: {section}")

        # 如果没有允许的配置节，直接返回错误
        if not any(section in self.ALLOWED_CONFIG_SECTIONS for section in config_data.keys()):
            errors.append("没有可修改的有效配置节")

        # 验证服务器配置
        if "server" in config_data:
            server = config_data["server"]
            if not isinstance(server, dict):
                errors.append("server 配置必须是对象")
            else:
                # 检查是否有不允许修改的字段
                if "reload" in server:
                    errors.append("server.reload 不允许修改（运行时热重载设置）")

                if "host" in server:
                    host = server["host"]
                    if not isinstance(host, str) or not host:
                        errors.append("服务器地址不能为空")

                if "port" in server:
                    try:
                        port = int(server["port"])
                        if port < 1 or port > 65535:
                            errors.append("服务器端口必须是1-65535之间的整数")
                    except (ValueError, TypeError):
                        errors.append("服务器端口必须是1-65535之间的整数")

                if "workers" in server:
                    try:
                        workers = int(server["workers"])
                        if workers < 1:
                            errors.append("服务器工作进程数必须是正整数")
                    except (ValueError, TypeError):
                        errors.append("服务器工作进程数必须是正整数")

                if "log_level" in server:
                    valid_levels = {"debug", "info", "warning", "error", "critical"}
                    if server["log_level"] not in valid_levels:
                        errors.append(f"日志级别必须是以下之一: {', '.join(valid_levels)}")

        # 验证代理配置
        if "proxy" in config_data:
            proxy = config_data["proxy"]
            if not isinstance(proxy, dict):
                errors.append("proxy 配置必须是对象")
            else:
                if "proxy" in proxy:
                    if not isinstance(proxy["proxy"], bool):
                        errors.append("proxy.proxy 必须是布尔值")

        # 验证速率限制配置
        if "rate_limit" in config_data:
            rate_limit = config_data["rate_limit"]
            if not isinstance(rate_limit, dict):
                errors.append("rate_limit 配置必须是对象")
            else:
                valid_limit_types = {"default_limits", "strict", "standard", "generous", "git_operations", "download"}
                for key in rate_limit.keys():
                    if key not in valid_limit_types:
                        errors.append(f"rate_limit 不支持 '{key}'，支持的类型: {', '.join(valid_limit_types)}")
                    elif not isinstance(rate_limit[key], list):
                        errors.append(f"rate_limit.{key} 必须是字符串数组")

        return len(errors) == 0, errors

    def _merge_config(self, current: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归合并配置

        Args:
            current: 当前配置
            updates: 更新的配置

        Returns:
            Dict[str, Any]: 合并后的配置
        """
        result = current.copy()

        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value

        return result

    def shutdown(self, is_debug: bool = False, is_admin: bool = False, force: bool = False) -> bool:
        """
        关闭应用

        实现方式：
        1. 首先尝试优雅关闭（通过全局标志通知服务器停止接收新请求）
        2. 如果 force=True 或优雅关闭超时，则强制终止进程

        Args:
            is_debug: 是否调试模式
            is_admin: 是否管理员
            force: 是否强制关闭（跳过优雅关闭）

        Returns:
            bool: 是否成功触发关闭

        Raises:
            AuthorizationException: 权限不足
        """
        self._check_permission(is_debug, is_admin)

        def _shutdown():
            """执行关闭流程"""
            import time
            time.sleep(0.5)  # 让响应先返回

            if not force:
                # 尝试优雅关闭：设置全局标志通知服务器
                _set_shutdown_flag()
                # 等待现有请求处理完成（最多5秒）
                time.sleep(2)

            # 强制终止进程
            _terminate_process()

        # 在后台线程执行关闭
        import threading
        shutdown_thread = threading.Thread(target=_shutdown)
        shutdown_thread.daemon = True
        shutdown_thread.start()

        return True

    def restart(self, is_debug: bool = False, is_admin: bool = False) -> bool:
        """
        重启应用

        实现方式：
        1. 优雅关闭当前进程
        2. 使用子进程启动新的应用实例
        3. 新进程启动成功后，旧进程退出

        Args:
            is_debug: 是否调试模式
            is_admin: 是否管理员

        Returns:
            bool: 是否成功触发重启

        Raises:
            AuthorizationException: 权限不足
        """
        self._check_permission(is_debug, is_admin)

        def _restart():
            """执行重启流程"""
            import time
            import subprocess

            time.sleep(0.5)  # 让响应先返回

            # 获取当前启动命令
            cmd = _get_restart_command()

            # 启动新进程
            try:
                if os.name == 'nt':  # Windows
                    subprocess.Popen(
                        cmd,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:  # Unix/Linux/Mac
                    subprocess.Popen(
                        cmd,
                        start_new_session=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                # 给新进程一点时间启动
                time.sleep(1)

                # 优雅关闭当前进程
                _set_shutdown_flag()
                time.sleep(1)
                _terminate_process()

            except Exception as e:
                logger.error(f"重启失败: {e}")
                raise AppServiceException(f"重启失败: {e}")

        # 在后台线程执行重启
        import threading
        restart_thread = threading.Thread(target=_restart)
        restart_thread.daemon = True
        restart_thread.start()

        return True

    def get_status(self) -> Dict[str, Any]:
        """
        获取应用状态

        Returns:
            Dict[str, Any]: 应用状态信息
        """
        config = get_config()

        # 计算运行时间
        uptime = datetime.now() - self._start_time
        uptime_seconds = int(uptime.total_seconds())

        # 获取系统信息
        import platform
        system_info = {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
        }

        return {
            "status": "running",
            "debug_mode": config.app.debug,
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": self._format_uptime(uptime_seconds),
            "system": system_info,
            "version": "1.0.0",  # TODO: 从版本文件读取
        }

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

    # ==================== 日志服务方法 ====================

    def get_log_info(self) -> Dict[str, Any]:
        """
        获取日志系统信息

        Returns:
            Dict[str, Any]: 日志信息，包括日志目录、日志文件列表等
        """
        from utils.logging_utils import LogManager

        log_dir = Path(LogManager.DEFAULT_LOG_DIR)
        today_dir = log_dir / datetime.now().strftime(LogManager.DATE_FORMAT)

        # 获取所有日志日期目录
        available_dates = []
        if log_dir.exists():
            for item in log_dir.iterdir():
                if item.is_dir():
                    try:
                        # 验证是否为日期格式
                        datetime.strptime(item.name, "%Y-%m-%d")
                        available_dates.append(item.name)
                    except ValueError:
                        pass

        available_dates.sort(reverse=True)

        # 获取今天的日志文件
        today_files = []
        if today_dir.exists():
            for log_file in today_dir.iterdir():
                if log_file.suffix == ".log":
                    stat = log_file.stat()
                    today_files.append({
                        "name": log_file.name,
                        "size": stat.st_size,
                        "size_formatted": self._format_file_size(stat.st_size),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })

        return {
            "log_dir": str(log_dir),
            "today_dir": str(today_dir),
            "today_files": today_files,
            "available_dates": available_dates[:30],  # 最近30天
        }

    def get_log_content(
        self,
        date: Optional[str] = None,
        log_name: str = "app",
        lines: int = 100,
        level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取日志内容

        Args:
            date: 日期字符串 (YYYY-MM-DD)，None 表示今天
            log_name: 日志文件名（不含扩展名），如 'app', 'error'
            lines: 返回的行数（从末尾开始）
            level: 过滤日志级别 (debug/info/warning/error/critical)

        Returns:
            Dict[str, Any]: 日志内容和元数据
        """
        from utils.logging_utils import LogManager

        # 确定日志目录
        if date is None:
            date = datetime.now().strftime(LogManager.DATE_FORMAT)

        # 验证日期格式
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValidationException(detail="日期格式无效，应为 YYYY-MM-DD")

        log_dir = Path(LogManager.DEFAULT_LOG_DIR) / date
        log_file = log_dir / f"{log_name}.log"

        if not log_file.exists():
            return {
                "date": date,
                "log_name": log_name,
                "lines": 0,
                "content": "",
                "exists": False,
            }

        # 读取日志内容
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
        except Exception as e:
            raise AppServiceException(f"读取日志文件失败: {e}")

        # 过滤日志级别
        if level:
            level_upper = level.upper()
            all_lines = [line for line in all_lines if level_upper in line]

        # 获取最后 N 行
        total_lines = len(all_lines)
        start_line = max(0, total_lines - lines)
        selected_lines = all_lines[start_line:]

        return {
            "date": date,
            "log_name": log_name,
            "lines": len(selected_lines),
            "total_lines": total_lines,
            "content": "".join(selected_lines),
            "exists": True,
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

        Raises:
            AuthorizationException: 权限不足
        """
        self._check_permission(is_debug, is_admin)

        from utils.logging_utils import cleanup_old_logs

        if keep_days < 1:
            raise ValidationException(detail="保留天数必须大于等于1")

        deleted_count = cleanup_old_logs(keep_days=keep_days)

        return {
            "success": True,
            "deleted_count": deleted_count,
            "keep_days": keep_days,
        }

    def _format_file_size(self, size_bytes: int) -> str:
        """
        格式化文件大小

        Args:
            size_bytes: 字节数

        Returns:
            str: 格式化后的文件大小
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# 全局应用服务实例
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
