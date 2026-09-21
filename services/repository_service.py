"""
仓库服务层

处理与Git仓库相关的所有业务逻辑
"""
import os
import shutil
import asyncio
import logging
from typing import Dict, Tuple
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, asc, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Repository
from models.branch import Branch
from models.repository_member import RepositoryMember
from core.exception import ValidationException, NotFoundException, ConflictException
from utils.git_utils import init_bare_repo, get_repository_storage_path, repo_exists_async, enable_receive_pack, GitError
from utils.response_builder import build_repo_response, build_pagination_response
from utils.db_utils import exists, paginate
from services.language_service import detect_repo_languages
from core.constants import ROLE_PRIORITY

# 日志记录器
logger = logging.getLogger(__name__)

# 物理仓库存在状态缓存（仓库ID -> (存在状态, 缓存时间)）
# 缓存有效期30秒，减少频繁的磁盘IO检查
_repo_exists_cache: Dict[uuid.UUID, Tuple[bool, datetime]] = {}
_REPO_EXISTS_CACHE_TTL_SECONDS = 30


def _get_cached_repo_exists(repo_id: uuid.UUID) -> Tuple[bool, bool]:
    """
    获取缓存的仓库存在状态

    Args:
        repo_id: 仓库ID

    Returns:
        Tuple[bool, bool]: (是否存在, 是否命中缓存)
    """
    if repo_id in _repo_exists_cache:
        exists, cached_time = _repo_exists_cache[repo_id]
        if datetime.now() - cached_time < timedelta(seconds=_REPO_EXISTS_CACHE_TTL_SECONDS):
            return exists, True
        # 缓存过期，删除
        del _repo_exists_cache[repo_id]
    return False, False


def _set_cached_repo_exists(repo_id: uuid.UUID, exists: bool) -> None:
    """
    设置仓库存在状态缓存

    Args:
        repo_id: 仓库ID
        exists: 是否存在
    """
    _repo_exists_cache[repo_id] = (exists, datetime.now())


async def _check_physical_repo_exists_async(repo: Repository) -> bool:
    """
    检查物理仓库是否存在（异步版本，带缓存）

    优先从缓存获取，缓存未命中时执行异步IO检查
    缓存有效期30秒，减少频繁的磁盘IO操作

    Args:
        repo: Repository 模型对象

    Returns:
        bool: 物理仓库是否存在
    """
    # 先检查缓存
    cached_exists, cache_hit = _get_cached_repo_exists(repo.id)
    if cache_hit:
        return cached_exists

    # 缓存未命中，执行异步检查
    try:
        physical_path = get_repository_storage_path(repo.path)
        exists = await repo_exists_async(physical_path)
        # 更新缓存
        _set_cached_repo_exists(repo.id, exists)
        return exists
    except Exception:
        return False


async def sync_repository_default_branch(repo: Repository, db: AsyncSession) -> None:
    """
    将数据库默认分支与物理仓库实际分支对齐（自愈逻辑）

    背景：早期创建的仓库 DB 默认分支为 master，而用户本地以 main 推送，
    导致仓库页按 default_branch 查询 commits/tree 时 404/500。

    策略（物理仓库存在且非空时）：
    - DB 默认分支物理存在：仅修复悬空的物理 HEAD 指向
    - DB 默认分支物理不存在：采用物理分支（优先 main，否则首个分支），
      同步 Repository.default_branch 与 Branch 表默认标记

    Args:
        repo: Repository 模型对象
        db: 异步数据库会话
    """
    from utils.git_utils import get_local_branch_names, set_head_branch

    try:
        physical_path = get_repository_storage_path(repo.path)
        branches = await asyncio.to_thread(get_local_branch_names, physical_path)
        if not branches:
            return  # 物理仓库不存在或为空，无需处理

        default_branch = repo.default_branch
        adopted: str | None = None

        if default_branch in branches:
            # DB 默认分支存在，确保物理 HEAD 指向它（修复悬空 HEAD）
            await asyncio.to_thread(set_head_branch, physical_path, default_branch)
        else:
            # DB 默认分支不存在（如推送的是 main），采用物理分支
            adopted = "main" if "main" in branches else sorted(branches)[0]

        if adopted is None:
            # 默认分支已一致，仅同步 Branch 表中缺失的分支行（推送产生的分支）
            await _sync_branch_rows(repo.id, branches, repo.default_branch, db)
            return

        repo.default_branch = adopted
        await asyncio.to_thread(set_head_branch, physical_path, adopted)
        await _sync_branch_rows(repo.id, branches, adopted, db)
        await db.commit()
        logger.info(
            f"Repository {repo.path}: default branch migrated "
            f"{default_branch!r} -> {adopted!r} (physical branches: {branches})"
        )
    except Exception as e:
        logger.warning(f"Failed to sync default branch for {repo.path}: {e}")


