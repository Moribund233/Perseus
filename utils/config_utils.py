"""
配置工具模块

提供配置文件的生成、读取、更新和验证功能
"""
import os
import re
import secrets
import sys
from typing import Any, Dict, List, Optional

import toml

from config import Config
from utils.logging import get_named_logger

logger = get_named_logger("config")


def generate_default_config() -> Dict[str, Any]:
    """
    生成默认配置，包含系统信息获取
    注意：敏感配置（JWT Secret Key、Debug 模式）通过环境变量注入，不写入配置文件

    Returns:
        Dict[str, Any]: 默认配置字典
    """
    system_info = {
        "platform": sys.platform,
        "python_version": sys.version,
        "python_version_info": {
            "major": sys.version_info.major,
            "minor": sys.version_info.minor,
            "micro": sys.version_info.micro,
            "releaselevel": sys.version_info.releaselevel,
            "serial": sys.version_info.serial,
        },
    }

    default_config = Config()
    config_dict = default_config.model_dump()

    # 默认配置：禁用 reload（避免打包后反复重启）
    config_dict["server"]["workers"] = 1
    config_dict["server"]["reload"] = False

    if sys.platform != "win32":
        config_dict["server"]["workers"] = min(4, os.cpu_count() or 2)

    config_dict["system"] = system_info

    # 移除敏感配置项（这些通过环境变量注入，不写入配置文件）
    # 1. 移除 security.secret_key（JWT Secret Key）
    if "security" in config_dict and "secret_key" in config_dict["security"]:
        del config_dict["security"]["secret_key"]
        logger.debug("已从默认配置中移除 security.secret_key（通过环境变量注入）")

    # 2. 移除 app.debug（调试模式）
    if "app" in config_dict and "debug" in config_dict["app"]:
        del config_dict["app"]["debug"]
        logger.debug("已从默认配置中移除 app.debug（通过环境变量注入）")

    # 3. 移除 database.url 和 database.is_stress_test（数据库连接配置）
    if "database" in config_dict:
        if "url" in config_dict["database"]:
            del config_dict["database"]["url"]
            logger.debug("已从默认配置中移除 database.url（通过环境变量 DATABASE_URL 注入）")
        if "is_stress_test" in config_dict["database"]:
            del config_dict["database"]["is_stress_test"]
            logger.debug("已从默认配置中移除 database.is_stress_test（通过环境变量 LANGIT_STRESS_TEST 注入）")

    return config_dict


