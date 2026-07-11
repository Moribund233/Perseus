"""Pull Request 活动日志服务模块"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.pr_activity import PRActivity


async def record_activity(pr_id: int, actor_id: int, action: str,
                          details: str = None, db: AsyncSession = None) -> dict:
    """
    记录 PR 活动

    Args:
        pr_id: PR ID
        actor_id: 操作者 ID
        action: 动作类型 (created/reviewed/merged/closed/commented)
        details: 可选详情
        db: 异步数据库会话

    Returns:
        dict: 活动记录
    """
    activity = PRActivity(
        pull_request_id=pr_id, actor_id=actor_id, action=action, details=details,
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return {
        "id": activity.id,
        "action": activity.action,
        "details": activity.details,
        "actor_id": activity.actor_id,
        "created_at": activity.created_at.isoformat() if activity.created_at else None,
    }


async def list_activities(pr_id: int, db: AsyncSession) -> list[dict]:
    """
    获取 PR 活动日志

    Args:
        pr_id: PR ID
        db: 异步数据库会话

    Returns:
        list[dict]: 活动列表（按时间倒序）
    """
    result = await db.execute(
        select(PRActivity)
        .filter(PRActivity.pull_request_id == pr_id)
        .order_by(PRActivity.created_at.desc(), PRActivity.id.desc())
    )
    return [
        {
            "id": a.id, "action": a.action, "details": a.details,
            "actor_id": a.actor_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in result.scalars().all()
    ]
