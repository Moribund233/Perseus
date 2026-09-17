"""
行内评论控制器（Editor Discussions / 文件+行号锚定）

路径: /api/v1/repositories/{repo_id}/discussions
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from api.routes_prefix import get_route_prefix
from models.async_db import get_async_db
from models.user import User
from api.dependencies import get_current_user
from services.file_comment_service import (
    create_file_comment,
    list_file_comments,
    set_file_comment_resolved,
    delete_file_comment,
)
from core.exception import NotFoundException

router = APIRouter(prefix=get_route_prefix("repositories"), tags=["file-comments"])


class FileCommentCreateRequest(BaseModel):
    """创建行内评论请求体"""
    content: str = Field(..., min_length=1, max_length=10000, description="评论内容")
    file_path: str = Field(..., min_length=1, max_length=500, description="文件路径")
    line_number: Optional[int] = Field(None, ge=1, description="行号")
    branch: Optional[str] = Field(None, max_length=100, description="分支名")
    commit_hash: Optional[str] = Field(None, max_length=40, description="提交哈希")
    parent_id: Optional[uuid.UUID] = Field(None, description="父评论ID（回复）")


class FileCommentResolveRequest(BaseModel):
    """解决/重新打开评论请求体"""
    resolved: bool = Field(..., description="是否已解决")


@router.post("/{repo_id}/discussions", status_code=201)
async def create_discussion_comment(
    repo_id: uuid.UUID,
    data: FileCommentCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await create_file_comment(
        db=db,
        repository_id=repo_id,
        author_id=current_user.id,
        content=data.content,
        file_path=data.file_path,
        line_number=data.line_number,
        branch=data.branch,
        commit_hash=data.commit_hash,
        parent_id=data.parent_id,
    )


@router.get("/{repo_id}/discussions")
async def get_discussion_comments(
    repo_id: uuid.UUID,
    file_path: Optional[str] = Query(None, description="按文件路径过滤"),
    branch: Optional[str] = Query(None, description="按分支过滤"),
    line_number: Optional[int] = Query(None, description="按行号过滤"),
    include_resolved: bool = Query(True, description="是否包含已解决评论"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await list_file_comments(
        db=db,
        repository_id=repo_id,
        user_id=current_user.id,
        file_path=file_path,
        branch=branch,
        line_number=line_number,
        include_resolved=include_resolved,
    )


@router.patch("/{repo_id}/discussions/{comment_id}")
async def resolve_discussion_comment(
    repo_id: uuid.UUID,
    comment_id: uuid.UUID,
    data: FileCommentResolveRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await set_file_comment_resolved(
        db=db,
        repository_id=repo_id,
        comment_id=comment_id,
        user_id=current_user.id,
        resolved=data.resolved,
    )


@router.delete("/{repo_id}/discussions/{comment_id}")
async def remove_discussion_comment(
    repo_id: uuid.UUID,
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    success = await delete_file_comment(
        db=db,
        repository_id=repo_id,
        comment_id=comment_id,
        user_id=current_user.id,
    )
    return {"success": success}