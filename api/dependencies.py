"""
API 依赖模块

提供可复用的 FastAPI 依赖函数，如认证、权限检查等
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Union

from models.db import get_db
from models.user import User
from services.token_service import verify_token
from api.local_auth import get_local_auth_user, LocalUser

# 使用 HTTPBearer 从 Authorization 头中提取 token
# auto_error=False 允许在没有 Authorization 头时继续处理（用于本地认证回退）
security = HTTPBearer(auto_error=False)
security_strict = HTTPBearer(auto_error=True)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Union[User, LocalUser]:
    """
    获取当前认证用户（支持本地认证和JWT认证）

    优先尝试本地认证（通过 X-LanGit-Local 头），如果失败则尝试 JWT Token 认证

    Args:
        request: FastAPI 请求对象
        credentials: HTTP 认证凭证
        db: 数据库会话

    Returns:
        Union[User, LocalUser]: 当前认证用户对象（本地用户或数据库用户）

    Raises:
        HTTPException: 认证失败时抛出 401 异常
    """
    # 首先尝试本地认证
    local_user = await get_local_auth_user(request, credentials)
    if local_user:
        return local_user

    # 本地认证失败，尝试 JWT 认证
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    token_data = verify_token(token, token_type="access")

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == token_data.user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户（简化版，仅检查用户是否激活）

    Args:
        current_user: 当前认证用户

    Returns:
        User: 当前活跃用户对象
    """
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前管理员用户

    Args:
        current_user: 当前认证用户

    Returns:
        User: 当前管理员用户对象

    Raises:
        HTTPException: 用户不是管理员时抛出 403 异常
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


# ==================== 仓库权限检查工具函数 ====================

async def check_repository_permission(
    db: Session,
    repository_id: int,
    user_id: int,
    required_roles: list = None
) -> bool:
    """
    检查用户在仓库中的权限

    Args:
        db: 数据库会话
        repository_id: 仓库ID
        user_id: 用户ID
        required_roles: 所需角色列表，默认 ["owner", "admin", "developer"]

    Returns:
        bool: 是否有权限
    """
    from models.repository import Repository
    from models.repository_member import RepositoryMember

    if required_roles is None:
        required_roles = ["owner", "admin", "developer"]

    # 检查是否是系统管理员
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.is_admin:
        return True

    # 检查是否是仓库所有者
    repo = db.query(Repository).filter(Repository.id == repository_id).first()
    if repo and repo.owner_id == user_id:
        return True

    # 检查仓库成员角色
    member = db.query(RepositoryMember).filter(
        RepositoryMember.repository_id == repository_id,
        RepositoryMember.user_id == user_id,
        RepositoryMember.is_active == True
    ).first()

    if member and member.role in required_roles:
        return True

    return False


async def require_repository_permission(
    repository_id: int,
    user_id: int,
    db: Session,
    required_roles: list = None
):
    """
    要求用户具有仓库权限，无权限时抛出异常

    Args:
        repository_id: 仓库ID
        user_id: 用户ID
        db: 数据库会话
        required_roles: 所需角色列表

    Raises:
        HTTPException: 无权限时抛出 403 异常
    """
    has_permission = await check_repository_permission(
        db, repository_id, user_id, required_roles
    )

    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this action on this repository"
        )


async def check_repository_owner_or_admin(
    db: Session,
    repository_id: int,
    user_id: int
) -> bool:
    """
    检查用户是否是仓库所有者或管理员

    Args:
        db: 数据库会话
        repository_id: 仓库ID
        user_id: 用户ID

    Returns:
        bool: 是否是所有者或管理员
    """
    from models.repository import Repository
    from models.repository_member import RepositoryMember

    # 检查是否是系统管理员
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.is_admin:
        return True

    # 检查是否是仓库所有者
    repo = db.query(Repository).filter(Repository.id == repository_id).first()
    if repo and repo.owner_id == user_id:
        return True

    # 检查是否是仓库管理员
    member = db.query(RepositoryMember).filter(
        RepositoryMember.repository_id == repository_id,
        RepositoryMember.user_id == user_id,
        RepositoryMember.role.in_(["owner", "admin"]),
        RepositoryMember.is_active == True
    ).first()

    return member is not None


# ==================== FastAPI 依赖注入函数 ====================

def require_repository_permission_dependency(
    required_roles: list = None,
    action_description: str = "perform this action"
):
    """
    创建仓库权限检查依赖

    用于 FastAPI 路由中检查用户是否有仓库操作权限

    Args:
        required_roles: 所需角色列表
        action_description: 操作描述

    Returns:
        依赖函数
    """
    async def check_permission(
        repo_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        from utils.permission_utils import require_repository_permission_sync
        require_repository_permission_sync(
            db, repo_id, current_user.id, required_roles, action_description
        )
        return current_user
    return check_permission


def require_repository_owner_dependency(
    action_description: str = "perform this action"
):
    """
    创建仓库所有者权限检查依赖

    用于 FastAPI 路由中检查用户是否是仓库所有者或管理员

    Args:
        action_description: 操作描述

    Returns:
        依赖函数
    """
    async def check_owner(
        repo_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        from utils.permission_utils import require_repository_owner_or_admin_sync
        require_repository_owner_or_admin_sync(
            db, repo_id, current_user.id, action_description
        )
        return current_user
    return check_owner
