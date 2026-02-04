"""
客户端控制器模块

提供CLI和桌面客户端共用的控制器功能。
"""
from .service_controller import (
    ServiceController,
    ServiceState,
    get_service_controller
)

__all__ = [
    "ServiceController",
    "ServiceState",
    "get_service_controller"
]
