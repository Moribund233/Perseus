"""通用审计日志服务模块"""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.activity import Activity
from utils.db_utils import paginate
from utils.response_builder import build_pagination_response


async def record_activity(
    repository_id: uuid.UUID, actor_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID,
    action: str, details: str = None, db: AsyncSession = None,
) -> dict:
    """记录审计日志"""
    activity = Activity(
        repository_id=repository_id, actor_id=actor_id,
        entity_type=entity_type, entity_id=entity_id,
        action=action, details=details,
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return {
        "id": activity.id,
        "repository_id": activity.repository_id,
        "actor_id": activity.actor_id,
        "entity_type": activity.entity_type,
        "entity_id": activity.entity_id,
        "action": activity.action,
        "details": activity.details,
        "created_at": activity.created_at.isoformat() if activity.created_at else None,
    }


async def list_activities(
    repository_id: uuid.UUID, db: AsyncSession,
    entity_type: str = None, actor_id: uuid.UUID = None,
    page: int = 1, limit: int = 20,
) -> dict:
    """查询审计日志"""
    stmt = select(Activity).filter(Activity.repository_id == repository_id)
    if entity_type:
        stmt = stmt.filter(Activity.entity_type == entity_type)
    if actor_id:
        stmt = stmt.filter(Activity.actor_id == actor_id)
    stmt = stmt.order_by(Activity.created_at.desc())

    activities, total = await paginate(db, stmt, page=page, limit=limit)
    items = [
        {
            "id": a.id, "repository_id": a.repository_id, "actor_id": a.actor_id,
            "entity_type": a.entity_type, "entity_id": a.entity_id,
            "action": a.action, "details": a.details,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in activities
    ]
    return build_pagination_response(items, total, page, limit)
