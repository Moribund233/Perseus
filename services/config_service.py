"""
配置管理服务层

提供配置管理功能：
- 配置读取、修改、验证
- 配置重置
- 权限检查
"""
from typing import Any, Dict, List, Optional, Tuple

from core.config import ConfigManager, get_config as get_core_config
from core.exception import ValidationException, AuthorizationException


class ConfigService:
    """
    配置服务类

    提供配置管理功能
    """

    ALLOWED_CONFIG_SECTIONS = {"server", "gunicorn", "proxy", "cors", "database"}
    PROTECTED_CONFIG_SECTIONS = {"storage", "security", "app", "logging", "system"}
    RESTART_REQUIRED_CONFIGS = {
        "server": {"host", "port", "log_level"},
        "gunicorn": {
            "workers", "worker_class", "threads", "worker_connections", "backlog",
            "timeout", "graceful_timeout", "keepalive", "max_requests", "max_requests_jitter",
            "preload_app", "daemon", "access_log", "access_log_format", "capture_output",
            "enable_reuse_port"
        },
        "proxy": {"proxy"},
        "cors": {"allow_origins", "allow_credentials", "allow_methods", "allow_headers", "max_age"},
        "database": {
            "pool_size", "max_overflow", "pool_timeout", "pool_recycle", "echo",
            "sqlite_timeout", "sqlite_check_same_thread", "sqlite_isolation_level",
            "enable_wal", "wal_synchronous", "wal_cache_size", "wal_temp_store",
            "stress_pool_size", "stress_max_overflow", "stress_pool_timeout", "stress_pool_recycle",
            "stress_sqlite_timeout", "stress_echo",
            "pg_ssl_mode", "pg_connect_timeout", "pg_application_name",
        },
    }

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
                detail="该操作需要调试模式或管理员权限"
            )

    def get_config(self, section: Optional[str] = None) -> Dict[str, Any]:
        """
        获取应用配置

        Args:
            section: 配置节名称，为None则返回全部配置

        Returns:
            Dict[str, Any]: 配置数据
        """
        config = get_core_config()
        config_dict = config.model_dump()

        if section:
            return config_dict.get(section, {})
        return config_dict

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

        is_valid, errors = self._validate_config_data(config_data)
        if not is_valid:
            raise ValidationException(detail=f"配置验证失败: {'; '.join(errors)}")

        restart_required, restart_items = self._check_restart_required(config_data)

        config_manager = ConfigManager()
        config_manager.update_config(config_data)

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

        import toml
        try:
            with open("config.example.toml", "r", encoding="utf-8") as f:
                example_config = toml.load(f)
        except FileNotFoundError:
            return False, ["config.example.toml 不存在，无法重置"]

        config_manager = ConfigManager()

        # 使用 update_config 方法重置配置
        try:
            config_manager.update_config(example_config)
            return True, []
        except Exception as e:
            return False, [f"重置配置失败: {str(e)}"]

    def validate_config(self, config_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[str]]:
        """
        验证配置数据

        Args:
            config_data: 要验证的配置数据，为None则验证当前配置

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        if config_data is None:
            config_data = self.get_config()

        return self._validate_config_data(config_data)

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

    def _validate_config_data(self, config_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证配置数据的内部方法

        Args:
            config_data: 配置数据

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []

        for section in config_data.keys():
            if section in self.PROTECTED_CONFIG_SECTIONS:
                errors.append(f"配置节 '{section}' 不允许修改")
                continue
            if section not in self.ALLOWED_CONFIG_SECTIONS:
                errors.append(f"未知的配置节: {section}")

        if not any(section in self.ALLOWED_CONFIG_SECTIONS for section in config_data.keys()):
            errors.append("没有可修改的有效配置节")

        if "server" in config_data:
            errors.extend(self._validate_server_config(config_data["server"]))

        if "gunicorn" in config_data:
            errors.extend(self._validate_gunicorn_config(config_data["gunicorn"]))

        if "proxy" in config_data:
            errors.extend(self._validate_proxy_config(config_data["proxy"]))

        if "cors" in config_data:
            errors.extend(self._validate_cors_config(config_data["cors"]))

        if "database" in config_data:
            errors.extend(self._validate_database_config(config_data["database"]))

        return len(errors) == 0, errors

    def _validate_server_config(self, server: Any) -> List[str]:
        """验证服务器配置"""
        errors = []
        if not isinstance(server, dict):
            errors.append("server 配置必须是对象")
            return errors

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

        return errors

    def _validate_gunicorn_config(self, gunicorn: Any) -> List[str]:
        """验证 Gunicorn 配置"""
        errors = []
        if not isinstance(gunicorn, dict):
            errors.append("gunicorn 配置必须是对象")
            return errors

        int_fields = ["workers", "threads", "worker_connections", "backlog", "timeout",
                      "graceful_timeout", "keepalive", "max_requests", "max_requests_jitter"]
        for field in int_fields:
            if field in gunicorn:
                try:
                    value = int(gunicorn[field])
                    if value < 0:
                        errors.append(f"gunicorn.{field} 必须是非负整数")
                except (ValueError, TypeError):
                    errors.append(f"gunicorn.{field} 必须是整数")

        bool_fields = ["preload_app", "daemon", "access_log", "capture_output", "enable_reuse_port"]
        for field in bool_fields:
            if field in gunicorn and not isinstance(gunicorn[field], bool):
                errors.append(f"gunicorn.{field} 必须是布尔值")

        return errors

    def _validate_proxy_config(self, proxy: Any) -> List[str]:
        """验证代理配置"""
        errors = []
        if not isinstance(proxy, dict):
            errors.append("proxy 配置必须是对象")
            return errors

        if "proxy" in proxy and not isinstance(proxy["proxy"], bool):
            errors.append("proxy.proxy 必须是布尔值")

        return errors

    def _validate_cors_config(self, cors: Any) -> List[str]:
        """验证 CORS 配置"""
        errors = []
        if not isinstance(cors, dict):
            errors.append("cors 配置必须是对象")
            return errors

        if "allow_origins" in cors:
            origins = cors["allow_origins"]
            if not isinstance(origins, list):
                errors.append("cors.allow_origins 必须是数组")
            elif not all(isinstance(o, str) for o in origins):
                errors.append("cors.allow_origins 中的所有元素必须是字符串")

        if "allow_methods" in cors:
            methods = cors["allow_methods"]
            if not isinstance(methods, list):
                errors.append("cors.allow_methods 必须是数组")
            elif not all(isinstance(m, str) for m in methods):
                errors.append("cors.allow_methods 中的所有元素必须是字符串")

        if "allow_headers" in cors:
            headers = cors["allow_headers"]
            if not isinstance(headers, list):
                errors.append("cors.allow_headers 必须是数组")
            elif not all(isinstance(h, str) for h in headers):
                errors.append("cors.allow_headers 中的所有元素必须是字符串")

        if "allow_credentials" in cors and not isinstance(cors["allow_credentials"], bool):
            errors.append("cors.allow_credentials 必须是布尔值")

        if "max_age" in cors:
            try:
                max_age = int(cors["max_age"])
                if max_age < 0:
                    errors.append("cors.max_age 必须是非负整数")
            except (ValueError, TypeError):
                errors.append("cors.max_age 必须是整数")

        return errors

    def _validate_database_config(self, database: Any) -> List[str]:
        """验证数据库配置"""
        errors = []
        if not isinstance(database, dict):
            errors.append("database 配置必须是对象")
            return errors

        # 检查是否尝试修改只读配置
        readonly_fields = ["url", "is_stress_test"]
        for field in readonly_fields:
            if field in database:
                errors.append(f"database.{field} 不允许修改（通过环境变量注入）")

        int_fields = ["pool_size", "max_overflow", "pool_timeout", "pool_recycle",
                      "sqlite_timeout", "wal_cache_size", "pg_connect_timeout"]
        for field in int_fields:
            if field in database:
                try:
                    value = int(database[field])
                    if value < 0:
                        errors.append(f"database.{field} 必须是非负整数")
                except (ValueError, TypeError):
                    errors.append(f"database.{field} 必须是整数")

        bool_fields = ["echo", "sqlite_check_same_thread", "enable_wal"]
        for field in bool_fields:
            if field in database and not isinstance(database[field], bool):
                errors.append(f"database.{field} 必须是布尔值")

        return errors


# 全局配置服务实例
_config_service_instance: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """
    获取全局配置服务实例

    Returns:
        ConfigService: 配置服务实例
    """
    global _config_service_instance
    if _config_service_instance is None:
        _config_service_instance = ConfigService()
    return _config_service_instance
