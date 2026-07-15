"""审计日志控制器"""
from fastapi import APIRouter, Depends, Query
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from services import activity_service
import uuid

router = APIRouter(prefix=get_route_prefix("repositories"), tags=["activities"])


@router.get("/{repo_id}/activities", summary="获取仓库审计日志")
async def list_activities(
    repo_id: uuid.UUID,
    entity_type: str = Query(None, description="实体类型过滤"),
    actor_id: uuid.UUID = Query(None, description="操作者过滤"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """获取仓库审计日志，支持按实体类型和操作者过滤"""
    return await activity_service.list_activities(
        repository_id=repo_id, db=db,
        entity_type=entity_type, actor_id=actor_id,
        page=page, limit=limit,
    )
