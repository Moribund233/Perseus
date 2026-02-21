"""
分支服务层

处理与Git分支相关的所有业务逻辑
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.branch import Branch
from models.repository import Repository
from exception import ValidationException, NotFoundException, ConflictException, AuthorizationException


async def get_branches(repo_id: int, db: AsyncSession):
    """
    获取仓库的所有分支

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话

    Returns:
        list[Branch]: 分支列表
    """
    result = await db.execute(select(Branch).filter(Branch.repository_id == repo_id))
    return result.scalars().all()


async def get_branch(repo_id: int, branch_name: str, db: AsyncSession):
    """
    获取仓库的特定分支

    Args:
        repo_id: 仓库ID
        branch_name: 分支名称
        db: 异步数据库会话

    Returns:
        Branch: 分支信息

    Raises:
        NotFoundException: 分支不存在时抛出404异常
    """
    result = await db.execute(
        select(Branch).filter(
            Branch.repository_id == repo_id,
            Branch.name == branch_name
        )
    )
    branch = result.scalar_one_or_none()

    if branch is None:
        raise NotFoundException(detail=f"Branch '{branch_name}' not found")

    return branch


async def get_branch_by_id(branch_id: int, db: AsyncSession):
    """
    根据ID获取分支

    Args:
        branch_id: 分支ID
        db: 异步数据库会话

    Returns:
        Branch: 分支信息

    Raises:
        NotFoundException: 分支不存在时抛出404异常
    """
    result = await db.execute(select(Branch).filter(Branch.id == branch_id))
    branch = result.scalar_one_or_none()
    if branch is None:
        raise NotFoundException(detail="Branch not found")
    return branch


async def create_branch(repo_id: int, branch_data: dict, db: AsyncSession):
    """
    创建新分支

    Args:
        repo_id: 仓库ID
        branch_data: 分支信息
        db: 异步数据库会话

    Returns:
        Branch: 创建的分支信息

    Raises:
        ValidationException: 请求参数不完整时抛出422异常
        ConflictException: 分支名称已存在时抛出409异常
    """
    # 验证请求参数
    if "name" not in branch_data:
        raise ValidationException(detail="Branch name is required")

    # 检查分支名称是否已存在
    result = await db.execute(
        select(Branch).filter(
            Branch.repository_id == repo_id,
            Branch.name == branch_data["name"]
        )
    )
    existing_branch = result.scalar_one_or_none()

    if existing_branch:
        raise ConflictException(detail=f"Branch '{branch_data['name']}' already exists")

    # 创建新分支
    db_branch = Branch(
        name=branch_data["name"],
        repository_id=repo_id,
        is_protected=branch_data.get("is_protected", False),
        require_code_review=branch_data.get("require_code_review", False),
        require_status_checks=branch_data.get("require_status_checks", False),
        is_default=branch_data.get("is_default", False)
    )

    db.add(db_branch)
    await db.commit()
    await db.refresh(db_branch)

    # 如果设置为默认分支，更新其他分支的默认状态
    if db_branch.is_default:
        await set_default_branch(repo_id, db_branch.id, db)

    return db_branch


async def update_branch(repo_id: int, branch_name: str, branch_data: dict, db: AsyncSession):
    """
    更新分支信息

    Args:
        repo_id: 仓库ID
        branch_name: 分支名称
        branch_data: 更新的分支信息
        db: 异步数据库会话

    Returns:
        Branch: 更新后的分支信息

    Raises:
        NotFoundException: 分支不存在时抛出404异常
    """
    db_branch = await get_branch(repo_id, branch_name, db)

    # 更新分支信息
    for key, value in branch_data.items():
        if hasattr(db_branch, key):
            setattr(db_branch, key, value)

    await db.commit()
    await db.refresh(db_branch)

    # 如果设置为默认分支，更新其他分支的默认状态
    if db_branch.is_default:
        await set_default_branch(repo_id, db_branch.id, db)

    return db_branch


async def delete_branch(repo_id: int, branch_name: str, db: AsyncSession):
    """
    删除分支

    Args:
        repo_id: 仓库ID
        branch_name: 分支名称
        db: 异步数据库会话

    Returns:
        dict: 成功消息

    Raises:
        NotFoundException: 分支不存在时抛出404异常
        AuthorizationException: 无法删除默认分支时抛出403异常
    """
    db_branch = await get_branch(repo_id, branch_name, db)

    # 检查是否是默认分支
    if db_branch.is_default:
        raise AuthorizationException(detail="Cannot delete default branch")

    await db.delete(db_branch)
    await db.commit()

    return {"message": f"Branch '{branch_name}' deleted successfully"}


async def set_default_branch(repo_id: int, branch_id: int, db: AsyncSession):
    """
    设置默认分支

    Args:
        repo_id: 仓库ID
        branch_id: 分支ID
        db: 异步数据库会话

    Returns:
        dict: 成功消息

    Raises:
        NotFoundException: 分支不存在时抛出404异常
    """
    # 检查分支是否存在
    branch = await get_branch_by_id(branch_id, db)

    # 确保分支属于指定仓库
    if branch.repository_id != repo_id:
        raise NotFoundException(detail="Branch does not belong to this repository")

    # 将所有分支的默认状态设置为False
    await db.execute(
        select(Branch).filter(Branch.repository_id == repo_id)
    )
    # 使用update语句
    from sqlalchemy import update
    await db.execute(
        update(Branch)
        .where(Branch.repository_id == repo_id)
        .values(is_default=False)
    )

    # 设置指定分支为默认分支
    branch.is_default = True
    await db.commit()

    # 更新仓库的默认分支名称
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if repo:
        repo.default_branch = branch.name
        await db.commit()

    return {"message": f"Default branch set to '{branch.name}'"}


async def protect_branch(repo_id: int, branch_name: str, protection_settings: dict, db: AsyncSession):
    """
    保护分支

    Args:
        repo_id: 仓库ID
        branch_name: 分支名称
        protection_settings: 保护设置
        db: 异步数据库会话

    Returns:
        Branch: 更新后的分支信息

    Raises:
        NotFoundException: 分支不存在时抛出404异常
    """
    db_branch = await get_branch(repo_id, branch_name, db)

    # 更新保护设置
    db_branch.is_protected = True
    db_branch.require_code_review = protection_settings.get("require_code_review", False)
    db_branch.require_status_checks = protection_settings.get("require_status_checks", False)

    await db.commit()
    await db.refresh(db_branch)

    return db_branch


async def unprotect_branch(repo_id: int, branch_name: str, db: AsyncSession):
    """
    取消分支保护

    Args:
        repo_id: 仓库ID
        branch_name: 分支名称
        db: 异步数据库会话

    Returns:
        Branch: 更新后的分支信息

    Raises:
        NotFoundException: 分支不存在时抛出404异常
    """
    db_branch = await get_branch(repo_id, branch_name, db)

    db_branch.is_protected = False
    db_branch.require_code_review = False
    db_branch.require_status_checks = False

    await db.commit()
    await db.refresh(db_branch)

    return db_branch


async def get_default_branch(repo_id: int, db: AsyncSession):
    """
    获取默认分支

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话

    Returns:
        Branch: 默认分支信息

    Raises:
        NotFoundException: 没有默认分支时抛出404异常
    """
    result = await db.execute(
        select(Branch).filter(
            Branch.repository_id == repo_id,
            Branch.is_default == True
        )
    )
    branch = result.scalar_one_or_none()

    if branch is None:
        raise NotFoundException(detail="Default branch not found")

    return branch


async def check_branch_protection(repo_id: int, branch_name: str, db: AsyncSession):
    """
    检查分支保护状态

    Args:
        repo_id: 仓库ID
        branch_name: 分支名称
        db: 异步数据库会话

    Returns:
        dict: 分支保护状态信息

    Raises:
        NotFoundException: 分支不存在时抛出404异常
    """
    branch = await get_branch(repo_id, branch_name, db)

    return {
        "is_protected": branch.is_protected,
        "require_code_review": branch.require_code_review,
        "require_status_checks": branch.require_status_checks
    }
