"""
Release 控制器层

处理 Release 和 Git 标签相关的 HTTP 请求
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.async_db import get_async_db
from models.repository import Repository
from models.user import User
from api.dependencies import get_current_user
from core.exception import NotFoundException
from services import release_service
from services import release_asset_service
import uuid

# 创建路由实例
router = APIRouter(prefix="/api/v1/repositories", tags=["releases"])


class CreateReleaseRequest(BaseModel):
    """创建 Release 请求体"""
    tag_name: str = Field(..., min_length=1, max_length=100, description="Git 标签名称")
    name: str = Field(..., min_length=1, max_length=255, description="Release 标题")
    description: Optional[str] = Field(None, description="Release 描述（Markdown）")
    commit_hash: Optional[str] = Field(None, description="关联的提交哈希")
    is_draft: bool = Field(default=False, description="是否为草稿")
    is_prerelease: bool = Field(default=False, description="是否为预发布版本")
    create_git_tag: bool = Field(default=True, description="是否同时创建 Git 标签")


class UpdateReleaseRequest(BaseModel):
    """更新 Release 请求体"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Release 标题")
    description: Optional[str] = Field(None, description="Release 描述（Markdown）")
    is_draft: Optional[bool] = Field(None, description="是否为草稿")
    is_prerelease: Optional[bool] = Field(None, description="是否为预发布版本")


class AddAssetRequest(BaseModel):
    """添加 Release 附件请求体"""
    name: str = Field(..., min_length=1, max_length=255, description="文件名")
    file_path: str = Field(..., description="文件存储路径")
    file_size: int = Field(..., ge=1, description="文件大小（字节）")
    content_type: Optional[str] = Field(None, description="MIME 类型")


async def _get_repo(repo_id: uuid.UUID, db: AsyncSession) -> Repository:
    """
    获取仓库实例

    Args:
        repo_id: 仓库ID
        db: 数据库会话

    Returns:
        Repository: 仓库实例

    Raises:
        NotFoundException: 仓库不存在
    """
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")
    return repo


# ==================== Release CRUD ====================


