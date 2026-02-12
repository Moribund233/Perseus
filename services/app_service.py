"""
应用管理服务层

提供应用级别的管理功能：
- 配置管理（读取、修改、验证）
- 应用控制（关机、重启）
- 系统状态监控

这些功能仅在调试模式或管理员权限下可用
"""
import os
import sys
import signal
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from config import get_config
from utils.config_utils import ConfigManager, generate_default_config, get_config_manager
from exception import ValidationException, AuthorizationException, AppServiceException, ConfigValidationException


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

    def update_config(self, config_data: Dict[str, Any], is_debug: bool = False, is_admin: bool = False) -> Tuple[bool, List[str]]:
        """
        更新应用配置

        Args:
            config_data: 新的配置数据
            is_debug: 是否调试模式
            is_admin: 是否管理员

        Returns:
            Tuple[bool, List[str]]: (是否成功, 错误信息列表)

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

        # 合并配置（保留未修改的部分）
        current_config = config_manager.load_config()
        merged_config = self._merge_config(current_config, config_data)

        # 保存配置
        success = config_manager.save_config(merged_config)
        if not success:
            return False, ["保存配置失败"]

        return True, []

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

    def _validate_config_data(self, config_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证配置数据的内部方法

        Args:
            config_data: 配置数据

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []

        # 验证服务器配置
        server = config_data.get("server", {})

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

        # 验证存储配置
        storage = config_data.get("storage", {})
        if "repo_root" in storage:
            repo_root = storage["repo_root"]
            if not isinstance(repo_root, str) or not repo_root.strip():
                errors.append("仓库根目录路径不能为空")

        # 验证安全配置
        security = config_data.get("security", {})
        if "secret_key" in security:
            secret_key = security["secret_key"]
            if not isinstance(secret_key, str) or len(secret_key) < 16:
                errors.append("JWT Secret Key 长度不能少于16个字符")

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

    def shutdown(self, is_debug: bool = False, is_admin: bool = False) -> bool:
        """
        关闭应用

        Args:
            is_debug: 是否调试模式
            is_admin: 是否管理员

        Returns:
            bool: 是否成功触发关闭

        Raises:
            AuthorizationException: 权限不足
        """
        self._check_permission(is_debug, is_admin)

        # 使用信号触发优雅关闭
        def _shutdown():
            """延迟关闭，让响应先返回"""
            import time
            time.sleep(0.5)
            os.kill(os.getpid(), signal.SIGTERM)

        # 在后台线程执行关闭
        import threading
        shutdown_thread = threading.Thread(target=_shutdown)
        shutdown_thread.daemon = True
        shutdown_thread.start()

        return True

    def restart(self, is_debug: bool = False, is_admin: bool = False) -> bool:
        """
        重启应用

        使用 FastAPI 的 reload 机制或进程重启

        Args:
            is_debug: 是否调试模式
            is_admin: 是否管理员

        Returns:
            bool: 是否成功触发重启

        Raises:
            AuthorizationException: 权限不足
        """
        self._check_permission(is_debug, is_admin)

        # 获取当前配置
        config = get_config()

        # 检查是否使用 Uvicorn（支持 reload）
        if not config.app.debug:
            raise ValidationException(
                detail="重启功能仅在调试模式下可用（使用 Uvicorn 时）"
            )

        # 使用信号触发 reload（Uvicorn 会捕获 SIGUSR1 或重新加载）
        def _restart():
            """延迟重启，让响应先返回"""
            import time
            time.sleep(0.5)
            # 发送 SIGHUP 信号给父进程（如果是 Uvicorn 启动的）
            # 或者直接使用 sys.executable 重新启动
            python = sys.executable
            os.execl(python, python, *sys.argv)

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
