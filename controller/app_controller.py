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
from api.local_auth import get_local_auth_user, LocalUser
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
    hints: list = Field(default_factory=list, description="提示信息列表，如需要重启的提示")


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
    version: str
    server_time: str
    process: Dict[str, Any]
    requests: Dict[str, Any]
    git_operations: Dict[str, Any]


class ActionResponse(BaseModel):
    """操作响应模型"""
    success: bool
    message: str


# ============== 依赖函数 ==============


def check_app_permission(
    current_user: Optional[Any] = Depends(get_current_user),
    local_user: Optional[LocalUser] = Depends(get_local_auth_user)
) -> tuple[bool, bool]:
    """
    检查应用管理权限
    支持本地认证（Tauri Client）或 JWT 认证（管理员）

    Args:
        current_user: 当前用户信息（JWT 认证）- User对象或字典
        local_user: 本地用户对象（本地认证）

    Returns:
        tuple[bool, bool]: (是否调试模式, 是否管理员)

    Raises:
        AuthorizationException: 权限不足
    """
    from models.user import User
    
    config = get_config()
    is_debug = config.app.debug

    # 检查是否是本地认证（Client 具有最高权限）
    if local_user:
        return is_debug, True

    # 检查是否是管理员（JWT 认证）
    is_admin = False
    if current_user:
        # 处理 User 对象或字典类型
        if isinstance(current_user, User):
            is_admin = current_user.is_admin
        elif isinstance(current_user, dict):
            is_admin = current_user.get("is_admin", False)
        else:
            # 尝试从对象属性获取
            is_admin = getattr(current_user, "is_admin", False)

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
        ConfigResponse: 更新结果（包含重启提示）
    """
    is_debug, is_admin = permission
    app_service = get_app_service()

    success, errors, hints = app_service.update_config(
        request.config,
        is_debug=is_debug,
        is_admin=is_admin
    )

    return ConfigResponse(
        success=success,
        errors=errors,
        hints=hints
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


# ============== 日志管理接口 ==============


class LogInfoResponse(BaseModel):
    """日志信息响应模型"""
    log_dir: str
    today_dir: str
    today_files: list
    available_dates: list


class LogContentResponse(BaseModel):
    """日志内容响应模型"""
    date: str
    log_name: str
    lines: int
    total_lines: int
    content: str
    exists: bool


class LogCleanupResponse(BaseModel):
    """日志清理响应模型"""
    success: bool
    deleted_count: int
    keep_days: int


@router.get("/api/app/logs", response_model=LogInfoResponse)
async def get_log_info_endpoint(
    permission: tuple = Depends(check_app_permission)
):
    """
    获取日志系统信息

    Returns:
        LogInfoResponse: 日志目录、文件列表等信息
    """
    app_service = get_app_service()
    log_info = app_service.get_log_info()

    return LogInfoResponse(**log_info)


@router.get("/api/app/logs/content", response_model=LogContentResponse)
async def get_log_content_endpoint(
    date: Optional[str] = Query(None, description="日期 (YYYY-MM-DD)，默认为今天"),
    log_name: str = Query("app", description="日志文件名，如 app, error"),
    lines: int = Query(100, ge=1, le=1000, description="返回行数（1-1000）"),
    level: Optional[str] = Query(None, description="过滤级别 (debug/info/warning/error/critical)"),
    permission: tuple = Depends(check_app_permission)
):
    """
    获取日志内容

    Args:
        date: 日期字符串，格式 YYYY-MM-DD
        log_name: 日志文件名（不含扩展名）
        lines: 返回的行数（从末尾开始）
        level: 过滤日志级别

    Returns:
        LogContentResponse: 日志内容和元数据
    """
    app_service = get_app_service()
    log_content = app_service.get_log_content(
        date=date,
        log_name=log_name,
        lines=lines,
        level=level
    )

    return LogContentResponse(**log_content)


@router.post("/api/app/logs/cleanup", response_model=LogCleanupResponse)
async def cleanup_logs_endpoint(
    keep_days: int = Query(30, ge=1, le=365, description="保留天数（1-365）"),
    permission: tuple = Depends(check_app_permission)
):
    """
    清理旧日志文件

    Args:
        keep_days: 保留最近多少天的日志

    Returns:
        LogCleanupResponse: 清理结果
    """
    is_debug, is_admin = permission
    app_service = get_app_service()

    result = app_service.cleanup_old_logs(
        keep_days=keep_days,
        is_debug=is_debug,
        is_admin=is_admin
    )

    return LogCleanupResponse(**result)


# ============== 数据库迁移接口 ==============


class DatabaseMigrateRequest(BaseModel):
    """数据库迁移请求模型"""
    source_type: str = Field(..., description="源数据库类型 (sqlite/postgresql/mysql)")
    target_type: str = Field(..., description="目标数据库类型 (sqlite/postgresql/mysql)")
    target_url: str = Field(..., description="目标数据库连接URL")


class DatabaseMigrateResponse(BaseModel):
    """数据库迁移响应模型"""
    success: bool
    message: str
    tables: Optional[Dict[str, int]] = Field(None, description="各表迁移记录数")
    export_file: Optional[str] = Field(None, description="导出文件路径（保留时）")


@router.post("/api/app/database/migrate", response_model=DatabaseMigrateResponse)
async def migrate_database_endpoint(
    request: DatabaseMigrateRequest,
    permission: tuple = Depends(check_app_permission)
):
    """
    执行数据库迁移

    将数据从当前数据库迁移到目标数据库。
    迁移过程中会：
    1. 从源数据库导出所有数据到临时文件
    2. 在目标数据库创建表结构
    3. 将数据导入到目标数据库
    4. 清理临时文件

    Args:
        request: 迁移请求，包含源类型、目标类型和目标URL

    Returns:
        DatabaseMigrateResponse: 迁移结果
    """
    is_debug, is_admin = permission
    app_service = get_app_service()

    try:
        result = app_service.migrate_database(
            source_type=request.source_type,
            target_type=request.target_type,
            target_url=request.target_url,
            is_debug=is_debug,
            is_admin=is_admin
        )

        return DatabaseMigrateResponse(
            success=result.get("success", False),
            message=result.get("message", ""),
            tables=result.get("tables"),
            export_file=result.get("export_file")
        )
    except Exception as e:
        return DatabaseMigrateResponse(
            success=False,
            message=f"迁移失败: {str(e)}"
        )


@router.post("/api/app/database/test-connection", response_model=ConfigResponse)
async def test_database_connection_endpoint(
    db_url: str = Body(..., embed=True, description="要测试的数据库URL"),
    permission: tuple = Depends(check_app_permission)
):
    """
    测试数据库连接

    验证数据库URL是否可以正常连接。

    Args:
        db_url: 数据库连接URL

    Returns:
        ConfigResponse: 测试结果
    """
    app_service = get_app_service()

    is_valid, errors = app_service.test_database_connection(db_url)

    return ConfigResponse(
        success=is_valid,
        errors=errors,
        hints=["连接测试成功"] if is_valid else []
    )