async def _sync_branch_rows(
    repo_id: uuid.UUID,
    physical_branches: list,
    default_branch: str,
    db: AsyncSession,
) -> None:
    """
    同步 Branch 表：为物理存在的分支补建行，并维护默认分支标记

    不删除物理侧已消失的分支行（可能被 PR 等引用）
    """
    result = await db.execute(select(Branch).filter(Branch.repository_id == repo_id))
    db_branches = result.scalars().all()
    existing_names = {b.name for b in db_branches}

    changed = False
    for name in physical_branches:
        if name not in existing_names:
            db.add(Branch(
                name=name,
                repository_id=repo_id,
                is_protected=False,
                is_default=(name == default_branch),
            ))
            existing_names.add(name)
            changed = True

    for b in db_branches:
        expected = b.name == default_branch
        if b.is_default != expected:
            b.is_default = expected
            changed = True

    if changed:
        await db.commit()


async def _enrich_repos_with_physical_status(repos: list) -> list[dict]:
    """
    为仓库列表添加物理存在状态

    并行检查所有仓库的物理存在状态（异步IO优化）

    Args:
        repos: Repository 模型对象列表

    Returns:
        list[dict]: 包含物理状态的仓库响应列表
    """
    if not repos:
        return []

    physical_checks = await asyncio.gather(
        *[_check_physical_repo_exists_async(repo) for repo in repos],
        return_exceptions=True
    )
    exists_flags = [isinstance(c, bool) and c for c in physical_checks]

    language_map: Dict[str, dict] = {}
    queries = [
        detect_repo_languages(get_repository_storage_path(repo.path), repo.default_branch or "HEAD")
        for repo, ok in zip(repos, exists_flags)
        if ok
    ]
    if queries:
        results = await asyncio.gather(*queries, return_exceptions=True)
        it = iter(results)
        for repo, ok in zip(repos, exists_flags):
            if ok:
                lang_result = next(it)
                language_map[repo.id] = lang_result if isinstance(lang_result, dict) else {}

    return [
        build_repo_response(
            repo,
            ok,
            language_map.get(repo.id, {}),
        )
        for repo, ok in zip(repos, exists_flags)
    ]


async def get_repositories(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    sort: str = "updated_at",
    order: str = "desc",
    q: str | None = None,
    is_public: bool | None = None,
):
    """
    获取所有仓库（支持分页、排序、搜索、筛选）

    Args:
        db: 异步数据库会话
        page: 页码，从1开始
        limit: 每页数量
        sort: 排序字段（name, updated_at, stars）
        order: 排序方向（asc, desc）
        q: 搜索关键词（按名称、描述、路径模糊匹配）
        is_public: 可见性筛选

    Returns:
        dict: 分页响应，包含 items, total, page, limit, pages, has_next, has_prev
    """
    stmt = select(Repository).filter(Repository.is_archived == False)

    if is_public is not None:
        stmt = stmt.filter(Repository.is_public == is_public)

    if q:
        like_pattern = f"%{q}%"
        stmt = stmt.filter(
            or_(
                Repository.name.ilike(like_pattern),
                Repository.description.ilike(like_pattern),
                Repository.path.ilike(like_pattern),
            )
        )

    sort_column_map = {
        "name": Repository.name,
        "updated_at": Repository.updated_at,
        "stars": Repository.star_count,
    }
    sort_col = sort_column_map.get(sort, Repository.updated_at)
    order_func = asc if order == "asc" else desc
    stmt = stmt.order_by(order_func(sort_col))

    repos, total = await paginate(db, stmt, page, limit)
    items = await _enrich_repos_with_physical_status(list(repos))

    return build_pagination_response(items, total, page, limit)


async def get_repository_by_id(repo_id: uuid.UUID, db: AsyncSession):
    """
    根据ID获取仓库

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话

    Returns:
        dict: 仓库信息（包含物理仓库信息）

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if repo is None:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")
    await sync_repository_default_branch(repo, db)
    physical_exists = await _check_physical_repo_exists_async(repo)
    languages = await detect_repo_languages(get_repository_storage_path(repo.path), repo.default_branch or "HEAD") if physical_exists else {}
    return build_repo_response(repo, physical_exists, languages)


async def get_repository_by_path(owner: str, repo_name: str, db: AsyncSession):
    """
    根据 owner/repo 路径获取仓库

    Repository.path 格式固定为 {username}/{repo_name}，且具有唯一约束。

    Args:
        owner: 仓库所有者用户名
        repo_name: 仓库名称
        db: 异步数据库会话

    Returns:
        dict: 仓库信息（包含物理仓库信息）

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    path = f"{owner}/{repo_name}"
    result = await db.execute(select(Repository).filter(Repository.path == path))
    repo = result.scalar_one_or_none()
    if repo is None:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")
    await sync_repository_default_branch(repo, db)
    physical_exists = await _check_physical_repo_exists_async(repo)
    languages = await detect_repo_languages(get_repository_storage_path(repo.path), repo.default_branch or "HEAD") if physical_exists else {}
    return build_repo_response(repo, physical_exists, languages)


