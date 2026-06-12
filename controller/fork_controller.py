"""
Fork 控制器层

处理仓库 Fork 相关的 HTTP 请求
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.async_db import get_async_db
from models.repository import Repository
from models.user import User
from api.dependencies import get_current_user
from core.exception import NotFoundException
from services import fork_service

# 创建路由实例
router = APIRouter(prefix="/api/v1/repositories", tags=["forks"])


class ForkCreateRequest(BaseModel):
    """创建 Fork 请求体"""
    name: Optional[str] = Field(None, max_length=255, description="Fork 仓库名称（默认为源仓库名称）")
    description: Optional[str] = Field(None, description="Fork 仓库描述")
    is_public: Optional[bool] = Field(None, description="是否公开（默认为源仓库设置）")


async def _get_repo(repo_id: int, db: AsyncSession) -> Repository:
    """
    获取仓库实例

    Args:
        repo_id: 仓库ID
        db: 数据库会话

    Returns:
        Repository: 仓库实例

    Raises:
        NotFoundException: 仓库不存在
    """
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found")
    return repo


@router.post("/{repo_id}/forks", status_code=201)
async def fork_repository(
    repo_id: int,
    data: ForkCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
     Fork 仓库

    创建源仓库的副本，包括 Git 仓库和所有数据

    Args:
        repo_id: 源仓库ID
        data: Fork 创建数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 创建的 Fork 仓库信息
    """
    # 验证源仓库存在
    await _get_repo(repo_id, db)

    return await fork_service.fork_repository(
        db=db,
        source_repository_id=repo_id,
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        is_public=data.is_public
    )


@router.get("/{repo_id}/forks")
async def list_repository_forks(
    repo_id: int,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取仓库的 Fork 列表

    Args:
        repo_id: 仓库ID
        page: 页码
        limit: 每页数量
        db: 数据库会话

    Returns:
        dict: Fork 列表和分页信息
    """
    await _get_repo(repo_id, db)
    return await fork_service.get_repository_forks(
        db=db,
        repository_id=repo_id,
        page=page,
        limit=limit
    )


@router.get("/{repo_id}/forks/source")
async def get_fork_source(
    repo_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取 Fork 的源仓库

    Args:
        repo_id: 仓库ID
        db: 数据库会话

    Returns:
        dict: 源仓库信息，如果不是 Fork 则返回 None
    """
    repo = await _get_repo(repo_id, db)
    return await fork_service.get_fork_source(
        db=db,
        repository_id=repo_id
    )


@router.post("/{repo_id}/forks/sync")
async def sync_fork(
    repo_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    同步 Fork 仓库

    从源仓库拉取最新更改

    Args:
        repo_id: Fork 仓库ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 同步结果
    """
    await _get_repo(repo_id, db)
    return await fork_service.sync_fork(
        db=db,
        repository_id=repo_id,
        user_id=current_user.id
    )
