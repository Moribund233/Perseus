import os
import sys
from typing import Dict, Any

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
            "serial": sys.version_info.serial
        }
    }

    default_config = Config()
    config_dict = default_config.model_dump()

    if sys.platform == "win32":
        config_dict["server"]["workers"] = 1
        config_dict["server"]["reload"] = True
        # Windows下将install_path转换为绝对路径
        install_path = config_dict["nginx"].get("install_path", "nginx")
        if install_path:
            config_dict["nginx"]["install_path"] = os.path.abspath(install_path)
    else:
        config_dict["server"]["workers"] = min(4, os.cpu_count() or 2)
        config_dict["server"]["reload"] = False
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
    """
    try:
        dir_name = os.path.dirname(config_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            toml.dump(config_data, f)
    except IOError as e:
        raise RuntimeError(f"写入配置文件失败: {e}")
