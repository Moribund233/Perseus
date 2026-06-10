"""
配置工具模块

提供配置文件的生成、读取、更新和验证功能（工具函数版本）
"""
import os
from typing import Any, Dict

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
