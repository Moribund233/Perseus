"""
Star 控制器层

处理仓库 Star 相关的 HTTP 请求
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models.repository import Repository
from models.user import User
from api.dependencies import get_current_user
from services import star_service
from core.exception import NotFoundException
from utils.permission_utils import require_repository_permission

router = APIRouter(prefix=get_route_prefix("repositories"), tags=["stars"])


@router.post("/{repo_id}/star", status_code=201)
async def star_repository(
    repo_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Star 仓库

    Args:
        repo_id: 仓库ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: Star 操作结果
    """
    return await star_service.star_repository(repo_id, current_user.id, db)


@router.delete("/{repo_id}/star")
async def unstar_repository(
    repo_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    取消 Star 仓库

    Args:
        repo_id: 仓库ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 取消 Star 操作结果
    """
    return await star_service.unstar_repository(repo_id, current_user.id, db)


@router.get("/{repo_id}/star")
async def get_star_status(
    repo_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户对仓库的 Star 状态

    Args:
        repo_id: 仓库ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: Star 状态和数量
    """
    return await star_service.get_star_status(repo_id, current_user.id, db)


@router.get("/{repo_id}/stargazers")
async def get_stargazers(
    repo_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取仓库的 Stargazer 列表

    Args:
        repo_id: 仓库ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        list: Stargazer 列表
    """
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found")
    if not repo.is_public:
        await require_repository_permission(
            db, repo_id, current_user.id,
            action_description="view stargazers"
        )
    return await star_service.get_stargazers(repo_id, db)
