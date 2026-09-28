"""
Git 标签（Tag）管理控制器层

提供标签列表 / 详情 / 创建 / 删除的 HTTP 接口。
写操作需认证；读操作对齐仓库浏览器，公开可见。

端点前缀与仓库子路由一致（/api/v1/repositories），需在 repository_controller
的 /{owner}/{repo} 通配路由之前注册以避免路径冲突。
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from api.routes_prefix import get_route_prefix
from models.async_db import get_async_db
from models import Repository
from models.user import User
from api.dependencies import get_current_user
from core.exception import NotFoundException, ValidationException
from utils.git_utils import (
    GitError,
    get_head_commit,
    get_repository_storage_path,
    list_git_tags,
    get_git_tag,
    create_git_tag,
    delete_git_tag,
)

router = APIRouter(prefix=get_route_prefix("repositories"), tags=["tags"])


async def _get_repo_path(repo_id: uuid.UUID, db: AsyncSession) -> str:
    """获取仓库物理路径，不存在抛 404"""
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")
    return get_repository_storage_path(repo.path)


class TagCreateRequest(BaseModel):
    """创建标签请求体"""
    name: str = Field(..., min_length=1, max_length=255, description="标签名")
    target: Optional[str] = Field(None, description="目标提交/分支，默认 HEAD")
    message: Optional[str] = Field(None, description="附注信息，为空则为轻量标签")


@router.get("/{repo_id}/tags")
async def list_repository_tags(
    repo_id: uuid.UUID,
    pattern: Optional[str] = Query(None, description="glob 过滤，如 v1.*"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取标签列表

    Args:
        repo_id: 仓库ID
        pattern: 可选的 glob 过滤
        db: 数据库会话

    Returns:
        list: [{"name", "message", "commit_hash"}]

    Raises:
        HTTPException: 仓库不存在
    """
    repo_path = await _get_repo_path(repo_id, db)
    try:
        return list_git_tags(repo_path, pattern=pattern)
    except GitError as e:
        raise ValidationException(detail=str(e), error_code="tag_list_failed")


@router.get("/{repo_id}/tags/{tag_name}")
async def get_repository_tag(
    repo_id: uuid.UUID,
    tag_name: str,
    db: AsyncSession = Depends(get_async_db)
):
    """获取单个标签信息，不存在返回 404"""
    repo_path = await _get_repo_path(repo_id, db)
    try:
        tag = get_git_tag(repo_path, tag_name)
    except GitError as e:
        raise ValidationException(detail=str(e), error_code="tag_get_failed")
    if tag is None:
        raise NotFoundException(detail=f"Tag not found: {tag_name}", error_code="tag_not_found")
    return tag


@router.post("/{repo_id}/tags", status_code=201)
async def create_repository_tag(
    repo_id: uuid.UUID,
    data: TagCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建标签（需要认证）

    target 缺省时指向当前 HEAD；message 为空创建轻量标签，否则创建附注标签。

    Returns:
        dict: 创建的标签信息
    """
    repo_path = await _get_repo_path(repo_id, db)
    target = data.target or get_head_commit(repo_path)
    if not target:
        raise ValidationException(detail="Repository has no commit to tag", error_code="tag_no_target")

    try:
        commit_hash = create_git_tag(
            repo_path,
            data.name,
            target,
            message=data.message,
            tagger_name=current_user.full_name or current_user.username,
            tagger_email=current_user.email,
        )
        created = get_git_tag(repo_path, data.name)
    except GitError as e:
        raise ValidationException(detail=str(e), error_code="tag_create_failed")

    return created or {"name": data.name, "message": data.message or "", "commit_hash": commit_hash}


@router.delete("/{repo_id}/tags/{tag_name}", status_code=204)
async def delete_repository_tag(
    repo_id: uuid.UUID,
    tag_name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """删除标签（需要认证，不存在则忽略）"""
    repo_path = await _get_repo_path(repo_id, db)
    try:
        delete_git_tag(repo_path, tag_name)
    except GitError as e:
        raise ValidationException(detail=str(e), error_code="tag_delete_failed")
    return None
