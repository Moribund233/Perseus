"""
提交服务层

处理与Git提交相关的所有业务逻辑
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.commit import Commit
from models.branch import Branch
from core.exception import ValidationException, NotFoundException, ConflictException


async def get_commits(repo_id: int, db: AsyncSession, limit: int = 100, offset: int = 0):
    """
    获取仓库的提交记录

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话
        limit: 返回记录数量限制（默认100）
        offset: 记录偏移量（默认0）

    Returns:
        list[Commit]: 提交记录列表
    """
    result = await db.execute(
        select(Commit)
        .filter(Commit.repository_id == repo_id)
        .order_by(Commit.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def get_commits_by_branch(branch_id: int, db: AsyncSession, limit: int = 100, offset: int = 0):
    """
    获取特定分支的提交记录

    Args:
        branch_id: 分支ID
        db: 异步数据库会话
        limit: 返回记录数量限制（默认100）
        offset: 记录偏移量（默认0）

    Returns:
        list[Commit]: 提交记录列表
    """
    result = await db.execute(
        select(Commit)
        .filter(Commit.branch_id == branch_id)
        .order_by(Commit.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def get_commit_by_hash(repo_id: int, commit_hash: str, db: AsyncSession):
    """
    根据提交哈希获取提交详情

    Args:
        repo_id: 仓库ID
        commit_hash: 提交哈希值
        db: 异步数据库会话

    Returns:
        Commit: 提交详情

    Raises:
        NotFoundException: 提交不存在时抛出404异常
    """
    result = await db.execute(
        select(Commit).filter(
            Commit.repository_id == repo_id,
            Commit.hash == commit_hash
        )
    )
    commit = result.scalar_one_or_none()

    if commit is None:
        raise NotFoundException(detail=f"Commit '{commit_hash}' not found")

    return commit


async def get_commit_by_id(commit_id: int, db: AsyncSession):
    """
    根据ID获取提交详情

    Args:
        commit_id: 提交ID
        db: 异步数据库会话

    Returns:
        Commit: 提交详情

    Raises:
        NotFoundException: 提交不存在时抛出404异常
    """
    result = await db.execute(select(Commit).filter(Commit.id == commit_id))
    commit = result.scalar_one_or_none()
    if commit is None:
        raise NotFoundException(detail="Commit not found")
    return commit


async def create_commit(commit_data: dict, db: AsyncSession):
    """
    创建提交记录

    Args:
        commit_data: 提交信息
        db: 异步数据库会话

    Returns:
        Commit: 创建的提交记录

    Raises:
        ValidationException: 请求参数不完整时抛出422异常
        ConflictException: 提交哈希已存在时抛出409异常
        NotFoundException: 分支不存在时抛出404异常
    """
    # 验证请求参数
    required_fields = ["hash", "repository_id", "branch_id", "author_name", "author_email", "commit_message"]
    for field in required_fields:
        if field not in commit_data:
            raise ValidationException(detail=f"{field} is required")

    # 检查提交哈希是否已存在
    result = await db.execute(select(Commit).filter(Commit.hash == commit_data["hash"]))
    existing_commit = result.scalar_one_or_none()
    if existing_commit:
        raise ConflictException(detail=f"Commit hash '{commit_data['hash']}' already exists")

    # 检查分支是否存在
    result = await db.execute(select(Branch).filter(Branch.id == commit_data["branch_id"]))
    branch = result.scalar_one_or_none()
    if not branch:
        raise NotFoundException(detail="Branch not found")

    # 创建新提交记录
    db_commit = Commit(
        hash=commit_data["hash"],
        repository_id=commit_data["repository_id"],
        branch_id=commit_data["branch_id"],
        author_name=commit_data["author_name"],
        author_email=commit_data["author_email"],
        committer_name=commit_data.get("committer_name", commit_data["author_name"]),
        committer_email=commit_data.get("committer_email", commit_data["author_email"]),
        commit_message=commit_data["commit_message"],
        commit_date=commit_data.get("commit_date"),
        parent_hashes=commit_data.get("parent_hashes")
    )

    db.add(db_commit)
    await db.commit()
    await db.refresh(db_commit)

    return db_commit


async def get_commit_history(repo_id: int, db: AsyncSession, branch_name: str = None, limit: int = 50):
    """
    获取仓库的提交历史树

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话
        branch_name: 分支名称（可选，默认获取所有分支）
        limit: 返回记录数量限制（默认50）

    Returns:
        list[Commit]: 提交历史列表
    """
    stmt = select(Commit).filter(Commit.repository_id == repo_id)

    if branch_name:
        # 根据分支名称过滤
        result = await db.execute(
            select(Branch).filter(
                Branch.repository_id == repo_id,
                Branch.name == branch_name
            )
        )
        branch = result.scalar_one_or_none()
        if branch:
            stmt = stmt.filter(Commit.branch_id == branch.id)

    result = await db.execute(stmt.order_by(Commit.created_at.desc()).limit(limit))
    return result.scalars().all()


async def count_repo_commits(repo_id: int, db: AsyncSession):
    """
    统计仓库的提交数量

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话

    Returns:
        int: 提交数量
    """
    result = await db.execute(
        select(func.count()).select_from(Commit).filter(Commit.repository_id == repo_id)
    )
    return result.scalar()


async def count_branch_commits(branch_id: int, db: AsyncSession):
    """
    统计分支的提交数量

    Args:
        branch_id: 分支ID
        db: 异步数据库会话

    Returns:
        int: 提交数量
    """
    result = await db.execute(
        select(func.count()).select_from(Commit).filter(Commit.branch_id == branch_id)
    )
    return result.scalar()


async def get_latest_commit(repo_id: int, db: AsyncSession):
    """
    获取仓库的最新提交

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话

    Returns:
        Commit: 最新提交记录

    Raises:
        NotFoundException: 没有提交记录时抛出404异常
    """
    result = await db.execute(
        select(Commit)
        .filter(Commit.repository_id == repo_id)
        .order_by(Commit.created_at.desc())
    )
    commit = result.scalars().first()
    if commit is None:
        raise NotFoundException(detail="No commits found in this repository")
    return commit


async def get_latest_commit_by_branch(branch_id: int, db: AsyncSession):
    """
    获取分支的最新提交

    Args:
        branch_id: 分支ID
        db: 异步数据库会话

    Returns:
        Commit: 最新提交记录

    Raises:
        NotFoundException: 没有提交记录时抛出404异常
    """
    result = await db.execute(
        select(Commit)
        .filter(Commit.branch_id == branch_id)
        .order_by(Commit.created_at.desc())
    )
    commit = result.scalars().first()
    if commit is None:
        raise NotFoundException(detail="No commits found in this branch")
    return commit


async def search_commits(repo_id: int, search_query: str, db: AsyncSession, limit: int = 50):
    """
    搜索提交记录

    Args:
        repo_id: 仓库ID
        search_query: 搜索关键词
        db: 异步数据库会话
        limit: 返回记录数量限制（默认50）

    Returns:
        list[Commit]: 匹配的提交记录列表
    """
    result = await db.execute(
        select(Commit)
        .filter(
            Commit.repository_id == repo_id,
            Commit.commit_message.contains(search_query)
        )
        .order_by(Commit.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_commits_by_author(repo_id: int, author_email: str, db: AsyncSession, limit: int = 50):
    """
    根据作者邮箱获取提交记录

    Args:
        repo_id: 仓库ID
        author_email: 作者邮箱
        db: 异步数据库会话
        limit: 返回记录数量限制（默认50）

    Returns:
        list[Commit]: 提交记录列表
    """
    result = await db.execute(
        select(Commit)
        .filter(
            Commit.repository_id == repo_id,
            Commit.author_email == author_email
        )
        .order_by(Commit.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
