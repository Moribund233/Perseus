"""
Release 服务层

处理 Release 和 Git 标签相关的所有业务逻辑
"""
import os
import asyncio
import logging
from typing import List, Optional, Dict, Any, Callable, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from sqlalchemy.orm import selectinload

from models import Release, ReleaseAsset, Repository, User
from core.exception import NotFoundException, ValidationException, AuthorizationException
from utils.permission_utils import check_repository_permission
from utils.db_utils import paginate, get_next_sequence_number
from utils.response_builder import build_pagination_response
from utils.git_utils import (
    create_git_tag as git_create_tag,
    delete_git_tag as git_delete_tag,
    get_head_commit,
    GitError,
)

logger = logging.getLogger(__name__)


# 类型别名：仓库路径获取函数类型
RepositoryPathGetter = Callable[[AsyncSession, int], Awaitable[str]]


# =============================================================================
# Git 标签管理（实现见 utils/git_utils.py，基于 pygit2，无子进程）
# =============================================================================


# =============================================================================
# Release 管理
# =============================================================================

async def list_releases(
    db: AsyncSession,
    repository_id: uuid.UUID,
    include_drafts: bool = False,
    include_prereleases: bool = True,
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """
    获取 Release 列表

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        include_drafts: 是否包含草稿
        include_prereleases: 是否包含预发布版本
        page: 页码
        limit: 每页数量

    Returns:
        dict: 包含 Release 列表和分页信息
    """
    stmt = select(Release).filter(Release.repository_id == repository_id)

    if not include_drafts:
        stmt = stmt.filter(Release.is_draft == False)

    if not include_prereleases:
        stmt = stmt.filter(Release.is_prerelease == False)

    stmt = stmt.order_by(Release.created_at.desc())
    stmt = stmt.options(
        selectinload(Release.author),
        selectinload(Release.assets)
    )
    releases, total = await paginate(db, stmt, page, limit)

    return build_pagination_response(
        items=[build_release_response(r, include_assets=True) for r in releases],
        total=total,
        page=page,
        limit=limit
    )


async def get_release(
    db: AsyncSession,
    repository_id: uuid.UUID,
    release_number: int
) -> dict:
    """
    获取 Release 详情

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        release_number: Release 编号

    Returns:
        dict: Release 详情

    Raises:
        NotFoundException: Release 不存在
    """
    stmt = select(Release).filter(
        Release.repository_id == repository_id,
        Release.release_number == release_number
    ).options(
        selectinload(Release.author),
        selectinload(Release.assets)
    )

    result = await db.execute(stmt)
    release = result.scalar_one_or_none()

    if not release:
        raise NotFoundException(detail=f"Release #{release_number} not found", error_code="release_not_found")

    return build_release_response(release, include_assets=True)


async def get_release_by_tag(
    db: AsyncSession,
    repository_id: uuid.UUID,
    tag_name: str
) -> dict:
    """
    根据标签名称获取 Release

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        tag_name: 标签名称

    Returns:
        dict: Release 详情

    Raises:
        NotFoundException: Release 不存在
    """
    stmt = select(Release).filter(
        Release.repository_id == repository_id,
        Release.tag_name == tag_name
    ).options(
        selectinload(Release.author),
        selectinload(Release.assets)
    )

    result = await db.execute(stmt)
    release = result.scalar_one_or_none()

    if not release:
        raise NotFoundException(detail=f"Release with tag '{tag_name}' not found", error_code="release_tag_not_found")

    return build_release_response(release, include_assets=True)


async def create_release(
    db: AsyncSession,
    repository_id: uuid.UUID,
    author_id: uuid.UUID,
    tag_name: str,
    name: str,
    description: Optional[str] = None,
    commit_hash: Optional[str] = None,
    is_draft: bool = False,
    is_prerelease: bool = False,
    create_git_tag: bool = True,
    repo_path: Optional[str] = None
) -> dict:
    """
    创建 Release

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        author_id: 作者ID
        tag_name: Git 标签名称
        name: Release 标题
        description: Release 描述
        commit_hash: 关联的提交哈希（为空则使用当前 HEAD）
        is_draft: 是否为草稿
        is_prerelease: 是否为预发布版本
        create_git_tag: 是否同时创建 Git 标签
        repo_path: 仓库物理路径（可选，未提供时从数据库获取）

    Returns:
        dict: 创建的 Release 数据

    Raises:
        ValidationException: 创建失败
        NotFoundException: 仓库不存在
    """
    from utils.git_utils import get_repository_path

    # 检查仓库是否存在
    result = await db.execute(
        select(Repository).filter(Repository.id == repository_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")

    # 检查标签是否已存在
    result = await db.execute(
        select(Release).filter(
            Release.repository_id == repository_id,
            Release.tag_name == tag_name
        )
    )
    if result.scalar_one_or_none():
        raise ValidationException(detail=f"Release with tag '{tag_name}' already exists", error_code="release_tag_already_exists")

    # 获取仓库路径（如果未提供）
    if repo_path is None:
        repo_path = await get_repository_path(db, repository_id)

    # 如果未指定提交哈希，使用当前 HEAD（空仓库无提交时回退为占位值，
    # 保持 commit_hash 非空；此时标签创建会失败并被记录）
    if not commit_hash:
        commit_hash = get_head_commit(repo_path) or "HEAD"

    # 创建 Git 标签（幂等：已存在则复用）。标签创建失败不阻塞 Release
    # （例如空仓库无 HEAD / 无提交），但记录告警，避免静默丢失标签。
    if create_git_tag:
        try:
            await asyncio.to_thread(git_create_tag, repo_path, tag_name, commit_hash, name)
        except GitError as e:
            logger.warning(f"创建 Git 标签失败 tag={tag_name} repo={repo_path}: {e}")

    # 生成 Release 编号
    release_number = await get_next_sequence_number(
        db, Release, "release_number",
        {"repository_id": repository_id}
    )

    # 创建 Release
    release = Release(
        repository_id=repository_id,
        release_number=release_number,
        tag_name=tag_name,
        name=name,
        description=description,
        author_id=author_id,
        commit_hash=commit_hash,
        is_draft=is_draft,
        is_prerelease=is_prerelease
    )

    db.add(release)
    await db.commit()
    await db.refresh(release)

    return build_release_response(release)


async def update_release(
    db: AsyncSession,
    repository_id: uuid.UUID,
    release_number: int,
    user_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_draft: Optional[bool] = None,
    is_prerelease: Optional[bool] = None
) -> dict:
    """
    更新 Release

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        release_number: Release 编号
        user_id: 当前用户ID
        name: 新标题
        description: 新描述
        is_draft: 是否为草稿
        is_prerelease: 是否为预发布版本

    Returns:
        dict: 更新后的 Release 数据

    Raises:
        NotFoundException: Release 不存在
        AuthorizationException: 无权限修改
    """
    stmt = select(Release).filter(
        Release.repository_id == repository_id,
        Release.release_number == release_number
    )

    result = await db.execute(stmt)
    release = result.scalar_one_or_none()

    if not release:
        raise NotFoundException(detail=f"Release #{release_number} not found", error_code="release_not_found")

    # 检查权限（只有作者或管理员可以修改）
    if release.author_id != user_id:
        # 检查是否为仓库管理员
        has_permission = await check_repository_permission(
            db, repository_id, user_id, ["admin"]
        )
        if not has_permission:
            raise AuthorizationException(detail="Not authorized to update this release", error_code="release_update_forbidden")

    # 更新字段
    if name is not None:
        release.name = name

    if description is not None:
        release.description = description

    if is_draft is not None:
        release.is_draft = is_draft

    if is_prerelease is not None:
        release.is_prerelease = is_prerelease

    await db.commit()
    await db.refresh(release)

    return build_release_response(release)


async def delete_release(
    db: AsyncSession,
    repository_id: uuid.UUID,
    release_number: int,
    user_id: uuid.UUID,
    delete_git_tag: bool = True,
    repo_path: Optional[str] = None
) -> None:
    """
    删除 Release

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        release_number: Release 编号
        user_id: 当前用户ID
        delete_git_tag: 是否同时删除 Git 标签
        repo_path: 仓库物理路径（可选，未提供时从数据库获取）

    Raises:
        NotFoundException: Release 不存在
        AuthorizationException: 无权限删除
    """
    from utils.git_utils import get_repository_path

    stmt = select(Release).filter(
        Release.repository_id == repository_id,
        Release.release_number == release_number
    )

    result = await db.execute(stmt)
    release = result.scalar_one_or_none()

    if not release:
        raise NotFoundException(detail=f"Release #{release_number} not found", error_code="release_not_found")

    # 检查权限
    if release.author_id != user_id:
        has_permission = await check_repository_permission(
            db, repository_id, user_id, ["admin"]
        )
        if not has_permission:
            raise AuthorizationException(detail="Not authorized to delete this release", error_code="release_delete_forbidden")

    # 删除 Git 标签（不存在则忽略）
    if delete_git_tag:
        try:
            if repo_path is None:
                repo_path = await get_repository_path(db, repository_id)
            await asyncio.to_thread(git_delete_tag, repo_path, release.tag_name)
        except GitError as e:
            logger.warning(f"删除 Git 标签失败 tag={release.tag_name} repo={repo_path}: {e}")

    # 先清理关联附件（含物理文件），避免 release_id 外键约束导致删除失败
    asset_result = await db.execute(
        select(ReleaseAsset).filter(ReleaseAsset.release_id == release.id)
    )
    for asset in asset_result.scalars().all():
        if asset.file_path and os.path.exists(asset.file_path):
            try:
                os.remove(asset.file_path)
            except OSError:
                pass
        await db.delete(asset)
    await db.flush()

    await db.delete(release)
    await db.commit()


# =============================================================================
# Release Asset 管理
# =============================================================================

async def add_release_asset(
    db: AsyncSession,
    repository_id: uuid.UUID,
    release_number: int,
    user_id: uuid.UUID,
    name: str,
    file_path: str,
    file_size: int,
    content_type: Optional[str] = None
) -> dict:
    """
    添加 Release 附件

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        release_number: Release 编号
        user_id: 当前用户ID
        name: 文件名
        file_path: 文件存储路径
        file_size: 文件大小
        content_type: MIME 类型

    Returns:
        dict: 创建的附件数据

    Raises:
        NotFoundException: Release 不存在
        AuthorizationException: 无权限添加
    """
    stmt = select(Release).filter(
        Release.repository_id == repository_id,
        Release.release_number == release_number
    )

    result = await db.execute(stmt)
    release = result.scalar_one_or_none()

    if not release:
        raise NotFoundException(detail=f"Release #{release_number} not found", error_code="release_not_found")

    # 检查权限
    if release.author_id != user_id:
        has_permission = await check_repository_permission(
            db, repository_id, user_id, ["admin"]
        )
        if not has_permission:
            raise AuthorizationException(detail="Not authorized to add assets to this release", error_code="release_asset_add_forbidden")

    # 创建附件
    asset = ReleaseAsset(
        release_id=release.id,
        name=name,
        file_path=file_path,
        file_size=file_size,
        content_type=content_type
    )

    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    return build_asset_response(asset)


async def delete_release_asset(
    db: AsyncSession,
    repository_id: uuid.UUID,
    release_number: int,
    asset_id: uuid.UUID,
    user_id: uuid.UUID
) -> None:
    """
    删除 Release 附件

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        release_number: Release 编号
        asset_id: 附件ID
        user_id: 当前用户ID

    Raises:
        NotFoundException: Release 或附件不存在
        AuthorizationException: 无权限删除
    """
    # 获取 Release
    stmt = select(Release).filter(
        Release.repository_id == repository_id,
        Release.release_number == release_number
    )

    result = await db.execute(stmt)
    release = result.scalar_one_or_none()

    if not release:
        raise NotFoundException(detail=f"Release #{release_number} not found", error_code="release_not_found")

    # 获取附件
    stmt = select(ReleaseAsset).filter(
        ReleaseAsset.id == asset_id,
        ReleaseAsset.release_id == release.id
    )

    result = await db.execute(stmt)
    asset = result.scalar_one_or_none()

    if not asset:
        raise NotFoundException(detail="Asset not found", error_code="asset_not_found")

    # 检查权限
    if release.author_id != user_id:
        has_permission = await check_repository_permission(
            db, repository_id, user_id, ["admin"]
        )
        if not has_permission:
            raise AuthorizationException(detail="Not authorized to delete assets from this release", error_code="release_asset_delete_forbidden")

    # 删除物理文件
    if os.path.exists(asset.file_path):
        os.remove(asset.file_path)

    await db.delete(asset)
    await db.commit()


async def add_release_asset_from_upload(
    db: AsyncSession,
    repository_id: uuid.UUID,
    release_number: int,
    user_id: uuid.UUID,
    filename: str,
    file_data: bytes,
    content_type: str,
) -> dict:
    """
    上传并注册 Release 附件（二进制落盘 + 元数据入库）

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        release_number: Release 编号
        user_id: 当前用户ID
        filename: 消毒后的文件名
        file_data: 文件字节内容
        content_type: MIME 类型

    Returns:
        dict: 创建的附件元数据

    Raises:
        NotFoundException: Release 不存在
        AuthorizationException: 无权限添加
    """
    from services import release_asset_service

    stmt = select(Release).filter(
        Release.repository_id == repository_id,
        Release.release_number == release_number
    )
    result = await db.execute(stmt)
    release = result.scalar_one_or_none()
    if not release:
        raise NotFoundException(detail=f"Release #{release_number} not found", error_code="release_not_found")

    if release.author_id != user_id:
        has_permission = await check_repository_permission(
            db, repository_id, user_id, ["admin"]
        )
        if not has_permission:
            raise AuthorizationException(detail="Not authorized to add assets to this release", error_code="release_asset_add_forbidden")

    stored_name = f"{uuid.uuid4().hex[:12]}_{filename}"
    file_path = release_asset_service.save_asset_file(release.id, stored_name, file_data)

    asset = ReleaseAsset(
        release_id=release.id,
        name=filename,
        file_path=file_path,
        file_size=len(file_data),
        content_type=content_type,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return build_asset_response(asset)


async def get_release_asset_for_download(
    db: AsyncSession,
    repository_id: uuid.UUID,
    release_number: int,
    asset_id: uuid.UUID,
) -> ReleaseAsset:
    """
    定位待下载的附件并自增下载计数

    Raises:
        NotFoundException: Release 或附件不存在
    """
    stmt = select(Release).filter(
        Release.repository_id == repository_id,
        Release.release_number == release_number
    )
    result = await db.execute(stmt)
    release = result.scalar_one_or_none()
    if not release:
        raise NotFoundException(detail=f"Release #{release_number} not found", error_code="release_not_found")

    stmt = select(ReleaseAsset).filter(
        ReleaseAsset.id == asset_id,
        ReleaseAsset.release_id == release.id
    )
    result = await db.execute(stmt)
    asset = result.scalar_one_or_none()
    if not asset:
        raise NotFoundException(detail="Asset not found", error_code="asset_not_found")

    asset.download_count = (asset.download_count or 0) + 1
    await db.commit()
    return asset


# =============================================================================
# 响应构建函数
# =============================================================================

def build_release_response(release: Release, include_assets: bool = False) -> dict:
    """
    构建 Release 响应数据

    Args:
        release: Release 模型实例
        include_assets: 是否包含附件列表

    Returns:
        dict: 响应数据
    """
    data = {
        "id": release.id,
        "release_number": release.release_number,
        "tag_name": release.tag_name,
        "name": release.name,
        "description": release.description,
        "author": {
            "id": release.author.id if release.author else None,
            "username": release.author.username if release.author else None
        },
        "commit_hash": release.commit_hash,
        "is_draft": release.is_draft,
        "is_prerelease": release.is_prerelease,
        "created_at": release.created_at.isoformat() if release.created_at else None,
        "updated_at": release.updated_at.isoformat() if release.updated_at else None
    }

    if include_assets:
        data["assets"] = [build_asset_response(a) for a in release.assets]

    return data


def build_asset_response(asset: ReleaseAsset) -> dict:
    """
    构建 Release Asset 响应数据

    Args:
        asset: ReleaseAsset 模型实例

    Returns:
        dict: 响应数据
    """
    return {
        "id": asset.id,
        "name": asset.name,
        "file_size": asset.file_size,
        "content_type": asset.content_type,
        "download_count": asset.download_count,
        "created_at": asset.created_at.isoformat() if asset.created_at else None
    }