@router.get("/{repo_id}/releases")
async def list_releases(
    repo_id: uuid.UUID,
    include_drafts: bool = Query(False, description="是否包含草稿"),
    include_prereleases: bool = Query(True, description="是否包含预发布版本"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取 Release 列表

    Args:
        repo_id: 仓库ID
        include_drafts: 是否包含草稿
        include_prereleases: 是否包含预发布版本
        page: 页码
        limit: 每页数量
        db: 数据库会话

    Returns:
        dict: Release 列表和分页信息
    """
    await _get_repo(repo_id, db)
    return await release_service.list_releases(
        db=db,
        repository_id=repo_id,
        include_drafts=include_drafts,
        include_prereleases=include_prereleases,
        page=page,
        limit=limit
    )


@router.post("/{repo_id}/releases", status_code=201)
async def create_release(
    repo_id: uuid.UUID,
    data: CreateReleaseRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建 Release

    Args:
        repo_id: 仓库ID
        data: Release 创建数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 创建的 Release 数据
    """
    await _get_repo(repo_id, db)
    return await release_service.create_release(
        db=db,
        repository_id=repo_id,
        author_id=current_user.id,
        tag_name=data.tag_name,
        name=data.name,
        description=data.description,
        commit_hash=data.commit_hash,
        is_draft=data.is_draft,
        is_prerelease=data.is_prerelease,
        create_git_tag=data.create_git_tag
    )


@router.get("/{repo_id}/releases/{release_number}")
async def get_release(
    repo_id: uuid.UUID,
    release_number: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取 Release 详情

    Args:
        repo_id: 仓库ID
        release_number: Release 编号
        db: 数据库会话

    Returns:
        dict: Release 详情（包含附件）
    """
    await _get_repo(repo_id, db)
    return await release_service.get_release(
        db=db,
        repository_id=repo_id,
        release_number=release_number
    )


@router.patch("/{repo_id}/releases/{release_number}")
async def update_release(
    repo_id: uuid.UUID,
    release_number: int,
    data: UpdateReleaseRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新 Release

    Args:
        repo_id: 仓库ID
        release_number: Release 编号
        data: 更新数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 更新后的 Release 数据
    """
    await _get_repo(repo_id, db)
    return await release_service.update_release(
        db=db,
        repository_id=repo_id,
        release_number=release_number,
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        is_draft=data.is_draft,
        is_prerelease=data.is_prerelease
    )


@router.delete("/{repo_id}/releases/{release_number}", status_code=204)
async def delete_release(
    repo_id: uuid.UUID,
    release_number: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除 Release

    Args:
        repo_id: 仓库ID
        release_number: Release 编号
        db: 数据库会话
        current_user: 当前认证用户
    """
    await _get_repo(repo_id, db)
    await release_service.delete_release(
        db=db,
        repository_id=repo_id,
        release_number=release_number,
        user_id=current_user.id
    )


# ==================== Release by Tag ====================


@router.get("/{repo_id}/releases/tag/{tag_name}")
async def get_release_by_tag(
    repo_id: uuid.UUID,
    tag_name: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    根据标签名称获取 Release

    Args:
        repo_id: 仓库ID
        tag_name: 标签名称
        db: 数据库会话

    Returns:
        dict: Release 详情
    """
    await _get_repo(repo_id, db)
    return await release_service.get_release_by_tag(
        db=db,
        repository_id=repo_id,
        tag_name=tag_name
    )


# ==================== Release Asset 管理 ====================


@router.post("/{repo_id}/releases/{release_number}/assets", status_code=201)
async def add_release_asset(
    repo_id: uuid.UUID,
    release_number: int,
    data: AddAssetRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    添加 Release 附件

    Args:
        repo_id: 仓库ID
        release_number: Release 编号
        data: 附件数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 创建的附件数据
    """
    await _get_repo(repo_id, db)
    return await release_service.add_release_asset(
        db=db,
        repository_id=repo_id,
        release_number=release_number,
        user_id=current_user.id,
        name=data.name,
        file_path=data.file_path,
        file_size=data.file_size,
        content_type=data.content_type
    )


@router.post("/{repo_id}/releases/{release_number}/assets/upload", status_code=201)
async def upload_release_asset(
    repo_id: uuid.UUID,
    release_number: int,
    file: UploadFile = File(..., description="附件文件（最大 50MB）"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    上传 Release 附件（multipart，二进制落盘 + 元数据注册）

    Args:
        repo_id: 仓库ID
        release_number: Release 编号
        file: 上传的文件
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 创建的附件元数据
    """
    await _get_repo(repo_id, db)
    file_data, safe_name, content_type = await release_asset_service.read_upload(file)
    return await release_service.add_release_asset_from_upload(
        db=db,
        repository_id=repo_id,
        release_number=release_number,
        user_id=current_user.id,
        filename=safe_name,
        file_data=file_data,
        content_type=content_type,
    )


@router.get("/{repo_id}/releases/{release_number}/assets/{asset_id}/download")
async def download_release_asset(
    repo_id: uuid.UUID,
    release_number: int,
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    下载 Release 附件（流式返回文件，自增下载计数）

    Args:
        repo_id: 仓库ID
        release_number: Release 编号
        asset_id: 附件ID
        db: 数据库会话
        current_user: 当前认证用户
    """
    await _get_repo(repo_id, db)
    asset = await release_service.get_release_asset_for_download(
        db=db,
        repository_id=repo_id,
        release_number=release_number,
        asset_id=asset_id,
    )
    disk_path = release_asset_service.resolve_asset_path(asset.release_id, asset.file_path)
    return FileResponse(
        path=disk_path,
        filename=asset.name,
        media_type=release_asset_service.guess_content_type(asset.file_path),
    )


@router.delete("/{repo_id}/releases/{release_number}/assets/{asset_id}", status_code=204)
async def delete_release_asset(
    repo_id: uuid.UUID,
    release_number: int,
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除 Release 附件

    Args:
        repo_id: 仓库ID
        release_number: Release 编号
        asset_id: 附件ID
        db: 数据库会话
        current_user: 当前认证用户
    """
    await _get_repo(repo_id, db)
    await release_service.delete_release_asset(
        db=db,
        repository_id=repo_id,
        release_number=release_number,
        asset_id=asset_id,
        user_id=current_user.id
    )
