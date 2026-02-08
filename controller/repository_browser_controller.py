"""
仓库代码浏览控制器层

处理代码浏览相关的 HTTP 请求：
- 文件树浏览
- 文件内容查看
- 提交历史
- 代码对比
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from models.db import get_db
from models import Repository
from services.repository_browser_service import (
    get_tree_entries,
    get_blob_content,
    get_commits,
    get_diff,
    RepositoryBrowserError
)
from services.repository_service import get_repository_by_id
from client.utils.git_utils import get_repository_storage_path
from exception import NotFoundException

# 创建路由实例
router = APIRouter(prefix="/api/repositories", tags=["repository-browser"])


def _get_repo_path(repo_id: int, db: Session) -> str:
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
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise NotFoundException(detail="Repository not found")
    
    return get_repository_storage_path(repo.path)


@router.get("/{repo_id}/tree")
async def get_repository_tree(
    repo_id: int,
    ref: str = Query("HEAD", description="分支名或提交SHA"),
    path: str = Query("", description="子目录路径"),
    db: Session = Depends(get_db)
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
    try:
        repo_path = _get_repo_path(repo_id, db)
        result = get_tree_entries(repo_path, ref=ref, path=path)
        return result
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    except RepositoryBrowserError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tree: {e}"
        )


@router.get("/{repo_id}/blob")
async def get_repository_blob(
    repo_id: int,
    path: str = Query(..., description="文件路径"),
    ref: str = Query("HEAD", description="分支名或提交SHA"),
    db: Session = Depends(get_db)
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
    try:
        repo_path = _get_repo_path(repo_id, db)
        result = get_blob_content(repo_path, ref=ref, path=path)
        return result
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    except RepositoryBrowserError as e:
        error_msg = str(e).lower()
        if "is a directory" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get blob: {e}"
        )


@router.get("/{repo_id}/commits")
async def get_repository_commits(
    repo_id: int,
    ref: str = Query("HEAD", description="分支名"),
    path: Optional[str] = Query(None, description="特定文件路径"),
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(30, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
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
    try:
        repo_path = _get_repo_path(repo_id, db)
        result = get_commits(repo_path, ref=ref, path=path, page=page, per_page=per_page)
        return result
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    except RepositoryBrowserError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get commits: {e}"
        )


@router.get("/{repo_id}/diff")
async def get_repository_diff(
    repo_id: int,
    head: str = Query(..., description="对比提交SHA"),
    base: Optional[str] = Query(None, description="基准提交SHA"),
    path: Optional[str] = Query(None, description="特定文件路径"),
    db: Session = Depends(get_db)
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
    try:
        repo_path = _get_repo_path(repo_id, db)
        result = get_diff(repo_path, base=base, head=head, path=path)
        return result
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    except RepositoryBrowserError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get diff: {e}"
        )
