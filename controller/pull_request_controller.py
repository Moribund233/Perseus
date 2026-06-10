"""
Pull Request 控制器层

处理 Pull Request 相关的 HTTP 请求
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models.user import User
from api.dependencies import get_current_user
from services.pull_request_service import (
    list_pull_requests as service_list_pull_requests,
    get_pull_request as service_get_pull_request,
    create_pull_request as service_create_pull_request,
    update_pull_request as service_update_pull_request,
    close_pull_request as service_close_pull_request,
    merge_pull_request as service_merge_pull_request,
    create_pr_comment as service_create_pr_comment,
    create_pr_review as service_create_pr_review,
    list_pr_comments as service_list_pr_comments,
)

# 创建路由实例
router = APIRouter(prefix=get_route_prefix("pull_requests"), tags=["pull-requests"])


class PRCreateRequest(BaseModel):
    """创建 PR 请求体"""
    title: str = Field(..., min_length=1, max_length=255, description="PR 标题")
    description: Optional[str] = Field(None, description="PR 描述")
    source_branch: str = Field(..., min_length=1, max_length=100, description="源分支")
    target_branch: str = Field(..., min_length=1, max_length=100, description="目标分支")


class PRUpdateRequest(BaseModel):
    """更新 PR 请求体"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="PR 标题")
    description: Optional[str] = Field(None, description="PR 描述")


class PRCommentCreateRequest(BaseModel):
    """创建 PR 评论请求体"""
    content: str = Field(..., min_length=1, description="评论内容")
    file_path: Optional[str] = Field(None, description="文件路径（行级评论）")
    line_number: Optional[int] = Field(None, description="行号（行级评论）")
    commit_hash: Optional[str] = Field(None, description="提交哈希（行级评论）")
    parent_id: Optional[int] = Field(None, description="父评论ID（回复）")


class PRReviewRequest(BaseModel):
    """PR 审查请求体"""
    status: str = Field(..., description="审查状态：approved/changes_requested")
    comment: Optional[str] = Field(None, description="审查意见")


class PRMergeRequest(BaseModel):
    """PR 合并请求体"""
    merge_method: str = Field(default="merge", description="合并方式：merge/squash/rebase")


@router.get("/{repo_id}/pull-requests")
async def list_pull_requests(
    repo_id: int,
    status: Optional[str] = Query(None, description="状态筛选：open/merged/closed"),
    author: Optional[int] = Query(None, description="作者ID筛选"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取 PR 列表

    Args:
        repo_id: 仓库ID
        status: 状态筛选
        author: 作者ID筛选
        page: 页码
        limit: 每页数量
        db: 数据库会话

    Returns:
        dict: PR 列表和分页信息
    """
    return await service_list_pull_requests(
        db=db,
        repository_id=repo_id,
        status=status,
        author_id=author,
        page=page,
        limit=limit
    )


@router.post("/{repo_id}/pull-requests")
async def create_pull_request(
    repo_id: int,
    data: PRCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建 Pull Request

    Args:
        repo_id: 仓库ID
        data: PR 创建数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 创建的 PR 数据
    """
    return await service_create_pull_request(
        db=db,
        repository_id=repo_id,
        author_id=current_user.id,
        title=data.title,
        description=data.description,
        source_branch=data.source_branch,
        target_branch=data.target_branch
    )


@router.get("/{repo_id}/pull-requests/{pr_number}")
async def get_pull_request(
    repo_id: int,
    pr_number: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取 PR 详情

    Args:
        repo_id: 仓库ID
        pr_number: PR 编号
        db: 数据库会话

    Returns:
        dict: PR 详情（包含评论和审查）
    """
    return await service_get_pull_request(
        db=db,
        repository_id=repo_id,
        pr_number=pr_number,
        include_details=True
    )


@router.patch("/{repo_id}/pull-requests/{pr_number}")
async def update_pull_request(
    repo_id: int,
    pr_number: int,
    data: PRUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新 Pull Request

    Args:
        repo_id: 仓库ID
        pr_number: PR 编号
        data: 更新数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 更新后的 PR 数据
    """
    return await service_update_pull_request(
        db=db,
        repository_id=repo_id,
        pr_number=pr_number,
        user_id=current_user.id,
        title=data.title,
        description=data.description
    )


@router.post("/{repo_id}/pull-requests/{pr_number}/close")
async def close_pull_request(
    repo_id: int,
    pr_number: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    关闭 Pull Request

    Args:
        repo_id: 仓库ID
        pr_number: PR 编号
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 更新后的 PR 数据
    """
    return await service_close_pull_request(
        db=db,
        repository_id=repo_id,
        pr_number=pr_number,
        user_id=current_user.id
    )


@router.post("/{repo_id}/pull-requests/{pr_number}/merge")
async def merge_pull_request(
    repo_id: int,
    pr_number: int,
    data: PRMergeRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    合并 Pull Request

    Args:
        repo_id: 仓库ID
        pr_number: PR 编号
        data: 合并请求数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 更新后的 PR 数据
    """
    return await service_merge_pull_request(
        db=db,
        repository_id=repo_id,
        pr_number=pr_number,
        merger_id=current_user.id,
        merge_method=data.merge_method
    )


# ==================== PR 评论 ====================

@router.get("/{repo_id}/pull-requests/{pr_number}/comments")
async def list_pr_comments(
    repo_id: int,
    pr_number: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取 PR 评论列表

    Args:
        repo_id: 仓库ID
        pr_number: PR 编号
        db: 数据库会话

    Returns:
        list: 评论列表
    """
    return await service_list_pr_comments(
        db=db,
        repository_id=repo_id,
        pr_number=pr_number
    )


@router.post("/{repo_id}/pull-requests/{pr_number}/comments")
async def create_pr_comment(
    repo_id: int,
    pr_number: int,
    data: PRCommentCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建 PR 评论

    Args:
        repo_id: 仓库ID
        pr_number: PR 编号
        data: 评论数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 创建的评论数据
    """
    return await service_create_pr_comment(
        db=db,
        repository_id=repo_id,
        pr_number=pr_number,
        author_id=current_user.id,
        content=data.content,
        file_path=data.file_path,
        line_number=data.line_number,
        commit_hash=data.commit_hash,
        parent_id=data.parent_id
    )


# ==================== PR 审查 ====================

@router.post("/{repo_id}/pull-requests/{pr_number}/reviews")
async def create_pr_review(
    repo_id: int,
    pr_number: int,
    data: PRReviewRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建 PR 审查

    Args:
        repo_id: 仓库ID
        pr_number: PR 编号
        data: 审查数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 创建的审查数据
    """
    return await service_create_pr_review(
        db=db,
        repository_id=repo_id,
        pr_number=pr_number,
        reviewer_id=current_user.id,
        status=data.status,
        comment=data.comment
    )
