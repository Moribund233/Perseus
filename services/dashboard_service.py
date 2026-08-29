"""
用户 Dashboard 聚合服务

为当前登录用户提供跨仓库的统计、动态、最近 PR/Issue 聚合数据。
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from models.pull_request import PullRequest
from models.issue import Issue
from models.activity import Activity
from services.repository_service import get_accessible_repository_ids
from utils.response_builder import build_pr_response, build_issue_response

CONTRIBUTION_DAYS = 30


async def get_user_dashboard(db: AsyncSession, user_id: uuid.UUID, limit: int = 10) -> dict:
    """
    获取当前用户的 Dashboard 聚合数据

    Args:
        db: 异步数据库会话
        user_id: 当前用户ID
        limit: 最近活动/PR/Issue 返回条数

    Returns:
        dict: Dashboard 数据
    """
    accessible_ids = await get_accessible_repository_ids(db, user_id)

    # 可访问仓库总数
    repo_count = len(accessible_ids)

    # 跨仓库未关闭 PR 数
    open_pr_count = 0
    if accessible_ids:
        open_pr_count = (await db.execute(
            select(func.count())
            .select_from(PullRequest)
            .filter(
                PullRequest.repository_id.in_(accessible_ids),
                PullRequest.status == "open"
            )
        )).scalar() or 0

    # 跨仓库未关闭 Issue 数
    open_issue_count = 0
    if accessible_ids:
        open_issue_count = (await db.execute(
            select(func.count())
            .select_from(Issue)
            .filter(
                Issue.repository_id.in_(accessible_ids),
                Issue.status == "open"
            )
        )).scalar() or 0

    # 最近活动流（用户可访问仓库内的所有活动）
    recent_activities = []
    if accessible_ids:
        result = await db.execute(
            select(Activity)
            .options(selectinload(Activity.actor))
            .filter(Activity.repository_id.in_(accessible_ids))
            .order_by(Activity.created_at.desc())
            .limit(limit)
        )
        activities = result.scalars().all()
        recent_activities = [
            {
                "id": a.id,
                "repository_id": a.repository_id,
                "actor_id": a.actor_id,
                "actor_username": a.actor.username if a.actor else None,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "action": a.action,
                "details": a.details,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in activities
        ]

    # 最近 30 天按日活动聚合（贡献图真实数据）
    contributions_by_day = {}
    if accessible_ids:
        since = datetime.now() - timedelta(days=CONTRIBUTION_DAYS)
        day_expr = func.date(Activity.created_at)
        rows = (await db.execute(
            select(day_expr, func.count())
            .filter(
                Activity.repository_id.in_(accessible_ids),
                Activity.created_at >= since,
            )
            .group_by(day_expr)
        )).all()
        contributions_by_day = {str(day): count for day, count in rows}

    # 我最近创建的 PR
    recent_prs = []
    if accessible_ids:
        result = await db.execute(
            select(PullRequest)
        .options(
            selectinload(PullRequest.author),
            selectinload(PullRequest.merger),
            selectinload(PullRequest.repository),
            selectinload(PullRequest.pr_labels)
        )
        .filter(
            PullRequest.repository_id.in_(accessible_ids),
            PullRequest.author_id == user_id
        )
            .order_by(PullRequest.created_at.desc())
            .limit(limit)
        )
        recent_prs = [build_pr_response(pr) for pr in result.scalars().all()]

    # 我创建或指派给我的 Issue
    recent_issues = []
    if accessible_ids:
        result = await db.execute(
            select(Issue)
            .options(
                selectinload(Issue.author),
                selectinload(Issue.assignee),
                selectinload(Issue.closer),
                selectinload(Issue.repository),
                selectinload(Issue.labels)
            )
            .filter(
                Issue.repository_id.in_(accessible_ids),
                (Issue.author_id == user_id) | (Issue.assignee_id == user_id)
            )
            .order_by(Issue.created_at.desc())
            .limit(limit)
        )
        recent_issues = [build_issue_response(issue) for issue in result.scalars().all()]

    return {
        "repo_count": repo_count,
        "open_prs": open_pr_count,
        "open_issues": open_issue_count,
        "recent_activities": recent_activities,
        "recent_prs": recent_prs,
        "recent_issues": recent_issues,
        "contributions_by_day": contributions_by_day,
    }
