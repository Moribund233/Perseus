"""
调试控制器

提供调试/开发用的管理接口：
- debug/initdb: 重置数据库（删除并重新创建所有表）
- debug/initconf: 重置配置文件（删除并重新生成默认配置）

安全要求：
- 仅在调试模式下可用（app.debug=true）
- 需要本地认证（Local Auth）或管理员用户认证
- 这些接口具有破坏性，谨慎使用
"""
import os
import shutil
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.config import get_config
from api.dependencies import get_current_user
from models.user import User
from services.database_manager import DatabaseResetManager
from utils.logging import get_named_logger

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])
logger = get_named_logger("debug")


# ============== Pydantic 模型 ==============


class InitDbResponse(BaseModel):
    """初始化数据库响应模型"""
    success: bool
    message: str
    details: dict = Field(default_factory=dict)


class InitConfResponse(BaseModel):
    """初始化配置文件响应模型"""
    success: bool
    message: str
    config_path: str
    backup_path: Optional[str] = None


class DebugStatusResponse(BaseModel):
    """调试状态响应模型"""
    debug_mode: bool
    config_path: str
    config_exists: bool
    database_url: str
    database_type: str
    environment: dict = Field(default_factory=dict, description="环境变量信息")
    stress_test_mode: bool = Field(default=False, description="是否处于压力测试模式")


# ============== 依赖函数 ==============


async def require_debug_mode():
    """
    检查是否处于调试模式

    Raises:
        HTTPException: 非调试模式下抛出 403 错误
    """
    config = get_config()
    if not config.app.debug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoints are only available in debug mode"
        )


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    要求 JWT 管理员权限

    复用 api/dependencies.py 的 get_current_user 进行基础认证，
    然后额外检查管理员权限。

    Args:
        current_user: 当前认证用户（由 get_current_user 注入）

    Returns:
        User: 认证通过的管理员用户

    Raises:
        HTTPException: 权限不足时抛出 403 错误
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required",
        )
    return current_user


# ============== API 端点 ==============


@router.get("/status", response_model=DebugStatusResponse)
async def debug_status(
    _: User = Depends(require_admin),
    __: None = Depends(require_debug_mode)
):
    """
    获取调试状态信息

    显示当前调试模式状态、配置文件状态、环境变量等信息

    Returns:
        DebugStatusResponse: 调试状态信息
    """
    config = get_config()
    config_path = "config.toml"

    # 收集环境变量信息（排除敏感信息）
    env_info = {}
    sensitive_keys = {'password', 'secret', 'token', 'key', 'jwt', 'auth'}

    for key, value in os.environ.items():
        # 只包含 PERSEUS_ 开头的环境变量
        if key.startswith('PERSEUS_'):
            # 检查是否是敏感信息
            key_lower = key.lower()
            is_sensitive = any(s in key_lower for s in sensitive_keys)

            if is_sensitive:
                env_info[key] = "***masked***"
            else:
                env_info[key] = value

    # 检查是否处于压力测试模式
    stress_test_mode = os.environ.get('PERSEUS_STRESS_TEST', 'false').lower() == 'true'

    return DebugStatusResponse(
        debug_mode=config.app.debug,
        config_path=config_path,
        config_exists=os.path.exists(config_path),
        database_url=config.database._mask_url(config.database.url),
        database_type=config.database.db_type,
        environment=env_info,
        stress_test_mode=stress_test_mode
    )


@router.post("/initdb", response_model=InitDbResponse)
async def init_database(
    force: bool = False,
    create_test_data: bool = True,
    _: None = Depends(require_debug_mode),
    current_user: User = Depends(require_admin)
):
    """
    重置数据库

    删除所有表并重新创建，可选创建测试数据

    Args:
        force: 是否强制重置（跳过确认提示，始终为 true）
        create_test_data: 是否创建测试数据

    Returns:
        InitDbResponse: 操作结果

    Raises:
        HTTPException: 非调试模式或权限不足时
    """
    try:
        # 使用 DatabaseResetManager 执行重置
        manager = DatabaseResetManager()
        result = await manager.reset_database(
            create_test_data=create_test_data,
            preserve_config=True
        )

        return InitDbResponse(
            success=True,
            message=f"数据库重置成功 ({result['database_type']})",
            details=result
        )

    except Exception as e:
        logger.error(f"数据库重置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database reset failed: {str(e)}"
        )


@router.post("/initconf", response_model=InitConfResponse)
async def init_config(
    force: bool = False,
    backup: bool = True,
    _: None = Depends(require_debug_mode),
    current_user: User = Depends(require_admin)
):
    """
    重置配置文件

    删除当前配置文件并从 config.example.toml 恢复

    Args:
        force: 是否强制重置（跳过确认提示，始终为 true）
        backup: 是否备份原配置文件

    Returns:
        InitConfResponse: 操作结果

    Raises:
        HTTPException: 非调试模式或权限不足时
    """
    config_path = "config.toml"
    backup_path = None

    try:
        # 如果配置文件存在，进行备份
        if os.path.exists(config_path) and backup:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"config.toml.backup.{timestamp}"
            shutil.copy2(config_path, backup_path)
            logger.info(f"配置文件已备份到: {backup_path}")

        # 删除原配置文件
        if os.path.exists(config_path):
            os.remove(config_path)
            logger.info(f"已删除原配置文件: {config_path}")

        # 重置配置管理器单例
        reset_module_config_manager()

        # 重新初始化配置管理器（会自动生成默认配置）
        ConfigManager(config_path)

        logger.info("配置文件已重置为默认值")

        return InitConfResponse(
            success=True,
            message="配置文件重置成功",
            config_path=config_path,
            backup_path=backup_path
        )

    except Exception as e:
        logger.error(f"配置文件重置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Config reset failed: {str(e)}"
        )
