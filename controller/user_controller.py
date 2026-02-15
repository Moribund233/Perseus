"""
用户控制器层

处理与用户相关的HTTP请求，调用服务层方法并返回响应
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from models.db import get_db
from models.user import User
from api.dependencies import get_current_user, get_current_admin_user
from services.user_service import (
    get_users as service_get_users,
    get_user_by_id as service_get_user_by_id,
    create_user as service_create_user,
    update_user as service_update_user,
    delete_user as service_delete_user,
    login_user as service_login_user
)
from utils.rate_limiter import limiter, RateLimitConfig
from exception import AuthorizationException

# 创建路由实例
router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
@router.get("/")
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取所有用户（需要认证）

    Args:
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        list[User]: 用户列表
    """
    return service_get_users(db)


@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    根据ID获取用户（需要认证）

    Args:
        user_id: 用户ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        User: 用户信息

    Raises:
        NotFoundException: 用户不存在时抛出404异常
    """
    return service_get_user_by_id(user_id, db)


@router.post("")
@router.post("/")
def create_user(user: dict, db: Session = Depends(get_db)):
    """
    创建新用户
    
    Args:
        user: 用户信息
        db: 数据库会话
    
    Returns:
        User: 创建的用户信息
    
    Raises:
        ConflictException: 用户名或邮箱已存在时抛出409异常
    """
    return service_create_user(user, db)


@router.put("/{user_id}")
@limiter.limit(RateLimitConfig.STANDARD)
def update_user(
    request: Request,
    user_id: int,
    user: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新用户信息（需要认证）

    Args:
        request: HTTP请求对象（用于速率限制）
        user_id: 用户ID
        user: 更新的用户信息
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        User: 更新后的用户信息

    Raises:
        NotFoundException: 用户不存在时抛出404异常
        AuthorizationException: 无权限时抛出403异常
    """
    # 检查权限：只能更新自己的信息，或管理员可以更新任何用户
    if current_user.id != user_id and not current_user.is_admin:
        raise AuthorizationException(detail="You don't have permission to update this user")
    return service_update_user(user_id, user, db)


@router.delete("/{user_id}")
@limiter.limit(RateLimitConfig.STANDARD)
def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    删除用户（需要管理员权限）

    Args:
        request: HTTP请求对象（用于速率限制）
        user_id: 用户ID
        db: 数据库会话
        current_user: 当前认证管理员用户

    Returns:
        dict: 删除成功消息

    Raises:
        NotFoundException: 用户不存在时抛出404异常
        AuthorizationException: 非管理员时抛出403异常
    """
    return service_delete_user(user_id, db)


@router.post("/login")
@limiter.limit(RateLimitConfig.STRICT)
def login_user(request: Request, credentials: dict, db: Session = Depends(get_db)):
    """
    用户登录

    Args:
        request: HTTP请求对象（用于速率限制）
        credentials: 登录凭据（用户名和密码）
        db: 数据库会话

    Returns:
        dict: 登录成功信息和用户数据

    Raises:
        ValidationException: 请求参数不完整时抛出422异常
        AuthenticationException: 用户名或密码错误时抛出401异常
    """
    return service_login_user(credentials, db)
