"""
仓库成员服务层

处理与仓库成员相关的所有业务逻辑
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.repository_member import RepositoryMember
from core.exception import ValidationException, NotFoundException, ConflictException, AuthorizationException
from core.constants import ROLE_PRIORITY, VALID_ROLES


async def get_repository_members(repo_id: int, db: AsyncSession):
    """
    获取仓库的所有成员

    Args:
        repo_id: 仓库ID
        db: 异步数据库会话

    Returns:
        list[RepositoryMember]: 仓库成员列表
    """
    result = await db.execute(
        select(RepositoryMember).filter(RepositoryMember.repository_id == repo_id)
    )
    return result.scalars().all()


async def get_repository_member(repo_id: int, user_id: int, db: AsyncSession):
    """
    获取仓库的特定成员

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 异步数据库会话

    Returns:
        RepositoryMember: 仓库成员信息

    Raises:
        NotFoundException: 成员不存在时抛出404异常
    """
    result = await db.execute(
        select(RepositoryMember).filter(
            RepositoryMember.repository_id == repo_id,
            RepositoryMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()

    if member is None:
        raise NotFoundException(detail="Member not found in this repository")

    return member


async def add_repository_member(repo_id: int, member_data: dict, db: AsyncSession, operator_id: int = None):
    """
    添加仓库成员

    Args:
        repo_id: 仓库ID
        member_data: 成员信息
        db: 异步数据库会话
        operator_id: 操作人用户ID（可选，用于审计）

    Returns:
        RepositoryMember: 添加的成员信息

    Raises:
        ValidationException: 请求参数不完整时抛出422异常
        ConflictException: 成员已存在时抛出409异常
        NotFoundException: 用户不存在时抛出404异常
    """
    # 验证请求参数
    if "user_id" not in member_data:
        raise ValidationException(detail="User ID is required")

    # 检查用户是否存在
    from models.user import User
    result = await db.execute(select(User).filter(User.id == member_data["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException(detail="User not found")

    # 检查成员是否已存在
    result = await db.execute(
        select(RepositoryMember).filter(
            RepositoryMember.repository_id == repo_id,
            RepositoryMember.user_id == member_data["user_id"]
        )
    )
    existing_member = result.scalar_one_or_none()

    if existing_member:
        raise ConflictException(detail="User is already a member of this repository")

    # 创建新成员
    db_member = RepositoryMember(
        repository_id=repo_id,
        user_id=member_data["user_id"],
        role=member_data.get("role", "developer"),
        is_active=member_data.get("is_active", True)
    )

    db.add(db_member)
    await db.commit()
    await db.refresh(db_member)

    return db_member


async def update_repository_member(repo_id: int, user_id: int, member_data: dict, db: AsyncSession, operator_id: int = None):
    """
    更新仓库成员信息

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        member_data: 更新的成员信息
        db: 异步数据库会话
        operator_id: 操作人用户ID（可选，用于审计）

    Returns:
        RepositoryMember: 更新后的成员信息

    Raises:
        NotFoundException: 成员不存在时抛出404异常
    """
    db_member = await get_repository_member(repo_id, user_id, db)

    # 更新成员信息
    for key, value in member_data.items():
        if hasattr(db_member, key):
            setattr(db_member, key, value)

    await db.commit()
    await db.refresh(db_member)

    return db_member


async def remove_repository_member(repo_id: int, user_id: int, db: AsyncSession, operator_id: int = None):
    """
    删除仓库成员

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 异步数据库会话
        operator_id: 操作人用户ID（可选，用于审计）

    Returns:
        dict: 成功消息

    Raises:
        NotFoundException: 成员不存在时抛出404异常
        AuthorizationException: 无法删除仓库所有者时抛出403异常
    """
    db_member = await get_repository_member(repo_id, user_id, db)

    # 检查是否是仓库所有者
    if db_member.role == "owner":
        raise AuthorizationException(detail="Cannot remove repository owner")

    await db.delete(db_member)
    await db.commit()

    return {"message": "Member removed successfully"}


async def update_member_role(repo_id: int, user_id: int, role: str, db: AsyncSession, operator_id: int = None):
    """
    更新成员角色

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        role: 新角色
        db: 异步数据库会话
        operator_id: 操作人用户ID（可选，用于审计）

    Returns:
        RepositoryMember: 更新后的成员信息

    Raises:
        NotFoundException: 成员不存在时抛出404异常
        ValidationException: 角色无效时抛出422异常
    """
    # 验证角色是否有效
    if role not in VALID_ROLES:
        raise ValidationException(detail=f"Invalid role. Valid roles are: {', '.join(VALID_ROLES)}")

    return await update_repository_member(repo_id, user_id, {"role": role}, db, operator_id=operator_id)


async def get_user_repositories(user_id: int, db: AsyncSession):
    """
    获取用户参与的所有仓库

    Args:
        user_id: 用户ID
        db: 异步数据库会话

    Returns:
        list[Repository]: 用户参与的仓库列表
    """
    from models.repository import Repository
    result = await db.execute(
        select(Repository)
        .join(RepositoryMember)
        .filter(
            RepositoryMember.user_id == user_id,
            RepositoryMember.is_active == True
        )
    )
    return result.scalars().all()


async def check_member_permission(repo_id: int, user_id: int, required_role: str, db: AsyncSession):
    """
    检查用户在仓库中的权限

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        required_role: 所需的最低权限角色
        db: 异步数据库会话

    Returns:
        bool: 是否有足够的权限

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    # 检查仓库是否存在
    from models.repository import Repository
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found")

    # 检查用户是否是仓库所有者
    if repo.owner_id == user_id:
        return True

    # 检查用户是否是仓库成员
    result = await db.execute(
        select(RepositoryMember).filter(
            RepositoryMember.repository_id == repo_id,
            RepositoryMember.user_id == user_id,
            RepositoryMember.is_active == True
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        return False

    # 角色优先级：owner > admin > developer > readonly
    user_role_priority = ROLE_PRIORITY.get(member.role, 0)
    required_role_priority = ROLE_PRIORITY.get(required_role, 0)

    return user_role_priority >= required_role_priority


async def activate_repository_member(repo_id: int, user_id: int, db: AsyncSession, operator_id: int = None):
    """
    激活仓库成员

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 异步数据库会话
        operator_id: 操作人用户ID（可选，用于审计）

    Returns:
        RepositoryMember: 更新后的成员信息

    Raises:
        NotFoundException: 成员不存在时抛出404异常
    """
    return await update_repository_member(repo_id, user_id, {"is_active": True}, db, operator_id=operator_id)


async def deactivate_repository_member(repo_id: int, user_id: int, db: AsyncSession, operator_id: int = None):
    """
    停用仓库成员

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 异步数据库会话
        operator_id: 操作人用户ID（可选，用于审计）

    Returns:
        RepositoryMember: 更新后的成员信息

    Raises:
        NotFoundException: 成员不存在时抛出404异常
        AuthorizationException: 无法停用仓库所有者时抛出403异常
    """
    db_member = await get_repository_member(repo_id, user_id, db)

    # 检查是否是仓库所有者
    if db_member.role == "owner":
        raise AuthorizationException(detail="Cannot deactivate repository owner")

    return await update_repository_member(repo_id, user_id, {"is_active": False}, db, operator_id=operator_id)
