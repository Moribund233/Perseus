"""
仓库 Watch(关注) 服务层

处理仓库关注相关的所有业务逻辑
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from models.repository import Repository
from models.watcher import Watcher
from core.exception import NotFoundException, ConflictException, ValidationException
from utils.db_utils import get_or_404


async def watch_repository(repo_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> dict:
    """
    关注仓库

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 异步数据库会话

    Returns:
        dict: 关注操作结果，包含 watch_count 和 watching 状态

    Raises:
        NotFoundException: 仓库不存在
        ConflictException: 已经关注过该仓库
    """
    repo = await get_or_404(db, Repository, {"id": repo_id}, "Repository not found")

    existing = await db.execute(
        select(Watcher).filter(
            Watcher.repository_id == repo_id,
            Watcher.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictException(detail="Repository already watching", error_code="repository_already_watching")

    watcher = Watcher(repository_id=repo_id, user_id=user_id)
    db.add(watcher)
    repo.watch_count = (repo.watch_count or 0) + 1
    await db.commit()
    await db.refresh(repo)

    return {"watch_count": repo.watch_count, "watching": True}


async def unwatch_repository(repo_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> dict:
    """
    取消关注仓库

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 异步数据库会话

    Returns:
        dict: 取消关注操作结果，包含 watch_count 和 watching 状态

    Raises:
        NotFoundException: 仓库不存在
        ValidationException: 未关注该仓库
    """
    repo = await get_or_404(db, Repository, {"id": repo_id}, "Repository not found")

    result = await db.execute(
        select(Watcher).filter(
            Watcher.repository_id == repo_id,
            Watcher.user_id == user_id,
        )
    )
    watcher = result.scalar_one_or_none()
    if not watcher:
        raise ValidationException(detail="Repository not watching", error_code="repository_not_watching")

    await db.delete(watcher)
    repo.watch_count = max(0, (repo.watch_count or 0) - 1)
    await db.commit()
    await db.refresh(repo)

    return {"watch_count": repo.watch_count, "watching": False}


async def get_watch_status(repo_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> dict:
    """
    获取当前用户对仓库的关注状态

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 异步数据库会话

    Returns:
        dict: 关注状态和数量

    Raises:
        NotFoundException: 仓库不存在
    """
    repo = await get_or_404(db, Repository, {"id": repo_id}, "Repository not found")

    result = await db.execute(
        select(Watcher).filter(
            Watcher.repository_id == repo_id,
            Watcher.user_id == user_id,
        )
    )
    watching = result.scalar_one_or_none() is not None

    return {"watching": watching, "watch_count": repo.watch_count or 0}


async def get_watchers(repo_id: uuid.UUID, db: AsyncSession) -> list[dict]:
    """
    获取仓库的 Watcher 列表

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话

    Returns:
        list: Watcher 列表

    Raises:
        NotFoundException: 仓库不存在
    """
    await get_or_404(db, Repository, {"id": repo_id}, "Repository not found")

    result = await db.execute(
        select(Watcher)
        .filter(Watcher.repository_id == repo_id)
        .order_by(Watcher.created_at.desc())
    )
    watchers = result.scalars().all()

    return [
        {
            "id": w.id,
            "user_id": w.user_id,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in watchers
    ]
