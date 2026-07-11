"""
仓库 Fork 服务层

处理仓库 Fork 相关的所有业务逻辑
"""
import os
import shutil
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models import Repository, User
from core.exception import NotFoundException, ValidationException, AuthorizationException
from utils.permission_utils import check_repository_permission
from utils.db_utils import paginate
from utils.response_builder import build_pagination_response


async def fork_repository(
    db: AsyncSession,
    source_repository_id: int,
    user_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_public: Optional[bool] = None,
    repo_root: Optional[str] = None
) -> dict:
    """
    Fork 仓库

    创建源仓库的副本，包括 Git 仓库和所有数据

    Args:
        db: 异步数据库会话
        source_repository_id: 源仓库ID
        user_id: Fork 者用户ID
        name: 新仓库名称（可选，默认为源仓库名称）
        description: 新仓库描述（可选）
        is_public: 是否公开（可选，默认为源仓库设置）
        repo_root: 仓库根目录（可选，用于测试）

    Returns:
        dict: 创建的 Fork 仓库信息

    Raises:
        NotFoundException: 源仓库不存在
        ValidationException: Fork 验证失败
        AuthorizationException: 无权限 Fork
    """
    from services.repository_service import create_repository
    from utils.git_utils import get_repository_path
    from core.config import get_config

    # 获取源仓库
    stmt = select(Repository).filter(Repository.id == source_repository_id)
    result = await db.execute(stmt)
    source_repo = result.scalar_one_or_none()

    if not source_repo:
        raise NotFoundException(detail="Source repository not found")

    # 检查权限（只能 Fork 公开仓库或有权限的私有仓库）
    if not source_repo.is_public:
        has_permission = await check_repository_permission(
            db, source_repository_id, user_id, "read"
        )
        if not has_permission:
            raise AuthorizationException(detail="Not authorized to fork this repository")

    # 获取 Fork 者信息
    user_stmt = select(User).filter(User.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if not user:
        raise NotFoundException(detail="User not found")

    # 检查是否已 Fork 过
    existing_fork = await _get_user_fork(db, source_repository_id, user_id)
    if existing_fork:
        raise ValidationException(
            detail=f"You have already forked this repository to {existing_fork.path}"
        )

    # 确定新仓库名称
    new_name = name or source_repo.name

    # 检查目标路径是否已存在
    new_path = f"{user.username}/{new_name}"
    path_check = await db.execute(
        select(Repository).filter(Repository.path == new_path)
    )
    if path_check.scalar_one_or_none():
        raise ValidationException(
            detail=f"Repository with path '{new_path}' already exists"
        )

    # 确定可见性
    new_is_public = is_public if is_public is not None else source_repo.is_public

    # 确定描述
    new_description = description or source_repo.description

    # 创建新的仓库记录
    forked_repo = Repository(
        name=new_name,
        path=new_path,
        description=new_description,
        is_public=new_is_public,
        owner_id=user_id,
        default_branch=source_repo.default_branch,
        forked_from_id=source_repository_id
    )

    db.add(forked_repo)
    await db.flush()  # 获取 ID

    try:
        # 获取仓库路径
        if repo_root is None:
            config = get_config()
            repo_root = config.storage.repo_root

        # 创建物理仓库（通过 clone --bare）
        # 使用 repo_root 构建源仓库路径，而不是 get_repository_path
        source_repo_path = os.path.abspath(os.path.join(repo_root, source_repo.path))
        forked_repo_path = os.path.abspath(os.path.join(repo_root, new_path))

        # 确保父目录存在
        os.makedirs(os.path.dirname(forked_repo_path), exist_ok=True)

        # 使用 git clone --bare 创建 Fork
        import subprocess
        result = subprocess.run(
            ["git", "clone", "--bare", source_repo_path, forked_repo_path],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode != 0:
            raise ValidationException(detail=f"Failed to fork repository: {result.stderr}")

        # 更新源仓库的 Fork 计数
        source_repo.fork_count += 1

        # 提交事务
        await db.commit()
        await db.refresh(forked_repo)

        # 触发 WebHook
        try:
            from utils.webhook_trigger import trigger_repository_event, build_sender_info
            await trigger_repository_event(
                db=db,
                repository_id=source_repository_id,
                event="forked",
                repository={
                    "id": source_repo.id,
                    "name": source_repo.name,
                    "path": source_repo.path
                },
                sender=build_sender_info(user)
            )
        except Exception:
            # WebHook 失败不影响 Fork 结果
            pass

        return build_fork_response(forked_repo, source_repo)

    except Exception as e:
        # 回滚事务
        await db.rollback()
        # 清理已创建的目录
        if 'forked_repo_path' in locals() and os.path.exists(forked_repo_path):
            shutil.rmtree(forked_repo_path)
        raise


async def get_repository_forks(
    db: AsyncSession,
    repository_id: int,
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """
    获取仓库的所有 Fork

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        page: 页码
        limit: 每页数量

    Returns:
        dict: 包含 Fork 列表和分页信息

    Raises:
        NotFoundException: 仓库不存在
    """
    # 验证仓库存在
    repo_stmt = select(Repository).filter(Repository.id == repository_id)
    result = await db.execute(repo_stmt)
    if not result.scalar_one_or_none():
        raise NotFoundException(detail="Repository not found")

    # 获取 Fork 列表
    stmt = select(Repository).filter(
        Repository.forked_from_id == repository_id
    ).options(
        selectinload(Repository.parent)
    ).order_by(Repository.created_at.desc())

    forks, total = await paginate(db, stmt, page, limit)

    return build_pagination_response(
        items=[build_fork_response(f) for f in forks],
        total=total,
        page=page,
        limit=limit
    )


async def get_user_forks(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """
    获取用户 Fork 的所有仓库

    Args:
        db: 异步数据库会话
        user_id: 用户ID
        page: 页码
        limit: 每页数量

    Returns:
        dict: 包含 Fork 列表和分页信息
    """
    stmt = select(Repository).filter(
        Repository.owner_id == user_id,
        Repository.forked_from_id.isnot(None)
    ).options(
        selectinload(Repository.parent)
    ).order_by(Repository.created_at.desc())

    forks, total = await paginate(db, stmt, page, limit)

    return build_pagination_response(
        items=[build_fork_response(f) for f in forks],
        total=total,
        page=page,
        limit=limit
    )


async def get_fork_source(
    db: AsyncSession,
    repository_id: int
) -> Optional[dict]:
    """
    获取 Fork 的源仓库

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID

    Returns:
        dict: 源仓库信息，如果不是 Fork 则返回 None

    Raises:
        NotFoundException: 仓库不存在
    """
    stmt = select(Repository).filter(Repository.id == repository_id)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()

    if not repo:
        raise NotFoundException(detail="Repository not found")

    if not repo.is_fork():
        return None

    # 获取源仓库
    source_stmt = select(Repository).filter(Repository.id == repo.forked_from_id)
    source_result = await db.execute(source_stmt)
    source_repo = source_result.scalar_one_or_none()

    if not source_repo:
        return None

    return {
        "id": source_repo.id,
        "name": source_repo.name,
        "path": source_repo.path,
        "description": source_repo.description,
        "is_public": source_repo.is_public,
        "owner_id": source_repo.owner_id
    }


async def sync_fork(
    db: AsyncSession,
    repository_id: int,
    user_id: int,
    repo_root: Optional[str] = None
) -> dict:
    """
    同步 Fork 仓库与源仓库

    从源仓库拉取最新更改

    Args:
        db: 异步数据库会话
        repository_id: Fork 仓库ID
        user_id: 当前用户ID
        repo_root: 仓库根目录（可选，用于测试）

    Returns:
        dict: 同步结果

    Raises:
        NotFoundException: 仓库不存在
        ValidationException: 不是 Fork 仓库
        AuthorizationException: 无权限同步
    """
    from utils.git_utils import get_repository_path
    from core.config import get_config

    # 获取 Fork 仓库
    stmt = select(Repository).filter(Repository.id == repository_id)
    result = await db.execute(stmt)
    fork_repo = result.scalar_one_or_none()

    if not fork_repo:
        raise NotFoundException(detail="Repository not found")

    # 检查是否为 Fork
    if not fork_repo.is_fork():
        raise ValidationException(detail="This repository is not a fork")

    # 检查权限
    if fork_repo.owner_id != user_id:
        raise AuthorizationException(detail="Not authorized to sync this repository")

    # 获取源仓库
    source_stmt = select(Repository).filter(Repository.id == fork_repo.forked_from_id)
    source_result = await db.execute(source_stmt)
    source_repo = source_result.scalar_one_or_none()

    if not source_repo:
        raise NotFoundException(detail="Source repository not found")

    # 获取仓库路径
    if repo_root is None:
        config = get_config()
        repo_root = config.storage.repo_root

    fork_repo_path = await get_repository_path(db, repository_id)
    source_repo_path = await get_repository_path(db, source_repo.id)

    # 执行 git fetch
    import subprocess
    result = subprocess.run(
        ["git", "fetch", "origin"],
        cwd=fork_repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )

    if result.returncode != 0:
        raise ValidationException(detail=f"Failed to sync repository: {result.stderr}")

    return {
        "success": True,
        "message": "Repository synced successfully",
        "fork_id": repository_id,
        "source_id": source_repo.id
    }


async def _get_user_fork(
    db: AsyncSession,
    source_repository_id: int,
    user_id: int
) -> Optional[Repository]:
    """
    检查用户是否已 Fork 过指定仓库

    Args:
        db: 异步数据库会话
        source_repository_id: 源仓库ID
        user_id: 用户ID

    Returns:
        Repository: 已存在的 Fork 仓库，如果没有则返回 None
    """
    stmt = select(Repository).filter(
        Repository.forked_from_id == source_repository_id,
        Repository.owner_id == user_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def build_fork_response(fork_repo: Repository, source_repo: Optional[Repository] = None) -> dict:
    """
    构建 Fork 响应数据

    Args:
        fork_repo: Fork 仓库模型实例
        source_repo: 源仓库模型实例（可选）

    Returns:
        dict: 响应数据
    """
    data = {
        "id": fork_repo.id,
        "name": fork_repo.name,
        "path": fork_repo.path,
        "description": fork_repo.description,
        "is_public": fork_repo.is_public,
        "owner_id": fork_repo.owner_id,
        "default_branch": fork_repo.default_branch,
        "is_fork": fork_repo.is_fork(),
        "forked_from_id": fork_repo.forked_from_id,
        "created_at": fork_repo.created_at.isoformat() if fork_repo.created_at else None,
        "updated_at": fork_repo.updated_at.isoformat() if fork_repo.updated_at else None
    }

    if source_repo:
        data["source"] = {
            "id": source_repo.id,
            "name": source_repo.name,
            "path": source_repo.path,
            "owner_id": source_repo.owner_id
        }
    elif fork_repo.parent:
        data["source"] = {
            "id": fork_repo.parent.id,
            "name": fork_repo.parent.name,
            "path": fork_repo.parent.path,
            "owner_id": fork_repo.parent.owner_id
        }

    return data
