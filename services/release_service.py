"""
Release 服务层

处理 Release 和 Git 标签相关的所有业务逻辑
"""
import os
from typing import List, Optional, Dict, Any, Callable, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models import Release, ReleaseAsset, Repository, User
from core.exception import NotFoundException, ValidationException, AuthorizationException
from utils.permission_utils import check_repository_permission
from utils.db_utils import paginate, get_next_sequence_number
from utils.response_builder import build_pagination_response


# 类型别名：仓库路径获取函数类型
RepositoryPathGetter = Callable[[AsyncSession, int], Awaitable[str]]


# =============================================================================
# Git 标签管理
# =============================================================================

def _create_git_tag(
    repo_path: str,
    tag_name: str,
    commit_hash: str,
    message: Optional[str] = None
) -> str:
    """
    创建 Git 标签

    Args:
        repo_path: 仓库物理路径
        tag_name: 标签名称
        commit_hash: 关联的提交哈希
        message: 标签说明（可选，为空时创建轻量标签）

    Returns:
        str: 标签哈希

    Raises:
        ValidationException: 创建标签失败
    """
    import subprocess

    try:
        if message:
            # 创建附注标签（annotated tag）
            result = subprocess.run(
                ["git", "tag", "-a", tag_name, commit_hash, "-m", message],
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8"
            )
        else:
            # 创建轻量标签（lightweight tag）
            result = subprocess.run(
                ["git", "tag", tag_name, commit_hash],
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8"
            )

        if result.returncode != 0:
            raise ValidationException(detail=f"Failed to create tag: {result.stderr}")

        # 获取标签哈希
        result = subprocess.run(
            ["git", "rev-list", "-n", "1", tag_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode != 0:
            raise ValidationException(detail=f"Failed to get tag hash: {result.stderr}")

        return result.stdout.strip()

    except subprocess.SubprocessError as e:
        raise ValidationException(detail=f"Failed to create tag: {str(e)}")


def _delete_git_tag(repo_path: str, tag_name: str) -> None:
    """
    删除 Git 标签

    Args:
        repo_path: 仓库物理路径
        tag_name: 标签名称

    Raises:
        ValidationException: 删除标签失败
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "tag", "-d", tag_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode != 0:
            raise ValidationException(detail=f"Failed to delete tag: {result.stderr}")

    except subprocess.SubprocessError as e:
        raise ValidationException(detail=f"Failed to delete tag: {str(e)}")


def list_git_tags(repo_path: str, pattern: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    列出 Git 标签

    Args:
        repo_path: 仓库物理路径
        pattern: 标签匹配模式（如 "v1.*"）

    Returns:
        List[dict]: 标签列表

    Raises:
        ValidationException: 获取标签列表失败
    """
    import subprocess

    try:
        cmd = ["git", "tag", "-l"]
        if pattern:
            cmd.append(pattern)

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode != 0:
            raise ValidationException(detail=f"Failed to list tags: {result.stderr}")

        tags = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            tag_name = line.strip()

            # 获取标签信息
            info_result = subprocess.run(
                ["git", "tag", "-l", "-n1", tag_name],
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8"
            )

            message = ""
            if info_result.returncode == 0:
                parts = info_result.stdout.strip().split(" ", 1)
                if len(parts) > 1:
                    message = parts[1]

            # 获取关联的提交哈希
            hash_result = subprocess.run(
                ["git", "rev-list", "-n", "1", tag_name],
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8"
            )

            commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else None

            tags.append({
                "name": tag_name,
                "message": message,
                "commit_hash": commit_hash
            })

        return tags

    except subprocess.SubprocessError as e:
        raise ValidationException(detail=f"Failed to list tags: {str(e)}")


def get_git_tag(repo_path: str, tag_name: str) -> Optional[Dict[str, Any]]:
    """
    获取单个 Git 标签信息

    Args:
        repo_path: 仓库物理路径
        tag_name: 标签名称

    Returns:
        dict: 标签信息，不存在返回 None

    Raises:
        ValidationException: 获取标签信息失败
    """
    import subprocess

    try:
        # 检查标签是否存在
        result = subprocess.run(
            ["git", "tag", "-l", tag_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode != 0 or not result.stdout.strip():
            return None

        # 获取标签信息
        info_result = subprocess.run(
            ["git", "tag", "-l", "-n1", tag_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        message = ""
        if info_result.returncode == 0:
            parts = info_result.stdout.strip().split(" ", 1)
            if len(parts) > 1:
                message = parts[1]

        # 获取关联的提交哈希
        hash_result = subprocess.run(
            ["git", "rev-list", "-n", "1", tag_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else None

        return {
            "name": tag_name,
            "message": message,
            "commit_hash": commit_hash
        }

    except subprocess.SubprocessError as e:
        raise ValidationException(detail=f"Failed to get tag: {str(e)}")


# =============================================================================
# Release 管理
# =============================================================================

async def list_releases(
    db: AsyncSession,
    repository_id: int,
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
    releases, total = await paginate(db, stmt, page, limit)

    return build_pagination_response(
        items=[build_release_response(r) for r in releases],
        total=total,
        page=page,
        limit=limit
    )


async def get_release(
    db: AsyncSession,
    repository_id: int,
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
        raise NotFoundException(detail=f"Release #{release_number} not found")

    return build_release_response(release, include_assets=True)


async def get_release_by_tag(
    db: AsyncSession,
    repository_id: int,
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
        raise NotFoundException(detail=f"Release with tag '{tag_name}' not found")

    return build_release_response(release, include_assets=True)


async def create_release(
    db: AsyncSession,
    repository_id: int,
    author_id: int,
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
        raise NotFoundException(detail="Repository not found")

    # 检查标签是否已存在
    result = await db.execute(
        select(Release).filter(
            Release.repository_id == repository_id,
            Release.tag_name == tag_name
        )
    )
    if result.scalar_one_or_none():
        raise ValidationException(detail=f"Release with tag '{tag_name}' already exists")

    # 获取仓库路径（如果未提供）
    if repo_path is None:
        repo_path = await get_repository_path(db, repository_id)

    # 如果未指定提交哈希，使用当前 HEAD
    if not commit_hash:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        if result.returncode != 0:
            raise ValidationException(detail="Failed to get HEAD commit hash")
        commit_hash = result.stdout.strip()

    # 创建 Git 标签
    if create_git_tag:
        try:
            _create_git_tag(repo_path, tag_name, commit_hash, message=name)
        except ValidationException:
            # 标签已存在则继续
            pass

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
    repository_id: int,
    release_number: int,
    user_id: int,
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
        raise NotFoundException(detail=f"Release #{release_number} not found")

    # 检查权限（只有作者或管理员可以修改）
    if release.author_id != user_id:
        # 检查是否为仓库管理员
        has_permission = await check_repository_permission(
            db, repository_id, user_id, "admin"
        )
        if not has_permission:
            raise AuthorizationException(detail="Not authorized to update this release")

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
    repository_id: int,
    release_number: int,
    user_id: int,
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
        raise NotFoundException(detail=f"Release #{release_number} not found")

    # 检查权限
    if release.author_id != user_id:
        has_permission = await check_repository_permission(
            db, repository_id, user_id, "admin"
        )
        if not has_permission:
            raise AuthorizationException(detail="Not authorized to delete this release")

    # 删除 Git 标签
    if delete_git_tag:
        try:
            # 获取仓库路径（如果未提供）
            if repo_path is None:
                repo_path = await get_repository_path(db, repository_id)
            _delete_git_tag(repo_path, release.tag_name)
        except ValidationException:
            # 标签不存在则忽略
            pass

    await db.delete(release)
    await db.commit()


# =============================================================================
# Release Asset 管理
# =============================================================================

async def add_release_asset(
    db: AsyncSession,
    repository_id: int,
    release_number: int,
    user_id: int,
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
        raise NotFoundException(detail=f"Release #{release_number} not found")

    # 检查权限
    if release.author_id != user_id:
        has_permission = await check_repository_permission(
            db, repository_id, user_id, "admin"
        )
        if not has_permission:
            raise AuthorizationException(detail="Not authorized to add assets to this release")

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
    repository_id: int,
    release_number: int,
    asset_id: int,
    user_id: int
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
        raise NotFoundException(detail=f"Release #{release_number} not found")

    # 获取附件
    stmt = select(ReleaseAsset).filter(
        ReleaseAsset.id == asset_id,
        ReleaseAsset.release_id == release.id
    )

    result = await db.execute(stmt)
    asset = result.scalar_one_or_none()

    if not asset:
        raise NotFoundException(detail="Asset not found")

    # 检查权限
    if release.author_id != user_id:
        has_permission = await check_repository_permission(
            db, repository_id, user_id, "admin"
        )
        if not has_permission:
            raise AuthorizationException(detail="Not authorized to delete assets from this release")

    # 删除物理文件
    if os.path.exists(asset.file_path):
        os.remove(asset.file_path)

    await db.delete(asset)
    await db.commit()


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