async def get_accessible_repository_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """
    获取指定用户可访问的仓库 ID 列表

    包括：公开仓库、用户拥有的仓库、用户作为活跃成员参与的仓库。

    Args:
        db: 异步数据库会话
        user_id: 用户ID

    Returns:
        list[int]: 可访问仓库 ID 列表
    """
    stmt = (
        select(Repository.id)
        .outerjoin(
            RepositoryMember,
            (RepositoryMember.repository_id == Repository.id) &
            (RepositoryMember.user_id == user_id) &
            (RepositoryMember.is_active == True)
        )
        .filter(
            or_(
                Repository.is_public == True,
                Repository.owner_id == user_id,
                RepositoryMember.user_id.is_not(None)
            )
        )
        .distinct()
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


async def get_repositories_by_user(user_id: uuid.UUID, db: AsyncSession):
    """
    根据用户ID获取仓库列表

    Args:
        user_id: 用户ID
        db: 异步数据库会话

    Returns:
        list[dict]: 仓库列表（包含物理仓库信息）
    """
    # 查询用户拥有的仓库
    result = await db.execute(select(Repository).filter(Repository.owner_id == user_id))
    owned_repos = result.scalars().all()

    # 查询用户参与的仓库（通过repository_members表）
    result = await db.execute(
        select(Repository)
        .join(RepositoryMember)
        .filter(RepositoryMember.user_id == user_id)
    )
    member_repos = result.scalars().all()

    # 合并结果，去重
    all_repos = list(set(list(owned_repos) + list(member_repos)))

    return await _enrich_repos_with_physical_status(all_repos)


async def create_repository(repo_data: dict, db: AsyncSession):
    """
    创建新仓库

    Args:
        repo_data: 仓库信息
        db: 异步数据库会话

    Returns:
        dict: 创建的仓库信息

    Raises:
        ValidationException: 请求参数不完整时抛出422异常
        ConflictException: 仓库路径已存在时抛出409异常
    """
    # 验证请求参数
    if "name" not in repo_data or "path" not in repo_data or "owner_id" not in repo_data:
        raise ValidationException(detail="Name, path and owner_id are required", error_code="repository_required_fields")

    # 检查路径是否已存在
    if await exists(db, Repository, {"path": repo_data["path"]}):
        raise ConflictException(detail="Repository path already exists", error_code="repository_path_already_exists")

    # 创建新仓库
    db_repo = Repository(
        name=repo_data["name"],
        path=repo_data["path"],
        description=repo_data.get("description"),
        is_public=repo_data.get("is_public", True),
        owner_id=repo_data["owner_id"],
        default_branch=repo_data.get("default_branch") or "main"
    )

    db.add(db_repo)
    await db.commit()
    await db.refresh(db_repo)

    # 为仓库创建默认分支
    default_branch = Branch(
        name=db_repo.default_branch,
        repository_id=db_repo.id,
        is_protected=True,
        is_default=True
    )
    db.add(default_branch)
    await db.commit()

    # 添加仓库所有者为成员
    owner_member = RepositoryMember(
        repository_id=db_repo.id,
        user_id=db_repo.owner_id,
        role="owner"
    )
    db.add(owner_member)
    await db.commit()

    # 创建物理 Git 仓库（空仓库，无初始提交），HEAD 与默认分支对齐
    try:
        physical_path = get_repository_storage_path(db_repo.path)
        init_bare_repo(physical_path, default_branch=db_repo.default_branch)
        # 启用 HTTP push（git-http-backend 默认禁止 receive-pack）
        enable_receive_pack(physical_path)
    except GitError as e:
        # 物理仓库创建失败，记录错误但不阻止创建
        logger.warning(f"Failed to create physical git repository at {physical_path}: {e}")
    except Exception as e:
        # 其他错误，记录但不阻止
        logger.warning(f"Unexpected error creating git repository: {e}")

    physical_exists = await _check_physical_repo_exists_async(db_repo)

    from services.realtime.room_service import RoomService
    try:
        await RoomService.create_room(db, db_repo.id, db_repo.name, db_repo.owner_id)
    except Exception:
        logger.warning(f"Failed to create room for repository {db_repo.id}")

    return build_repo_response(db_repo, physical_exists)


async def update_repository(repo_id: uuid.UUID, repo_data: dict, db: AsyncSession):
    """
    更新仓库信息

    Args:
        repo_id: 仓库ID
        repo_data: 更新的仓库信息
        db: 异步数据库会话

    Returns:
        dict: 更新后的仓库信息（包含物理仓库信息）

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
        ConflictException: 仓库路径已存在时抛出409异常
    """
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    db_repo = result.scalar_one_or_none()
    if db_repo is None:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")

    # 检查路径是否已存在（如果更新了路径）
    if "path" in repo_data and repo_data["path"] != db_repo.path:
        if await exists(db, Repository, {"path": repo_data["path"]}):
            raise ConflictException(detail="Repository path already exists", error_code="repository_path_already_exists")

    # 更新仓库信息
    for key, value in repo_data.items():
        if hasattr(db_repo, key):
            setattr(db_repo, key, value)

    await db.commit()
    await db.refresh(db_repo)

    # 搜索索引已改为主库持久化（按 repository_id 键），路径变更无需清理：
    # 查询时按提交差异自动增量重建。

    physical_exists = await _check_physical_repo_exists_async(db_repo)
    return build_repo_response(db_repo, physical_exists)


async def delete_repository(repo_id: uuid.UUID, db: AsyncSession):
    """
    删除仓库

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话

    Returns:
        dict: 成功消息

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    db_repo = result.scalar_one_or_none()
    if db_repo is None:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")

    # 获取物理仓库路径（get_repository_storage_path 已包含 .git 后缀）
    physical_path = None
    try:
        physical_path = get_repository_storage_path(db_repo.path)
        if os.path.exists(physical_path):
            shutil.rmtree(physical_path)
            logger.info(f"物理仓库已删除: {physical_path}")
    except Exception as e:
        # 物理仓库删除失败，记录错误但不阻止数据库删除
        path_info = physical_path if physical_path else "unknown"
        logger.warning(f"Failed to delete physical repository at {path_info}: {e}")

    # 先清理搜索索引行（外键约束，必须在删除仓库行之前）
    try:
        from services.search_service import SearchService
        await SearchService().cleanup_index(db, repo_id)
    except Exception as e:
        logger.warning(f"Failed to cleanup search index for repo {repo_id}: {e}")

    from models.realtime_room import RealtimeRoom, RoomMember
    room_result = await db.execute(
        select(RealtimeRoom).filter(RealtimeRoom.repository_id == repo_id)
    )
    room = room_result.scalar_one_or_none()
    if room:
        await db.execute(
            RoomMember.__table__.delete().where(RoomMember.room_id == room.id)
        )
        await db.delete(room)

    await db.delete(db_repo)
    await db.commit()

    return {"message": "Repository deleted successfully"}


async def get_public_repositories(db: AsyncSession):
    """
    获取所有公开仓库

    Args:
        db: 异步数据库会话

    Returns:
        list[dict]: 公开仓库列表（包含物理仓库信息）
    """
    result = await db.execute(select(Repository).filter(Repository.is_public == True))
    repos = result.scalars().all()

    return await _enrich_repos_with_physical_status(list(repos))


async def check_repository_access(repo_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession, required_role: str | None = None):
    """
    检查用户对仓库的访问权限

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 异步数据库会话
        required_role: 所需的最低权限角色（可选）

    Returns:
        bool: 是否有访问权限

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    repo = await get_repository_by_id(repo_id, db)

    # 检查仓库是否公开
    if repo["is_public"] and required_role is None:
        return True

    # 检查用户是否是仓库所有者
    if repo["owner_id"] == user_id:
        return True

    # 检查用户是否是仓库成员
    result = await db.execute(
        select(RepositoryMember)
        .filter(
            RepositoryMember.repository_id == repo_id,
            RepositoryMember.user_id == user_id,
            RepositoryMember.is_active == True
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        return False

    # 如果需要特定角色，检查角色权限
    if required_role:
        user_role_priority = ROLE_PRIORITY.get(member.role, 0)
        required_role_priority = ROLE_PRIORITY.get(required_role, 0)
        return user_role_priority >= required_role_priority

    return True


async def archive_repository(repo_id: uuid.UUID, db: AsyncSession) -> dict:
    """
    归档仓库

    将仓库标记为已归档状态，归档后的仓库不会出现在普通仓库列表中。

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话

    Returns:
        dict: 归档后的仓库信息

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if repo is None:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")
    repo.is_archived = True
    await db.commit()
    await db.refresh(repo)
    physical_exists = await _check_physical_repo_exists_async(repo)
    return build_repo_response(repo, physical_exists)


async def unarchive_repository(repo_id: uuid.UUID, db: AsyncSession) -> dict:
    """
    取消归档仓库

    将已归档的仓库恢复为正常状态，重新出现在仓库列表中。

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话

    Returns:
        dict: 取消归档后的仓库信息

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if repo is None:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")
    repo.is_archived = False
    await db.commit()
    await db.refresh(repo)
    physical_exists = await _check_physical_repo_exists_async(repo)
    return build_repo_response(repo, physical_exists)
