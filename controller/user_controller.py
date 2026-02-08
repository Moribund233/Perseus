"""
用户控制器层

处理与用户相关的HTTP请求，调用服务层方法并返回响应
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from models.db import get_db
from services.user_service import (
    get_users as service_get_users,
    get_user_by_id as service_get_user_by_id,
    create_user as service_create_user,
    update_user as service_update_user,
    delete_user as service_delete_user,
    login_user as service_login_user
)
from utils.rate_limiter import limiter, RateLimitConfig

# 创建路由实例
router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
@router.get("/")
def get_users(db: Session = Depends(get_db)):
    """
    获取所有用户
    
    Args:
        db: 数据库会话
    
    Returns:
        list[User]: 用户列表
    """
    return service_get_users(db)


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    根据ID获取用户
    
    Args:
        user_id: 用户ID
        db: 数据库会话
    
    Returns:
        User: 用户信息
    
    Raises:
        NotFoundException: 用户不存在时抛出404异常
    """
    return service_get_user_by_id(user_id, db)


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
def update_user(user_id: int, user: dict, db: Session = Depends(get_db)):
    """
    更新用户信息
    
    Args:
        user_id: 用户ID
        user: 更新的用户信息
        db: 数据库会话
    
    Returns:
        User: 更新后的用户信息
    
    Raises:
        NotFoundException: 用户不存在时抛出404异常
    """
    return service_update_user(user_id, user, db)


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    删除用户
    
    Args:
        user_id: 用户ID
        db: 数据库会话
    
    Returns:
        dict: 删除成功消息
    
    Raises:
        NotFoundException: 用户不存在时抛出404异常
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
