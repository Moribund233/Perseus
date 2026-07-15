"""
搜索控制器层

处理与代码搜索相关的HTTP请求，调用服务层方法并返回响应
"""
import asyncio
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models import Repository
from models.user import User
from api.dependencies import get_current_user
from services.search_service import SearchService
from services.repository_service import get_accessible_repository_ids
from utils.git_utils import get_repository_storage_path
from core.exception import NotFoundException
import uuid

router = APIRouter(prefix=get_route_prefix("repositories"), tags=["search"])
global_search_router = APIRouter(prefix="/api/v1/search", tags=["search"])


async def _get_repo_path(repo_id: uuid.UUID, db: AsyncSession) -> str:
    """
    获取仓库物理路径

    Args:
        repo_id: 仓库ID
        db: 数据库会话

    Returns:
        str: 仓库物理路径

    Raises:
        NotFoundException: 仓库不存在
    """
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found")

    return get_repository_storage_path(repo.path)


@router.get("/{repo_id}/search")
async def search_code(
    repo_id: uuid.UUID,
    q: str = Query(..., description="搜索关键词"),
    path: str = Query(None, description="限制搜索目录"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    搜索仓库代码

    Args:
        repo_id: 仓库ID
        q: 搜索关键词
        path: 限制搜索目录
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 搜索结果
    """
    repo_path = await _get_repo_path(repo_id, db)
    search_service = SearchService()
    return search_service.search_code(
        repo_path=repo_path,
        query=q,
        path=path,
    )


@global_search_router.get("/code")
async def global_search_code(
    q: str = Query(..., description="搜索关键词"),
    path: str = Query(None, description="限制搜索目录"),
    max_results: int = Query(100, ge=1, le=500, description="最大返回结果数"),
    per_repo_max: int = Query(50, ge=1, le=200, description="每个仓库最大结果数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    跨仓库代码搜索

    在用户有权限访问的所有仓库中搜索代码，结果按仓库聚合。

    Args:
        q: 搜索关键词
        path: 限制搜索目录
        max_results: 最大返回结果总数
        per_repo_max: 单个仓库最大结果数
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 搜索结果（按仓库聚合）
    """
    accessible_ids = await get_accessible_repository_ids(db, current_user.id)

    if not accessible_ids:
        return {
            "query": q,
            "repositories": [],
            "total_count": 0,
            "truncated": False,
        }

    result = await db.execute(
        select(Repository).filter(Repository.id.in_(accessible_ids))
    )
    repos = result.scalars().all()

    search_service = SearchService()

    async def search_one(repo: Repository):
        repo_path = get_repository_storage_path(repo.path)
        try:
            response = await asyncio.to_thread(
                search_service.search_code,
                repo_path=repo_path,
                query=q,
                path=path,
                max_results=per_repo_max,
            )
        except Exception:
            return None
        if not response.results:
            return None
        return {
            "repository_id": repo.id,
            "repository_name": repo.name,
            "repository_path": repo.path,
            "results": [
                {"file": r.file, "line": r.line, "content": r.content}
                for r in response.results
            ],
            "total_count": response.total_count,
            "truncated": response.truncated,
        }

    repo_results = await asyncio.gather(*[search_one(repo) for repo in repos])
    aggregated = [r for r in repo_results if r is not None]

    # 按总结果数截断
    total_count = sum(r["total_count"] for r in aggregated)
    truncated = total_count > max_results
    if total_count > max_results:
        remaining = max_results
        limited = []
        for r in aggregated:
            if remaining <= 0:
                break
            results = r["results"]
            take = min(len(results), remaining)
            limited.append({
                **r,
                "results": results[:take],
                "total_count": take,
                "truncated": take < len(results) or r["truncated"],
            })
            remaining -= take
        aggregated = limited

    return {
        "query": q,
        "repositories": aggregated,
        "total_count": total_count,
        "truncated": truncated,
    }