def write_config_file(config_data: Dict[str, Any], config_path: str = "config.toml") -> None:
    """
    将配置写入文件

    Args:
        config_data: 配置字典
        config_path: 配置文件路径

    Raises:
        RuntimeError: 写入失败时抛出
    """
    try:
        dir_name = os.path.dirname(config_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            toml.dump(config_data, f)
    except IOError as e:
        raise RuntimeError(f"写入配置文件失败: {e}")


class ConfigManager:
    """
    配置管理器类

    提供配置文件的读取、更新、删除和验证功能
    支持点号分隔的嵌套键访问，如 'server.port'
    """

    def __init__(self, config_path: str = "config.toml"):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path

    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件

        Returns:
            Dict[str, Any]: 配置数据，文件不存在或格式错误返回空字典
        """
        if not os.path.exists(self.config_path):
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return toml.load(f)
        except (toml.TomlDecodeError, PermissionError, IsADirectoryError) as e:
            logger.error(f"加载配置文件失败 ({self.config_path}): {type(e).__name__}: {e}")
            return {}
        except Exception as e:
            logger.error(f"加载配置文件失败 ({self.config_path}): {type(e).__name__}: {e}")
            return {}

    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置文件

        Args:
            config: 配置数据

        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            dir_name = os.path.dirname(self.config_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                toml.dump(config, f)
            return True
        except (PermissionError, IsADirectoryError, IOError) as e:
            logger.error(f"保存配置文件失败 ({self.config_path}): {type(e).__name__}: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        支持点号分隔的嵌套键，如 'server.port'

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            Any: 配置值，不存在返回默认值
        """
        config = self.load_config()
        keys = key.split(".")
        value = config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值

        支持点号分隔的嵌套键，如 'server.port'

        Args:
            key: 配置键名
            value: 配置值

        Returns:
            bool: 设置成功返回True，否则返回False
        """
        config = self.load_config()
        keys = key.split(".")
        current = config

        # 创建嵌套结构
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value
        return self.save_config(config)

    def delete(self, key: str) -> bool:
        """
        删除配置项

        Args:
            key: 配置键名

        Returns:
            bool: 删除成功返回True，否则返回False
        """
        config = self.load_config()
        keys = key.split(".")
        current = config

        # 导航到父节点
        for k in keys[:-1]:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return False

        # 删除键
        if isinstance(current, dict) and keys[-1] in current:
            del current[keys[-1]]
            return self.save_config(config)

        return False

    def get_server_config(self) -> Dict[str, Any]:
        """
        获取服务器配置

        Returns:
            Dict[str, Any]: 服务器配置字典
        """
        return self.get("server", {})

    def get_app_config(self) -> Dict[str, Any]:
        """
        获取应用配置

        Returns:
            Dict[str, Any]: 应用配置字典
        """
        return self.get("app", {})

    def get_proxy_config(self) -> Dict[str, Any]:
        """
        获取代理配置

        Returns:
            Dict[str, Any]: 代理配置字典
        """
        return self.get("proxy", {})

    def get_storage_config(self) -> Dict[str, Any]:
        """
        获取存储配置

        Returns:
            Dict[str, Any]: 存储配置字典
        """
        return self.get("storage", {})

    def get_security_config(self) -> Dict[str, Any]:
        """
        获取安全配置

        Returns:
            Dict[str, Any]: 安全配置字典
        """
        return self.get("security", {})

    def get_secret_key(self) -> Optional[str]:
        """
        获取JWT Secret Key
        只能从环境变量 LANGIT_SECURITY_SECRET_KEY 读取

        Returns:
            Optional[str]: Secret Key，如果不存在返回None
        """
        # 只能从环境变量读取（Client 注入）
        return os.environ.get("LANGIT_SECURITY_SECRET_KEY")

    def get_repo_root(self) -> str:
        """
        获取仓库根目录路径

        Returns:
            str: 仓库根目录路径，默认为./repositories
        """
        return self.get("storage.repo_root", "./repositories")

    def set_repo_root(self, repo_root: str) -> bool:
        """
        设置仓库根目录路径

        Args:
            repo_root: 仓库根目录路径

        Returns:
            bool: 设置成功返回True，否则返回False
        """
        if not isinstance(repo_root, str) or not repo_root.strip():
            logger.warning("仓库根目录路径不能为空")
            return False
        return self.set("storage.repo_root", os.path.abspath(repo_root.strip()))

    def validate_config(self) -> tuple[bool, List[str]]:
        """
        验证配置文件

        Returns:
            tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors: List[str] = []
        config = self.load_config()

        # 验证服务器配置
        server = config.get("server", {})

        # 验证host格式
        if "host" in server:
            host = server["host"]
            if not isinstance(host, str) or not host:
                errors.append("服务器地址不能为空")
            else:
                ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
                hostname_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$"
                if (
                    host != "localhost"
                    and host != "0.0.0.0"
                    and not re.match(ip_pattern, host)
                    and not re.match(hostname_pattern, host)
                ):
                    errors.append("服务器地址格式无效")

        # 验证port范围
        if "port" in server:
            try:
                port = int(server["port"])
                if port < 1 or port > 65535:
                    errors.append("服务器端口必须是1-65535之间的整数")
            except (ValueError, TypeError):
                errors.append("服务器端口必须是1-65535之间的整数")

        # 验证workers
        if "workers" in server:
            try:
                workers = int(server["workers"])
                if workers < 1:
                    errors.append("服务器工作进程数必须是正整数")
            except (ValueError, TypeError):
                errors.append("服务器工作进程数必须是正整数")

        # 验证log_level
        if "log_level" in server:
            valid_levels = ["debug", "info", "warning", "error", "critical"]
            if server["log_level"] not in valid_levels:
                errors.append(f"日志级别必须是以下之一: {', '.join(valid_levels)}")

        return len(errors) == 0, errors

    def reset_to_defaults(self) -> bool:
        """
        重置为默认配置

        Returns:
            bool: 重置成功返回True，否则返回False
        """
        try:
            default_config = generate_default_config()
            return self.save_config(default_config)
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            return False


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: str = "config.toml") -> ConfigManager:
    """
    获取全局配置管理器实例

    Args:
        config_path: 配置文件路径

    Returns:
        ConfigManager: 配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager
