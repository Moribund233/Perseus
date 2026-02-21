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
    ALLOWED_CONFIG_SECTIONS = {"server", "proxy", "rate_limit", "cors", "database"}
    # 禁止修改的配置节（可能导致系统不稳定或安全问题）
    PROTECTED_CONFIG_SECTIONS = {"storage", "security", "app", "logging", "system"}
    # 需要重启才能生效的配置项
    # 注意：几乎所有配置修改都需要重启，因为：
    # 1. 服务器核心参数（host, port, workers）在启动时绑定
    # 2. 中间件（CORS、Proxy）在启动时加载
    # 3. 数据库连接池在启动时创建
    # 4. 速率限制器在启动时初始化
    RESTART_REQUIRED_CONFIGS = {
        # 服务器核心参数 - 启动时绑定到网络接口
        "server": {"host", "port", "workers", "log_level"},
        # 代理设置 - 影响中间件加载和请求处理链
        "proxy": {"proxy"},
        # CORS 配置 - 中间件在启动时加载
        "cors": {"allow_origins", "allow_credentials", "allow_methods", "allow_headers", "max_age"},
        # 速率限制 - 限制器在启动时初始化
        "rate_limit": {"default_limits", "strict", "standard", "generous", "git_operations", "download"},
        # 数据库配置 - 连接池在启动时创建
        "database": {
            # 连接池配置
            "pool_size", "max_overflow", "pool_timeout", "pool_recycle", "echo",
            # SQLite 配置
            "sqlite_timeout", "sqlite_check_same_thread", "sqlite_isolation_level",
            # WAL 模式配置
            "enable_wal", "wal_synchronous", "wal_cache_size", "wal_temp_store",
            # 压力测试配置
            "stress_pool_size", "stress_max_overflow", "stress_pool_timeout", "stress_pool_recycle",
            "stress_sqlite_timeout", "stress_echo",
            # PostgreSQL 配置
            "pg_ssl_mode", "pg_connect_timeout", "pg_application_name",
            # MySQL 配置
            "mysql_charset", "mysql_pool_recycle", "mysql_connect_timeout",
            "mysql_read_timeout", "mysql_write_timeout",
        },
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

        # 验证 CORS 配置
        if "cors" in config_data:
            cors = config_data["cors"]
            if not isinstance(cors, dict):
                errors.append("cors 配置必须是对象")
            else:
                # 验证 allow_origins
                if "allow_origins" in cors:
                    if not isinstance(cors["allow_origins"], list):
                        errors.append("cors.allow_origins 必须是字符串数组")
                    else:
                        for origin in cors["allow_origins"]:
                            if not isinstance(origin, str):
                                errors.append("cors.allow_origins 中的所有项必须是字符串")
                                break
                            # 生产环境警告：不允许使用通配符
                            if origin == "*":
                                errors.append("生产环境不允许使用通配符 '*'，请配置具体的允许域名")

                # 验证 allow_credentials
                if "allow_credentials" in cors:
                    if not isinstance(cors["allow_credentials"], bool):
                        errors.append("cors.allow_credentials 必须是布尔值")

                # 验证 allow_methods
                if "allow_methods" in cors:
                    if not isinstance(cors["allow_methods"], list):
                        errors.append("cors.allow_methods 必须是字符串数组")
                    else:
                        valid_methods = {"GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"}
                        for method in cors["allow_methods"]:
                            if not isinstance(method, str):
                                errors.append("cors.allow_methods 中的所有项必须是字符串")
                                break
                            if method.upper() not in valid_methods:
                                errors.append(f"cors.allow_methods 包含无效的 HTTP 方法: {method}")

                # 验证 allow_headers
                if "allow_headers" in cors:
                    if not isinstance(cors["allow_headers"], list):
                        errors.append("cors.allow_headers 必须是字符串数组")
                    else:
                        for header in cors["allow_headers"]:
                            if not isinstance(header, str):
                                errors.append("cors.allow_headers 中的所有项必须是字符串")
                                break

                # 验证 max_age
                if "max_age" in cors:
                    try:
                        max_age = int(cors["max_age"])
                        if max_age < 0 or max_age > 86400:  # 最大 24 小时
                            errors.append("cors.max_age 必须在 0-86400 秒之间")
                    except (ValueError, TypeError):
                        errors.append("cors.max_age 必须是整数（秒）")

        # 验证数据库配置
        if "database" in config_data:
            database = config_data["database"]
            if not isinstance(database, dict):
                errors.append("database 配置必须是对象")
            else:
                # 验证连接池配置
                pool_int_fields = ["pool_size", "max_overflow", "pool_timeout", "pool_recycle"]
                for field in pool_int_fields:
                    if field in database:
                        try:
                            value = int(database[field])
                            if value < 1:
                                errors.append(f"database.{field} 必须是正整数")
                        except (ValueError, TypeError):
                            errors.append(f"database.{field} 必须是正整数")

                # 验证布尔字段
                bool_fields = ["echo", "sqlite_check_same_thread", "enable_wal", "stress_echo"]
                for field in bool_fields:
                    if field in database:
                        if not isinstance(database[field], bool):
                            errors.append(f"database.{field} 必须是布尔值")

                # 验证 SQLite 超时时间
                if "sqlite_timeout" in database:
                    try:
                        value = int(database["sqlite_timeout"])
                        if value < 1:
                            errors.append("database.sqlite_timeout 必须是正整数")
                    except (ValueError, TypeError):
                        errors.append("database.sqlite_timeout 必须是正整数")

                # 验证 WAL 同步模式
                if "wal_synchronous" in database:
                    valid_modes = ["OFF", "NORMAL", "FULL", "EXTRA"]
                    if database["wal_synchronous"] not in valid_modes:
                        errors.append(f"database.wal_synchronous 必须是以下之一: {', '.join(valid_modes)}")

                # 验证 WAL 缓存大小
                if "wal_cache_size" in database:
                    try:
                        value = int(database["wal_cache_size"])
                        if value < 0:
                            errors.append("database.wal_cache_size 必须是非负整数")
                    except (ValueError, TypeError):
                        errors.append("database.wal_cache_size 必须是非负整数")

                # 验证 WAL 临时存储
                if "wal_temp_store" in database:
                    valid_stores = ["DEFAULT", "FILE", "MEMORY"]
                    if database["wal_temp_store"] not in valid_stores:
                        errors.append(f"database.wal_temp_store 必须是以下之一: {', '.join(valid_stores)}")

                # 验证压力测试配置
                stress_int_fields = [
                    "stress_pool_size", "stress_max_overflow", "stress_pool_timeout",
                    "stress_pool_recycle", "stress_sqlite_timeout"
                ]
                for field in stress_int_fields:
                    if field in database:
                        try:
                            value = int(database[field])
                            if value < 1:
                                errors.append(f"database.{field} 必须是正整数")
                        except (ValueError, TypeError):
                            errors.append(f"database.{field} 必须是正整数")

                # 验证 PostgreSQL SSL 模式
                if "pg_ssl_mode" in database:
                    valid_ssl_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
                    if database["pg_ssl_mode"] not in valid_ssl_modes:
                        errors.append(f"database.pg_ssl_mode 必须是以下之一: {', '.join(valid_ssl_modes)}")

                # 验证 PostgreSQL 超时时间
                if "pg_connect_timeout" in database:
                    try:
                        value = int(database["pg_connect_timeout"])
                        if value < 1:
                            errors.append("database.pg_connect_timeout 必须是正整数")
                    except (ValueError, TypeError):
                        errors.append("database.pg_connect_timeout 必须是正整数")

                # 验证 MySQL 字符集
                if "mysql_charset" in database:
                    if not isinstance(database["mysql_charset"], str):
                        errors.append("database.mysql_charset 必须是字符串")

                # 验证 MySQL 超时时间
                mysql_timeout_fields = ["mysql_pool_recycle", "mysql_connect_timeout", "mysql_read_timeout", "mysql_write_timeout"]
                for field in mysql_timeout_fields:
                    if field in database:
                        try:
                            value = int(database[field])
                            if value < 1:
                                errors.append(f"database.{field} 必须是正整数")
                        except (ValueError, TypeError):
                            errors.append(f"database.{field} 必须是正整数")

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
        1. 触发 lifespan 优雅关闭流程（关闭 WebSocket 连接、释放数据库连接池）
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
            import asyncio

            time.sleep(0.5)  # 让响应先返回

            if not force:
                # 尝试优雅关闭：触发 lifespan 关闭流程
                try:
                    from lifespan import get_lifecycle_manager
                    
                    manager = get_lifecycle_manager()
                    
                    # 创建新的事件循环来运行异步关闭
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(manager.shutdown())
                        loop.close()
                        logger.info("优雅关闭完成")
                        
                        # 关闭完成后终止进程
                        _terminate_process()
                        return
                    except Exception as loop_error:
                        logger.error(f"事件循环执行失败: {loop_error}")
                        raise
                        
                except Exception as e:
                    logger.error(f"优雅关闭失败，将强制终止: {e}")

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
        1. 使用子进程启动新的应用实例
        2. 等待新进程启动
        3. 触发 lifespan 优雅关闭流程（关闭 WebSocket 连接、释放数据库连接池）
        4. 新进程启动成功后，旧进程退出

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
            import asyncio

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

                logger.info(f"新进程已启动，命令: {' '.join(cmd)}")

                # 给新进程一点时间启动
                time.sleep(1)

                # 优雅关闭当前进程：触发 lifespan 关闭流程
                try:
                    from lifespan import get_lifecycle_manager

                    manager = get_lifecycle_manager()

                    # 创建新的事件循环来运行异步关闭
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(manager.shutdown())
                    loop.close()
                    logger.info("优雅关闭完成")

                except Exception as e:
                    logger.error(f"优雅关闭失败: {e}")
                    # 即使优雅关闭失败，也继续终止进程

                # 终止当前进程
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
            Dict[str, Any]: 应用状态信息，包含运行时信息、请求统计、Git操作状态等
        """
        config = get_config()

        # 计算运行时间
        uptime = datetime.now() - self._start_time
        uptime_seconds = int(uptime.total_seconds())

        # 获取进程信息
        process_info = self._get_process_info()

        # 获取请求统计
        requests_info = self._get_requests_info()

        # 获取Git操作状态
        git_info = self._get_git_operations_info()

        return {
            "status": "running",
            "debug_mode": config.app.debug,
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": self._format_uptime(uptime_seconds),
            "version": "1.0.0",  # TODO: 从版本文件读取
            "server_time": datetime.now().isoformat(),
            "process": process_info,
            "requests": requests_info,
            "git_operations": git_info,
        }

    def _get_process_info(self) -> Dict[str, Any]:
        """
        获取当前进程信息

        Returns:
            Dict[str, Any]: 进程信息
        """
        import psutil
        import os

        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            return {
                "pid": process.pid,
                "memory_mb": round(memory_info.rss / (1024 * 1024), 2),
                "cpu_percent": process.cpu_percent(interval=0.1),
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

    def _get_requests_info(self) -> Dict[str, Any]:
        """
        获取请求统计信息

        Returns:
            Dict[str, Any]: 请求统计信息
        """
        from middleware.request_stats import get_request_stats
        return get_request_stats().get_stats()

    def _get_git_operations_info(self) -> Dict[str, Any]:
        """
        获取Git操作状态信息

        Returns:
            Dict[str, Any]: Git操作状态
        """
        # TODO: 实现真实的Git操作状态监控
        # 目前返回占位数据，后续可以接入Git操作队列
        return {
            "active_clones": 0,
            "active_pushes": 0,
            "queue_size": 0,
        }

    # ==================== 日志服务方法 ====================

    def get_log_info(self) -> Dict[str, Any]:
        """
        获取日志系统信息（适配新版日志系统）

        Returns:
            Dict[str, Any]: 日志信息，包括日志目录、日志文件列表等
        """
        from utils.logging import get_log_info as get_simple_log_info, LogManager

        # 使用新版日志系统的信息获取函数，传入默认日志目录
        info = get_simple_log_info(log_dir=LogManager.DEFAULT_LOG_DIR)

        return {
            "log_dir": info["log_dir"],
            "today_dir": info["today_dir"],
            "today_files": info["files"],
            "available_dates": info["available_dates"],
        }

    def get_log_content(
        self,
        date: Optional[str] = None,
        log_name: str = "langit",
        lines: int = 100,
        level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取日志内容（适配新版日志系统）

        Args:
            date: 日期字符串 (YYYY-MM-DD)，None 表示今天
            log_name: 日志文件名（不含扩展名），如 'langit', 'error', 'audit'
            lines: 返回的行数（从末尾开始）
            level: 过滤日志级别 (debug/info/warning/error/critical)

        Returns:
            Dict[str, Any]: 日志内容和元数据
        """
        from utils.logging import LogManager, read_log_file

        # 确定日期
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # 验证日期格式
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValidationException(detail="日期格式无效，应为 YYYY-MM-DD")

        # 构建日志文件路径
        log_dir = Path(LogManager.DEFAULT_LOG_DIR) / date
        log_file = log_dir / f"{log_name}.log"

        # 如果文件不存在，尝试使用默认的 langit.log
        if not log_file.exists():
            log_file = log_dir / "langit.log"

        if not log_file.exists():
            return {
                "date": date,
                "log_name": log_name,
                "lines": 0,
                "total_lines": 0,
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

        from utils.logging import cleanup_old_logs, LogManager

        if keep_days < 1:
            raise ValidationException(detail="保留天数必须大于等于1")

        deleted_count = cleanup_old_logs(
            keep_days=keep_days,
            log_dir=LogManager.DEFAULT_LOG_DIR
        )

        return {
            "success": True,
            "deleted_count": deleted_count,
            "keep_days": keep_days,
        }

    def migrate_database(
        self,
        source_type: str,
        target_type: str,
        source_url: str,
        target_url: str,
        is_debug: bool = False,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        执行数据库迁移

        将数据从源数据库迁移到目标数据库。

        Args:
            source_type: 源数据库类型
            target_type: 目标数据库类型
            source_url: 源数据库URL（由前端从加密配置提供）
            target_url: 目标数据库URL（由前端从加密配置提供）
            is_debug: 是否调试模式
            is_admin: 是否管理员

        Returns:
            Dict[str, Any]: 迁移结果
        """
        self._check_permission(is_debug, is_admin)

        try:
            from utils.migration import DatabaseMigration, MigrationError
            from config import get_config, ConfigManager

            config = get_config()

            logger.info(f"开始数据库迁移: {source_type} -> {target_type}")
            logger.info(f"源数据库: {source_url}")
            logger.info(f"目标数据库: {target_url}")

            # 创建迁移器
            migrator = DatabaseMigration()

            # 执行迁移
            result = migrator.migrate(source_url, target_url)

            logger.info(f"数据库迁移完成: {result}")

            # 迁移成功，更新 current_db_type
            config.database.current_db_type = target_type
            
            # 保存配置
            try:
                config_manager = ConfigManager()
                config_manager.save_config(config)
                logger.info(f"已更新 current_db_type 为: {target_type}")
            except Exception as save_error:
                logger.error(f"保存配置失败: {save_error}")
                # 配置保存失败不影响迁移结果，但应该记录日志

            return {
                "success": True,
                "message": f"成功从 {source_type} 迁移到 {target_type}",
                "tables": result,
                "export_file": None  # 临时文件已清理
            }

        except MigrationError as e:
            logger.error(f"数据库迁移失败: {e}")
            return {
                "success": False,
                "message": f"迁移失败: {str(e)}",
                "tables": {},
                "export_file": None
            }
        except Exception as e:
            logger.error(f"数据库迁移时发生错误: {e}")
            return {
                "success": False,
                "message": f"迁移时发生错误: {str(e)}",
                "tables": {},
                "export_file": None
            }

    def test_database_connection(self, db_url: str) -> Tuple[bool, List[str]]:
        """
        测试数据库连接

        Args:
            db_url: 数据库连接URL

        Returns:
            Tuple[bool, List[str]]: (是否成功, 错误信息列表)
        """
        errors = []

        try:
            from utils.db_validation import validate_database_config
            from sqlalchemy import create_engine, text

            # 检测数据库类型
            url_lower = db_url.lower()
            if url_lower.startswith("sqlite"):
                db_type = "sqlite"
            elif url_lower.startswith("postgresql") or url_lower.startswith("postgres"):
                db_type = "postgresql"
            elif url_lower.startswith("mysql"):
                db_type = "mysql"
            else:
                return False, ["无法识别的数据库类型"]

            # 验证配置
            validate_database_config(db_url, db_type)

            # 测试连接
            engine = create_engine(db_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()

            return True, []

        except Exception as e:
            errors.append(f"连接测试失败: {str(e)}")
            return False, errors

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
