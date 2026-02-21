"""
仓库服务层

处理与Git仓库相关的所有业务逻辑
"""
import os
import shutil
import asyncio
import logging
from typing import Dict, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Repository
from models.branch import Branch
from models.repository_member import RepositoryMember
from exception import ValidationException, NotFoundException, ConflictException
from utils.git_utils import init_bare_repo, get_repository_storage_path, repo_exists_async, GitError
from utils.response_builder import build_repo_response
from utils.db_utils import exists

# 日志记录器
logger = logging.getLogger(__name__)

# 常量定义
ROLE_PRIORITY = {
    "owner": 4,
    "admin": 3,
    "developer": 2,
    "readonly": 1
}

# 物理仓库存在状态缓存（仓库ID -> (存在状态, 缓存时间)）
# 缓存有效期30秒，减少频繁的磁盘IO检查
_repo_exists_cache: Dict[int, Tuple[bool, datetime]] = {}
_REPO_EXISTS_CACHE_TTL_SECONDS = 30


def _get_cached_repo_exists(repo_id: int) -> Tuple[bool, bool]:
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


def _set_cached_repo_exists(repo_id: int, exists: bool) -> None:
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


async def get_repositories(db: AsyncSession, limit: int = 100):
    """
    获取所有仓库

    Args:
        db: 异步数据库会话
        limit: 最大返回数量，默认100

    Returns:
        list[dict]: 仓库列表（包含物理仓库信息）
    """
    result = await db.execute(
        select(Repository)
        .order_by(Repository.updated_at.desc())
        .limit(limit)
    )
    repos = result.scalars().all()

    # 并行检查所有仓库的物理存在状态（异步IO优化）
    physical_checks = await asyncio.gather(
        *[_check_physical_repo_exists_async(repo) for repo in repos],
        return_exceptions=True
    )

    return [
        build_repo_response(repo, check if not isinstance(check, Exception) else False)
        for repo, check in zip(repos, physical_checks)
    ]


async def get_repository_by_id(repo_id: int, db: AsyncSession):
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
        raise NotFoundException(detail="Repository not found")
    physical_exists = await _check_physical_repo_exists_async(repo)
    return build_repo_response(repo, physical_exists)


async def get_repositories_by_user(user_id: int, db: AsyncSession):
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

    # 并行检查所有仓库的物理存在状态（异步IO优化）
    physical_checks = await asyncio.gather(
        *[_check_physical_repo_exists_async(repo) for repo in all_repos],
        return_exceptions=True
    )

    return [
        build_repo_response(repo, check if not isinstance(check, Exception) else False)
        for repo, check in zip(all_repos, physical_checks)
    ]


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
        raise ValidationException(detail="Name, path and owner_id are required")

    # 检查路径是否已存在
    if await exists(db, Repository, {"path": repo_data["path"]}):
        raise ConflictException(detail="Repository path already exists")

    # 创建新仓库
    db_repo = Repository(
        name=repo_data["name"],
        path=repo_data["path"],
        description=repo_data.get("description"),
        is_public=repo_data.get("is_public", True),
        owner_id=repo_data["owner_id"],
        default_branch=repo_data.get("default_branch", "master")
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

    # 创建物理 Git 仓库（空仓库，无初始提交）
    try:
        physical_path = get_repository_storage_path(db_repo.path)
        init_bare_repo(physical_path)
    except GitError as e:
        # 物理仓库创建失败，记录错误但不阻止创建
        logger.warning(f"Failed to create physical git repository at {physical_path}: {e}")
    except Exception as e:
        # 其他错误，记录但不阻止
        logger.warning(f"Unexpected error creating git repository: {e}")

    physical_exists = await _check_physical_repo_exists_async(db_repo)
    return build_repo_response(db_repo, physical_exists)


async def update_repository(repo_id: int, repo_data: dict, db: AsyncSession):
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
        raise NotFoundException(detail="Repository not found")

    # 检查路径是否已存在（如果更新了路径）
    if "path" in repo_data and repo_data["path"] != db_repo.path:
        if await exists(db, Repository, {"path": repo_data["path"]}):
            raise ConflictException(detail="Repository path already exists")

    # 更新仓库信息
    for key, value in repo_data.items():
        if hasattr(db_repo, key):
            setattr(db_repo, key, value)

    await db.commit()
    await db.refresh(db_repo)

    physical_exists = await _check_physical_repo_exists_async(db_repo)
    return build_repo_response(db_repo, physical_exists)


async def delete_repository(repo_id: int, db: AsyncSession):
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
        raise NotFoundException(detail="Repository not found")

    # 获取物理仓库路径
    try:
        physical_path = get_repository_storage_path(db_repo.path)
        if os.path.exists(physical_path):
            shutil.rmtree(physical_path)
            logger.info(f"物理仓库已删除: {physical_path}")
    except Exception as e:
        # 物理仓库删除失败，记录错误但不阻止数据库删除
        logger.warning(f"Failed to delete physical repository at {physical_path}: {e}")

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

    # 并行检查所有仓库的物理存在状态（异步IO优化）
    physical_checks = await asyncio.gather(
        *[_check_physical_repo_exists_async(repo) for repo in repos],
        return_exceptions=True
    )

    return [
        build_repo_response(repo, check if not isinstance(check, Exception) else False)
        for repo, check in zip(repos, physical_checks)
    ]


async def check_repository_access(repo_id: int, user_id: int, db: AsyncSession, required_role: str = None):
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
