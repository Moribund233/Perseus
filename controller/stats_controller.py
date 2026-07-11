"""
仓库统计控制器

处理仓库聚合统计的HTTP请求
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from services import stats_service

router = APIRouter(prefix=get_route_prefix("repositories"), tags=["repository-stats"])


@router.get("/{repo_id}/stats", summary="获取仓库统计")
async def get_repo_stats(
    repo_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """获取仓库聚合统计"""
    return await stats_service.get_repo_stats(repo_id, db)