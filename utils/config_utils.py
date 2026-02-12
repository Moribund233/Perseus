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


def generate_default_config() -> Dict[str, Any]:
    """
    生成默认配置，包含系统信息获取

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

    if sys.platform == "win32":
        # Windows下将install_path转换为绝对路径
        install_path = config_dict["nginx"].get("install_path", "nginx")
        if install_path:
            config_dict["nginx"]["install_path"] = os.path.abspath(install_path)
    else:
        config_dict["server"]["workers"] = min(4, os.cpu_count() or 2)
        # Linux下install_path不使用，设置为空字符串
        config_dict["nginx"]["install_path"] = ""

    config_dict["system"] = system_info

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
            print(f"加载配置文件失败 ({self.config_path}): {type(e).__name__}: {e}")
            return {}
        except Exception as e:
            print(f"加载配置文件失败 ({self.config_path}): {type(e).__name__}: {e}")
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
            print(f"保存配置文件失败 ({self.config_path}): {type(e).__name__}: {e}")
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

    def get_nginx_config(self) -> Dict[str, Any]:
        """
        获取Nginx配置

        Returns:
            Dict[str, Any]: Nginx配置字典
        """
        return self.get("nginx", {})

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

        Returns:
            Optional[str]: Secret Key，如果不存在返回None
        """
        return self.get("security.secret_key")

    def set_secret_key(self, secret_key: str) -> bool:
        """
        设置JWT Secret Key

        Args:
            secret_key: Secret Key

        Returns:
            bool: 设置成功返回True，否则返回False
        """
        if not secret_key or not isinstance(secret_key, str):
            print("Secret Key 不能为空且必须是字符串")
            return False
        return self.set("security.secret_key", secret_key)

    def generate_and_save_secret_key(self) -> Optional[str]:
        """
        生成并保存新的JWT Secret Key

        Returns:
            Optional[str]: 生成的Secret Key，失败返回None
        """
        secret_key = secrets.token_urlsafe(32)
        if self.set_secret_key(secret_key):
            print("已生成并保存新的 JWT Secret Key")
            return secret_key
        else:
            print("保存 JWT Secret Key 失败")
            return None

    def ensure_secret_key(self) -> Optional[str]:
        """
        确保Secret Key存在，如果不存在则生成

        Returns:
            Optional[str]: Secret Key，失败返回None
        """
        secret_key = self.get_secret_key()
        if secret_key:
            return secret_key

        print("JWT Secret Key 不存在，正在生成...")
        return self.generate_and_save_secret_key()

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
            print("仓库根目录路径不能为空")
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

        # 验证Nginx配置
        nginx = config.get("nginx", {})

        # 验证listen_port
        if "listen_port" in nginx:
            try:
                listen_port = int(nginx["listen_port"])
                if listen_port < 1 or listen_port > 65535:
                    errors.append("Nginx监听端口必须是1-65535之间的整数")
            except (ValueError, TypeError):
                errors.append("Nginx监听端口必须是1-65535之间的整数")

        # 验证api_port
        if "api_port" in nginx:
            try:
                api_port = int(nginx["api_port"])
                if api_port < 1 or api_port > 65535:
                    errors.append("Nginx API端口必须是1-65535之间的整数")
            except (ValueError, TypeError):
                errors.append("Nginx API端口必须是1-65535之间的整数")

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
            print(f"重置配置失败: {e}")
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
