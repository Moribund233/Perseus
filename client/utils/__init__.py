"""
客户端工具模块

提供CLI和桌面客户端共用的工具函数。
"""
from .config_manager import (
    ClientConfigManager,
    get_client_config_manager
)

__all__ = [
    "ClientConfigManager",
    "get_client_config_manager"
]
