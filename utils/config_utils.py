"""
配置工具模块

提供配置文件的生成、读取、更新和验证功能
"""
import os
import re
import secrets
from typing import Any, Dict, List, Optional

import toml

from utils.logging import get_named_logger

logger = get_named_logger("config")


def load_example_config() -> Dict[str, Any]:
    """
    加载 config.example.toml 作为默认配置模板

    Returns:
        Dict[str, Any]: 配置字典，文件不存在返回空字典

    Raises:
        FileNotFoundError: config.example.toml 不存在时抛出
    """
    example_path = "config.example.toml"
    if not os.path.exists(example_path):
        raise FileNotFoundError(
            f"{example_path} 不存在，请确保项目包含配置文件模板"
        )

    import toml
    with open(example_path, "r", encoding="utf-8") as f:
        return toml.load(f)


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
        只能从环境变量 PERSEUS_SECURITY_SECRET_KEY 读取

        Returns:
            Optional[str]: Secret Key，如果不存在返回None
        """
        # 只能从环境变量读取（Client 注入）
        return os.environ.get("PERSEUS_SECURITY_SECRET_KEY")

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
        重置为默认配置（从 config.example.toml 读取）

        Returns:
            bool: 重置成功返回True，否则返回False
        """
        try:
            default_config = load_example_config()
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
