"""
搜索控制器层

处理与代码搜索相关的HTTP请求，调用服务层方法并返回响应
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models import Repository
from models.user import User
from api.dependencies import get_current_user
from services.search_service import SearchService
from utils.git_utils import get_repository_storage_path
from core.exception import NotFoundException

router = APIRouter(prefix=get_route_prefix("repositories"), tags=["search"])


async def _get_repo_path(repo_id: int, db: AsyncSession) -> str:
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
    repo_id: int,
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
