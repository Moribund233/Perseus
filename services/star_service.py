"""
仓库 Star 服务层

处理仓库 Star 相关的所有业务逻辑
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from models.stargazer import Stargazer
from core.exception import NotFoundException, ConflictException, ValidationException
from utils.db_utils import get_or_404


async def star_repository(repo_id: int, user_id: int, db: AsyncSession) -> dict:
    """
    Star 仓库

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 异步数据库会话

    Returns:
        dict: Star 操作结果，包含 star_count 和 starred 状态

    Raises:
        NotFoundException: 仓库不存在
        ConflictException: 已经 Star 过该仓库
    """
    repo = await get_or_404(db, Repository, {"id": repo_id}, "Repository not found")

    existing = await db.execute(
        select(Stargazer).filter(
            Stargazer.repository_id == repo_id,
            Stargazer.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictException(detail="Repository already starred")

    stargazer = Stargazer(repository_id=repo_id, user_id=user_id)
    db.add(stargazer)
    repo.star_count = (repo.star_count or 0) + 1
    await db.commit()
    await db.refresh(repo)

    return {"star_count": repo.star_count, "starred": True}


async def unstar_repository(repo_id: int, user_id: int, db: AsyncSession) -> dict:
    """
    取消 Star 仓库

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 异步数据库会话

    Returns:
        dict: 取消 Star 操作结果，包含 star_count 和 starred 状态

    Raises:
        NotFoundException: 仓库不存在
        ValidationException: 未 Star 该仓库
    """
    repo = await get_or_404(db, Repository, {"id": repo_id}, "Repository not found")

    result = await db.execute(
        select(Stargazer).filter(
            Stargazer.repository_id == repo_id,
            Stargazer.user_id == user_id,
        )
    )
    stargazer = result.scalar_one_or_none()
    if not stargazer:
        raise ValidationException(detail="Repository not starred")

    await db.delete(stargazer)
    repo.star_count = max(0, (repo.star_count or 0) - 1)
    await db.commit()
    await db.refresh(repo)

    return {"star_count": repo.star_count, "starred": False}


async def get_star_status(repo_id: int, user_id: int, db: AsyncSession) -> dict:
    """
    获取当前用户对仓库的 Star 状态

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 异步数据库会话

    Returns:
        dict: Star 状态和数量

    Raises:
        NotFoundException: 仓库不存在
    """
    repo = await get_or_404(db, Repository, {"id": repo_id}, "Repository not found")

    result = await db.execute(
        select(Stargazer).filter(
            Stargazer.repository_id == repo_id,
            Stargazer.user_id == user_id,
        )
    )
    starred = result.scalar_one_or_none() is not None

    return {"starred": starred, "star_count": repo.star_count}


async def get_stargazers(repo_id: int, db: AsyncSession) -> list[dict]:
    """
    获取仓库的 Stargazer 列表

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话

    Returns:
        list: Stargazer 列表

    Raises:
        NotFoundException: 仓库不存在
    """
    await get_or_404(db, Repository, {"id": repo_id}, "Repository not found")

    result = await db.execute(
        select(Stargazer)
        .filter(Stargazer.repository_id == repo_id)
        .order_by(Stargazer.created_at.desc())
    )
    stargazers = result.scalars().all()

    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in stargazers
    ]
