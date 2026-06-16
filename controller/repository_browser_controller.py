"""
仓库代码浏览控制器层

处理代码浏览相关的 HTTP 请求：
- 文件树浏览
- 文件内容查看
- 提交历史
- 代码对比
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models import Repository
from services.repository_browser_service import (
    get_tree_entries,
    get_blob_content,
    get_commits,
    get_diff,
    get_readme_content,
    get_file_symbols,
    detect_file_language
)
from utils.git_utils import get_repository_storage_path
from core.exception import NotFoundException

# 创建路由实例
router = APIRouter(prefix=get_route_prefix("repository_browser"), tags=["repository-browser"])


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


@router.get("/{repo_id}/tree")
async def get_repository_tree(
    repo_id: int,
    ref: str = Query("HEAD", description="分支名或提交SHA"),
    path: str = Query("", description="子目录路径"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取仓库文件树

    Args:
        repo_id: 仓库ID
        ref: 分支名或提交SHA，默认 HEAD
        path: 子目录路径，默认根目录
        db: 数据库会话

    Returns:
        dict: 文件树数据

    Raises:
        HTTPException: 仓库或路径不存在
    """
    repo_path = await _get_repo_path(repo_id, db)
    return get_tree_entries(repo_path, ref=ref, path=path)


@router.get("/{repo_id}/blob")
async def get_repository_blob(
    repo_id: int,
    path: str = Query(..., description="文件路径"),
    ref: str = Query("HEAD", description="分支名或提交SHA"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取文件内容

    Args:
        repo_id: 仓库ID
        path: 文件路径（必填）
        ref: 分支名或提交SHA，默认 HEAD
        db: 数据库会话

    Returns:
        dict: 文件内容数据

    Raises:
        HTTPException: 文件不存在或是目录
    """
    repo_path = await _get_repo_path(repo_id, db)
    return get_blob_content(repo_path, ref=ref, path=path)


@router.get("/{repo_id}/commits")
async def get_repository_commits(
    repo_id: int,
    ref: str = Query("HEAD", description="分支名"),
    path: Optional[str] = Query(None, description="特定文件路径"),
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(30, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取提交历史

    Args:
        repo_id: 仓库ID
        ref: 分支名，默认 HEAD
        path: 特定文件路径，None 表示所有提交
        page: 页码，默认 1
        per_page: 每页数量，默认 30
        db: 数据库会话

    Returns:
        dict: 提交历史数据

    Raises:
        HTTPException: 仓库不存在
    """
    repo_path = await _get_repo_path(repo_id, db)
    return await get_commits(repo_path, ref=ref, path=path, page=page, per_page=per_page)


@router.get("/{repo_id}/diff")
async def get_repository_diff(
    repo_id: int,
    head: str = Query(..., description="对比提交SHA"),
    base: Optional[str] = Query(None, description="基准提交SHA"),
    path: Optional[str] = Query(None, description="特定文件路径"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取代码差异

    Args:
        repo_id: 仓库ID
        head: 对比提交SHA（必填）
        base: 基准提交SHA，None 表示与空树对比
        path: 特定文件路径，None 表示所有文件
        db: 数据库会话

    Returns:
        dict: 差异数据

    Raises:
        HTTPException: 提交不存在
    """
    repo_path = await _get_repo_path(repo_id, db)
    return get_diff(repo_path, base=base, head=head, path=path)


@router.get("/{repo_id}/readme")
async def get_repository_readme(
    repo_id: int,
    ref: str = Query("HEAD", description="分支名或提交SHA"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取 README 文件内容

    自动查找 README.md, README.rst, README.txt, README 等常见 README 文件

    Args:
        repo_id: 仓库ID
        ref: 分支名或提交SHA，默认 HEAD
        db: 数据库会话

    Returns:
        dict: README 文件信息
        {
            "found": bool,
            "filename": str or None,
            "content": str or None,
            "language": str,
            "encoding": str
        }
    """
    repo_path = await _get_repo_path(repo_id, db)
    return await get_readme_content(repo_path, ref=ref)


@router.get("/{repo_id}/symbols")
async def get_repository_file_symbols(
    repo_id: int,
    path: str = Query(..., description="文件路径"),
    ref: str = Query("HEAD", description="分支名或提交SHA"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取文件符号（函数、类、变量等）

    目前支持 Python 文件的符号提取，其他语言返回空列表

    Args:
        repo_id: 仓库ID
        path: 文件路径（必填）
        ref: 分支名或提交SHA，默认 HEAD
        db: 数据库会话

    Returns:
        dict: 符号列表
        {
            "path": str,
            "language": str,
            "symbols": [
                {
                    "name": str,
                    "type": str,
                    "line": int
                }
            ]
        }
    """
    repo_path = await _get_repo_path(repo_id, db)
    return await get_file_symbols(repo_path, ref=ref, path=path)


@router.get("/{repo_id}/language")
async def detect_repository_file_language(
    repo_id: int,
    path: str = Query(..., description="文件路径"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    检测文件语言类型

    Args:
        repo_id: 仓库ID
        path: 文件路径（必填）
        db: 数据库会话

    Returns:
        dict: 语言信息
        {
            "path": str,
            "language": str
        }
    """
    # 验证仓库存在
    await _get_repo_path(repo_id, db)

    language = detect_file_language(path)
    return {
        "path": path,
        "language": language
    }
