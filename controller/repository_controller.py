"""
仓库控制器层

处理与仓库相关的HTTP请求，调用服务层方法并返回响应
"""
from fastapi import APIRouter, Depends, Request, status, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models.user import User
from api.dependencies import get_current_user, get_current_admin_user
from utils.permission_utils import (
    require_repository_permission,
    require_repository_owner_or_admin
)
from core.exception import AuthorizationException

from services.repository_service import (
    get_repositories as service_get_repositories,
    get_repository_by_id as service_get_repository_by_id,
    get_repositories_by_user as service_get_repositories_by_user,
    create_repository as service_create_repository,
    update_repository as service_update_repository,
    delete_repository as service_delete_repository,
    get_public_repositories as service_get_public_repositories,
    check_repository_access as service_check_repository_access,
    archive_repository as service_archive_repository,
    unarchive_repository as service_unarchive_repository,
)

# 创建路由实例
router = APIRouter(prefix=get_route_prefix("repositories"), tags=["repositories"])

# 安全方案
security = HTTPBearer(auto_error=False)


@router.get("", summary="获取所有仓库")
async def get_repositories(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取所有仓库（需要认证）

    Args:
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        list[Repository]: 仓库列表
    """
    return await service_get_repositories(db)


@router.get("/public")
async def get_public_repositories(db: AsyncSession = Depends(get_async_db)):
    """
    获取所有公开仓库

    Args:
        db: 数据库会话

    Returns:
        list[Repository]: 公开仓库列表
    """
    return await service_get_public_repositories(db)


@router.get("/user/{user_id}")
async def get_repositories_by_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    根据用户ID获取仓库列表（需要认证）

    Args:
        user_id: 用户ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        list[Repository]: 用户的仓库列表
    """
    return await service_get_repositories_by_user(user_id, db)


@router.get("/{repo_id}")
async def get_repository(
    repo_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    根据ID获取仓库（需要认证）

    Args:
        repo_id: 仓库ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        Repository: 仓库信息

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    return await service_get_repository_by_id(repo_id, db)


@router.post("", summary="创建新仓库")
async def create_repository(
    request: Request,
    repo: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新仓库（需要认证）

    路径自动生成，格式为: {username}/{repo_name}
    符合 Git HTTP 标准 URL 格式

    Args:
        request: HTTP请求对象（用于速率限制）
        repo: 仓库信息（包含 name, description, is_public, default_branch 等）
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        Repository: 创建的仓库信息

    Raises:
        ValidationException: 请求参数不完整时抛出422异常
        ConflictException: 仓库路径已存在时抛出409异常
    """
    # 验证必要参数
    if "name" not in repo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Repository name is required"
        )

    # 设置当前用户为仓库所有者
    repo["owner_id"] = current_user.id

    # 自动生成路径，格式: {username}/{repo_name}
    # 这是 Git HTTP 标准 URL 格式，如: admin/test-repo
    repo["path"] = f"{current_user.username}/{repo['name']}"

    return await service_create_repository(repo, db)


@router.put("/{repo_id}")
async def update_repository(
    request: Request,
    repo_id: int,
    repo: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新仓库信息（需要认证）

    Args:
        request: HTTP请求对象（用于速率限制）
        repo_id: 仓库ID
        repo: 更新的仓库信息
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        Repository: 更新后的仓库信息

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
        AuthorizationException: 无权限时抛出403异常
    """
    # 使用工具函数检查权限（需要所有者或管理员权限）
    await require_repository_owner_or_admin(
        db, repo_id, current_user.id, "update this repository"
    )
    return await service_update_repository(repo_id, repo, db)


@router.delete("/{repo_id}")
async def delete_repository(
    request: Request,
    repo_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除仓库（需要认证）

    Args:
        request: HTTP请求对象（用于速率限制）
        repo_id: 仓库ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 删除成功消息

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
        AuthorizationException: 无权限时抛出403异常
    """
    # 使用工具函数检查权限（只有所有者可以删除）
    await require_repository_permission(
        db, repo_id, current_user.id, ["owner"], "delete this repository"
    )
    return await service_delete_repository(repo_id, db)


@router.get("/{repo_id}/access")
async def check_repository_access(
    repo_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    检查用户对仓库的访问权限（需要认证）

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 访问权限信息

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    has_access = await service_check_repository_access(repo_id, user_id, db)
    return {"has_access": has_access}


@router.post("/{repo_id}/archive", summary="归档仓库")
async def archive_repository(
    repo_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    归档仓库（需要认证）

    Args:
        repo_id: 仓库ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        Repository: 归档后的仓库信息

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
        AuthorizationException: 无权限时抛出403异常
    """
    await require_repository_owner_or_admin(
        db, repo_id, current_user.id, "archive this repository"
    )
    return await service_archive_repository(repo_id, db)


@router.post("/{repo_id}/unarchive", summary="取消归档仓库")
async def unarchive_repository(
    repo_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    取消归档仓库（需要认证）

    Args:
        repo_id: 仓库ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        Repository: 取消归档后的仓库信息

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
        AuthorizationException: 无权限时抛出403异常
    """
    await require_repository_owner_or_admin(
        db, repo_id, current_user.id, "unarchive this repository"
    )
    return await service_unarchive_repository(repo_id, db)
