"""
仓库统计服务模块

提供仓库的聚合统计功能
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from models.repository import Repository
from models.pull_request import PullRequest, PRReview
from models.issue import Issue
from models.stargazer import Stargazer
from models.repository_member import RepositoryMember
from utils.db_utils import get_or_404


async def get_repo_stats(repo_id: uuid.UUID, db: AsyncSession) -> dict:
    """
    获取仓库聚合统计

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话

    Returns:
        dict: 包含 pr_count, issue_count, review_count, star_count, member_count
    """
    await get_or_404(db, Repository, {"id": repo_id}, "Repository not found")

    pr_count = (await db.execute(
        select(func.count()).select_from(PullRequest).filter(PullRequest.repository_id == repo_id)
    )).scalar()

    issue_count = (await db.execute(
        select(func.count()).select_from(Issue).filter(Issue.repository_id == repo_id)
    )).scalar()

    review_count = (await db.execute(
        select(func.count()).select_from(PRReview)
        .join(PullRequest)
        .filter(PullRequest.repository_id == repo_id)
    )).scalar()

    star_count = (await db.execute(
        select(func.count()).select_from(Stargazer).filter(Stargazer.repository_id == repo_id)
    )).scalar()

    member_count = (await db.execute(
        select(func.count()).select_from(RepositoryMember)
        .filter(RepositoryMember.repository_id == repo_id)
    )).scalar()

    return {
        "pr_count": pr_count or 0,
        "issue_count": issue_count or 0,
        "review_count": review_count or 0,
        "star_count": star_count or 0,
        "member_count": member_count or 0,
    }