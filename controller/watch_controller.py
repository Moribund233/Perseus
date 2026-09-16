"""
Watch(关注) 控制器层

处理仓库 Watch 相关的 HTTP 请求
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_prefix import get_route_prefix
from models.async_db import get_async_db
from models.repository import Repository
from models.user import User
from api.dependencies import get_current_user
from services import watch_service
from core.exception import NotFoundException
from utils.permission_utils import require_repository_permission
import uuid

router = APIRouter(prefix=get_route_prefix("repositories"), tags=["watches"])


@router.post("/{repo_id}/watch", status_code=201)
async def watch_repository(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    关注仓库

    Args:
        repo_id: 仓库ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 关注操作结果
    """
    return await watch_service.watch_repository(repo_id, current_user.id, db)


@router.delete("/{repo_id}/watch")
async def unwatch_repository(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    取消关注仓库

    Args:
        repo_id: 仓库ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 取消关注操作结果
    """
    return await watch_service.unwatch_repository(repo_id, current_user.id, db)


@router.get("/{repo_id}/watch")
async def get_watch_status(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户对仓库的关注状态

    Args:
        repo_id: 仓库ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 关注状态和数量
    """
    return await watch_service.get_watch_status(repo_id, current_user.id, db)


@router.get("/{repo_id}/watchers")
async def get_watchers(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取仓库的 Watcher 列表

    Args:
        repo_id: 仓库ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        list: Watcher 列表
    """
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")
    if not repo.is_public:
        await require_repository_permission(
            db, repo_id, current_user.id,
            action_description="view watchers"
        )
    return await watch_service.get_watchers(repo_id, db)
