"""
应用管理控制器

提供应用级别的管理 API：
- 根路由（欢迎信息）
- 健康检查
- 配置管理（读取、修改、重置、验证）
- 应用控制（关机、重启）
- 系统状态监控

配置管理、关机、重启等 API 仅在调试模式或管理员权限下可用
"""
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, Body
from pydantic import BaseModel, Field

from config import get_config
from services.app_service import get_app_service, AppService
from api.dependencies import get_current_user
from exception import AuthorizationException

# 创建路由实例
router = APIRouter(tags=["app-management"])


# ============== 根路由和健康检查 ==============


@router.get("/", tags=["root"])
async def root():
    """
    根路由 - 欢迎信息

    Returns:
        dict: 应用基本信息
    """
    config = get_config()
    return {
        "message": "Welcome to LanGit API",
        "title": config.app.title,
        "version": config.app.version,
        "status": "running"
    }


@router.get("/health", tags=["health"])
async def health_check():
    """
    健康检查路由

    Returns:
        dict: 健康状态信息
    """
    config = get_config()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": config.app.title
    }


# ============== Pydantic 模型 ==============


class ConfigResponse(BaseModel):
    """配置响应模型"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    errors: list = Field(default_factory=list)


class ConfigUpdateRequest(BaseModel):
    """配置更新请求模型"""
    config: Dict[str, Any] = Field(..., description="新的配置数据")


class ConfigSectionRequest(BaseModel):
    """配置节请求模型"""
    section: Optional[str] = Field(None, description="配置节名称")


class StatusResponse(BaseModel):
    """状态响应模型"""
    status: str
    debug_mode: bool
    uptime_seconds: int
    uptime_formatted: str
    system: Dict[str, Any]
    version: str


class ActionResponse(BaseModel):
    """操作响应模型"""
    success: bool
    message: str


# ============== 依赖函数 ==============


def check_app_permission(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> tuple[bool, bool]:
    """
    检查应用管理权限

    Args:
        current_user: 当前用户信息

    Returns:
        tuple[bool, bool]: (是否调试模式, 是否管理员)

    Raises:
        AuthorizationException: 权限不足
    """
    config = get_config()
    is_debug = config.app.debug

    # 检查是否是管理员
    is_admin = False
    if current_user:
        # 从用户信息中检查管理员权限
        user_role = current_user.get("role", "")
        is_admin = user_role == "admin"

    # 调试模式或管理员可以访问
    if not is_debug and not is_admin:
        raise AuthorizationException(
            detail="该操作仅在调试模式或管理员权限下可用"
        )

    return is_debug, is_admin


# ============== API 路由 ==============


@router.get("/api/app/config", response_model=ConfigResponse)
async def get_config_endpoint(
    section: Optional[str] = Query(None, description="配置节名称"),
    permission: tuple = Depends(check_app_permission)
):
    """
    获取应用配置

    Args:
        section: 配置节名称，如 'server', 'app', 'storage' 等

    Returns:
        ConfigResponse: 配置数据
    """
    app_service = get_app_service()
    config_data = app_service.get_config(section)

    return ConfigResponse(
        success=True,
        data=config_data,
        errors=[]
    )


@router.post("/api/app/config", response_model=ConfigResponse)
async def update_config_endpoint(
    request: ConfigUpdateRequest,
    permission: tuple = Depends(check_app_permission)
):
    """
    更新应用配置

    Args:
        request: 配置更新请求

    Returns:
        ConfigResponse: 更新结果
    """
    is_debug, is_admin = permission
    app_service = get_app_service()

    success, errors = app_service.update_config(
        request.config,
        is_debug=is_debug,
        is_admin=is_admin
    )

    return ConfigResponse(
        success=success,
        errors=errors
    )


@router.post("/api/app/config/reset", response_model=ConfigResponse)
async def reset_config_endpoint(
    permission: tuple = Depends(check_app_permission)
):
    """
    重置配置为默认值

    Returns:
        ConfigResponse: 重置结果
    """
    is_debug, is_admin = permission
    app_service = get_app_service()

    success, errors = app_service.reset_config(
        is_debug=is_debug,
        is_admin=is_admin
    )

    return ConfigResponse(
        success=success,
        errors=errors
    )


@router.post("/api/app/config/validate", response_model=ConfigResponse)
async def validate_config_endpoint(
    config_data: Optional[Dict[str, Any]] = Body(None, description="要验证的配置数据"),
    permission: tuple = Depends(check_app_permission)
):
    """
    验证配置数据

    Args:
        config_data: 要验证的配置数据，为空则验证当前配置

    Returns:
        ConfigResponse: 验证结果
    """
    app_service = get_app_service()
    is_valid, errors = app_service.validate_config(config_data)

    return ConfigResponse(
        success=is_valid,
        errors=errors
    )


@router.get("/api/app/status", response_model=StatusResponse)
async def get_status_endpoint():
    """
    获取应用状态

    Returns:
        StatusResponse: 应用状态信息
    """
    app_service = get_app_service()
    status = app_service.get_status()

    return StatusResponse(**status)


@router.post("/api/app/shutdown", response_model=ActionResponse)
async def shutdown_endpoint(
    permission: tuple = Depends(check_app_permission)
):
    """
    关闭应用

    发送信号触发优雅关闭

    Returns:
        ActionResponse: 操作结果
    """
    is_debug, is_admin = permission
    app_service = get_app_service()

    success = app_service.shutdown(
        is_debug=is_debug,
        is_admin=is_admin
    )

    return ActionResponse(
        success=success,
        message="应用将在稍后关闭" if success else "关闭失败"
    )


@router.post("/api/app/restart", response_model=ActionResponse)
async def restart_endpoint(
    permission: tuple = Depends(check_app_permission)
):
    """
    重启应用

    仅在调试模式下可用（使用 Uvicorn 时）

    Returns:
        ActionResponse: 操作结果
    """
    is_debug, is_admin = permission
    app_service = get_app_service()

    success = app_service.restart(
        is_debug=is_debug,
        is_admin=is_admin
    )

    return ActionResponse(
        success=success,
        message="应用将在稍后重启" if success else "重启失败"
    )
