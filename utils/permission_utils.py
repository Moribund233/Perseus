"""
权限检查工具模块

提供统一的权限检查函数，避免在多个服务中重复实现
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from exception import AuthorizationException


async def check_resource_author_or_admin(
    db: AsyncSession,
    resource_author_id: int,
    current_user_id: int,
    repository_id: int,
    action_description: str = "perform this action"
) -> None:
    """
    检查资源操作权限（资源作者或仓库管理员）

    用于检查当前用户是否有权限操作某个资源（如 Issue、PR 等）。
    权限规则：
    1. 资源作者有权限
    2. 仓库所有者或管理员有权限
    3. 其他用户无权限

    Args:
        db: 异步数据库会话
        resource_author_id: 资源作者ID
        current_user_id: 当前用户ID
        repository_id: 仓库ID
        action_description: 操作描述，用于错误信息

    Raises:
        AuthorizationException: 无权限时抛出异常
    """
    # 资源作者有权限
    if resource_author_id == current_user_id:
        return

    # 检查是否是仓库所有者或管理员
    is_admin = await _check_repository_owner_or_admin_internal(
        db, repository_id, current_user_id
    )

    if not is_admin:
        raise AuthorizationException(
            detail=f"You don't have permission to {action_description}"
        )


async def check_repository_owner_or_admin(
    db: AsyncSession,
    repository_id: int,
    user_id: int
) -> bool:
    """
    检查用户是否是仓库所有者或管理员

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        user_id: 用户ID

    Returns:
        bool: 是否是所有者或管理员
    """
    return await _check_repository_owner_or_admin_internal(db, repository_id, user_id)


async def _check_repository_owner_or_admin_internal(
    db: AsyncSession,
    repository_id: int,
    user_id: int
) -> bool:
    """
    内部函数：检查用户是否是仓库所有者或管理员

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        user_id: 用户ID

    Returns:
        bool: 是否是所有者或管理员
    """
    from models.user import User
    from models.repository import Repository
    from models.repository_member import RepositoryMember

    # 检查是否是系统管理员
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and user.is_admin:
        return True

    # 检查是否是仓库所有者
    result = await db.execute(
        select(Repository).filter(Repository.id == repository_id)
    )
    repo = result.scalar_one_or_none()
    if repo and repo.owner_id == user_id:
        return True

    # 检查是否是仓库管理员
    result = await db.execute(
        select(RepositoryMember).filter(
            RepositoryMember.repository_id == repository_id,
            RepositoryMember.user_id == user_id,
            RepositoryMember.role.in_(["owner", "admin"]),
            RepositoryMember.is_active == True
        )
    )
    member = result.scalar_one_or_none()

    return member is not None


async def check_repository_permission(
    db: AsyncSession,
    repository_id: int,
    user_id: int,
    required_roles: list = None
) -> bool:
    """
    检查用户在仓库中的权限

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        user_id: 用户ID
        required_roles: 所需角色列表，默认 ["owner", "admin", "developer"]

    Returns:
        bool: 是否有权限
    """
    from models.user import User
    from models.repository import Repository
    from models.repository_member import RepositoryMember

    if required_roles is None:
        required_roles = ["owner", "admin", "developer"]

    # 检查是否是系统管理员
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and user.is_admin:
        return True

    # 检查是否是仓库所有者
    result = await db.execute(
        select(Repository).filter(Repository.id == repository_id)
    )
    repo = result.scalar_one_or_none()
    if repo and repo.owner_id == user_id:
        return True

    # 检查仓库成员角色
    result = await db.execute(
        select(RepositoryMember).filter(
            RepositoryMember.repository_id == repository_id,
            RepositoryMember.user_id == user_id,
            RepositoryMember.is_active == True
        )
    )
    member = result.scalar_one_or_none()

    if member and member.role in required_roles:
        return True

    return False


async def require_repository_permission(
    db: AsyncSession,
    repository_id: int,
    user_id: int,
    required_roles: list = None,
    action_description: str = "perform this action on this repository"
) -> None:
    """
    要求用户具有仓库权限，无权限时抛出异常

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        user_id: 用户ID
        required_roles: 所需角色列表
        action_description: 操作描述，用于错误信息

    Raises:
        AuthorizationException: 无权限时抛出异常
    """
    has_permission = await check_repository_permission(db, repository_id, user_id, required_roles)

    if not has_permission:
        raise AuthorizationException(
            detail=f"You don't have permission to {action_description}"
        )


async def require_repository_owner_or_admin(
    db: AsyncSession,
    repository_id: int,
    user_id: int,
    action_description: str = "perform this action"
) -> None:
    """
    要求用户是仓库所有者或管理员，无权限时抛出异常

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        user_id: 用户ID
        action_description: 操作描述，用于错误信息

    Raises:
        AuthorizationException: 无权限时抛出异常
    """
    is_owner_or_admin = await check_repository_owner_or_admin(db, repository_id, user_id)

    if not is_owner_or_admin:
        raise AuthorizationException(
            detail=f"You don't have permission to {action_description}"
        )
