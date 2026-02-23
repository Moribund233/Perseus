"""
配置管理服务层

提供配置管理功能：
- 配置读取、修改、验证
- 配置重置
- 权限检查
"""
from typing import Any, Dict, List, Optional, Tuple

from utils.config_utils import ConfigManager, generate_default_config, get_config_manager
from exception import ValidationException, AuthorizationException


class ConfigService:
    """
    配置服务类

    提供配置管理功能
    """

    ALLOWED_CONFIG_SECTIONS = {"server", "proxy", "rate_limit", "cors", "database"}
    PROTECTED_CONFIG_SECTIONS = {"storage", "security", "app", "logging", "system"}
    RESTART_REQUIRED_CONFIGS = {
        "server": {"host", "port", "workers", "log_level"},
        "proxy": {"proxy"},
        "cors": {"allow_origins", "allow_credentials", "allow_methods", "allow_headers", "max_age"},
        "rate_limit": {"default_limits", "strict", "standard", "generous", "git_operations", "download"},
        "database": {
            "pool_size", "max_overflow", "pool_timeout", "pool_recycle", "echo",
            "sqlite_timeout", "sqlite_check_same_thread", "sqlite_isolation_level",
            "enable_wal", "wal_synchronous", "wal_cache_size", "wal_temp_store",
            "stress_pool_size", "stress_max_overflow", "stress_pool_timeout", "stress_pool_recycle",
            "stress_sqlite_timeout", "stress_echo",
            "pg_ssl_mode", "pg_connect_timeout", "pg_application_name",
            "mysql_charset", "mysql_pool_recycle", "mysql_connect_timeout",
            "mysql_read_timeout", "mysql_write_timeout",
        },
    }

    def __init__(self):
        """初始化配置服务"""
        self._config_manager: Optional[ConfigManager] = None

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
                detail="该操作需要本地认证或调试模式"
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

        is_valid, errors = self._validate_config_data(config_data)
        if not is_valid:
            raise ValidationException(detail=f"配置验证失败: {'; '.join(errors)}")

        restart_required, restart_items = self._check_restart_required(config_data)

        current_config = config_manager.load_config()
        merged_config = self._merge_config(current_config, config_data)

        success = config_manager.save_config(merged_config)
        if not success:
            return False, ["保存配置失败"], []

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

    def _merge_config(self, current: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并配置（深度合并）

        Args:
            current: 当前配置
            updates: 更新的配置

        Returns:
            Dict[str, Any]: 合并后的配置
        """
        result = current.copy()

        for section, values in updates.items():
            if section in result and isinstance(result[section], dict) and isinstance(values, dict):
                result[section] = {**result[section], **values}
            else:
                result[section] = values

        return result

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

        if "proxy" in config_data:
            errors.extend(self._validate_proxy_config(config_data["proxy"]))

        if "rate_limit" in config_data:
            errors.extend(self._validate_rate_limit_config(config_data["rate_limit"]))

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

    def _validate_proxy_config(self, proxy: Any) -> List[str]:
        """验证代理配置"""
        errors = []
        if not isinstance(proxy, dict):
            errors.append("proxy 配置必须是对象")
            return errors

        if "proxy" in proxy:
            if not isinstance(proxy["proxy"], bool):
                errors.append("proxy.proxy 必须是布尔值")

        return errors

    def _validate_rate_limit_config(self, rate_limit: Any) -> List[str]:
        """验证速率限制配置"""
        errors = []
        if not isinstance(rate_limit, dict):
            errors.append("rate_limit 配置必须是对象")
            return errors

        valid_limit_types = {"default_limits", "strict", "standard", "generous", "git_operations", "download"}
        for key in rate_limit.keys():
            if key not in valid_limit_types:
                errors.append(f"rate_limit 不支持 '{key}'，支持的类型: {', '.join(valid_limit_types)}")
            elif not isinstance(rate_limit[key], list):
                errors.append(f"rate_limit.{key} 必须是字符串数组")

        return errors

    def _validate_cors_config(self, cors: Any) -> List[str]:
        """验证 CORS 配置"""
        errors = []
        if not isinstance(cors, dict):
            errors.append("cors 配置必须是对象")
            return errors

        if "allow_origins" in cors:
            if not isinstance(cors["allow_origins"], list):
                errors.append("cors.allow_origins 必须是字符串数组")
            else:
                for origin in cors["allow_origins"]:
                    if not isinstance(origin, str):
                        errors.append("cors.allow_origins 中的所有项必须是字符串")
                        break
                    if origin == "*":
                        errors.append("生产环境不允许使用通配符 '*'，请配置具体的允许域名")

        if "allow_credentials" in cors:
            if not isinstance(cors["allow_credentials"], bool):
                errors.append("cors.allow_credentials 必须是布尔值")

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

        if "allow_headers" in cors:
            if not isinstance(cors["allow_headers"], list):
                errors.append("cors.allow_headers 必须是字符串数组")
            else:
                for header in cors["allow_headers"]:
                    if not isinstance(header, str):
                        errors.append("cors.allow_headers 中的所有项必须是字符串")
                        break

        if "max_age" in cors:
            try:
                max_age = int(cors["max_age"])
                if max_age < 0 or max_age > 86400:
                    errors.append("cors.max_age 必须在 0-86400 秒之间")
            except (ValueError, TypeError):
                errors.append("cors.max_age 必须是整数（秒）")

        return errors

    def _validate_database_config(self, database: Any) -> List[str]:
        """验证数据库配置"""
        errors = []
        if not isinstance(database, dict):
            errors.append("database 配置必须是对象")
            return errors

        pool_int_fields = ["pool_size", "max_overflow", "pool_timeout", "pool_recycle"]
        for field in pool_int_fields:
            if field in database:
                try:
                    value = int(database[field])
                    if value < 1:
                        errors.append(f"database.{field} 必须是正整数")
                except (ValueError, TypeError):
                    errors.append(f"database.{field} 必须是正整数")

        bool_fields = ["echo", "sqlite_check_same_thread", "enable_wal", "stress_echo"]
        for field in bool_fields:
            if field in database:
                if not isinstance(database[field], bool):
                    errors.append(f"database.{field} 必须是布尔值")

        if "sqlite_timeout" in database:
            try:
                value = int(database["sqlite_timeout"])
                if value < 1:
                    errors.append("database.sqlite_timeout 必须是正整数")
            except (ValueError, TypeError):
                errors.append("database.sqlite_timeout 必须是正整数")

        if "wal_synchronous" in database:
            valid_modes = ["OFF", "NORMAL", "FULL", "EXTRA"]
            if database["wal_synchronous"] not in valid_modes:
                errors.append(f"database.wal_synchronous 必须是以下之一: {', '.join(valid_modes)}")

        if "wal_cache_size" in database:
            try:
                value = int(database["wal_cache_size"])
                if value < 0:
                    errors.append("database.wal_cache_size 必须是非负整数")
            except (ValueError, TypeError):
                errors.append("database.wal_cache_size 必须是非负整数")

        if "wal_temp_store" in database:
            valid_stores = ["DEFAULT", "FILE", "MEMORY"]
            if database["wal_temp_store"] not in valid_stores:
                errors.append(f"database.wal_temp_store 必须是以下之一: {', '.join(valid_stores)}")

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

        if "pg_ssl_mode" in database:
            valid_ssl_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
            if database["pg_ssl_mode"] not in valid_ssl_modes:
                errors.append(f"database.pg_ssl_mode 必须是以下之一: {', '.join(valid_ssl_modes)}")

        if "pg_connect_timeout" in database:
            try:
                value = int(database["pg_connect_timeout"])
                if value < 1:
                    errors.append("database.pg_connect_timeout 必须是正整数")
            except (ValueError, TypeError):
                errors.append("database.pg_connect_timeout 必须是正整数")

        if "mysql_charset" in database:
            if not isinstance(database["mysql_charset"], str) or not database["mysql_charset"]:
                errors.append("database.mysql_charset 必须是非空字符串")

        mysql_timeout_fields = ["mysql_connect_timeout", "mysql_read_timeout", "mysql_write_timeout"]
        for field in mysql_timeout_fields:
            if field in database:
                try:
                    value = int(database[field])
                    if value < 1:
                        errors.append(f"database.{field} 必须是正整数")
                except (ValueError, TypeError):
                    errors.append(f"database.{field} 必须是正整数")

        return errors


_config_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """
    获取全局配置服务实例

    Returns:
        ConfigService: 配置服务实例
    """
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service
