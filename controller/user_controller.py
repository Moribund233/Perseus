"""
用户控制器层

处理与用户相关的HTTP请求，调用服务层方法并返回响应
"""
from fastapi import APIRouter, Depends
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

# 创建路由实例
router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/")
async def get_users(db: Session = Depends(get_db)):
    """
    获取所有用户
    
    Args:
        db: 数据库会话
    
    Returns:
        list[User]: 用户列表
    """
    return await service_get_users(db)


@router.get("/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
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
    return await service_get_user_by_id(user_id, db)


@router.post("/")
async def create_user(user: dict, db: Session = Depends(get_db)):
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
    return await service_create_user(user, db)


@router.put("/{user_id}")
async def update_user(user_id: int, user: dict, db: Session = Depends(get_db)):
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
    return await service_update_user(user_id, user, db)


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    删除用户
    
    Args:
        user_id: 用户ID
        db: 数据库会话
    
    Returns:
        dict: 成功消息
    
    Raises:
        NotFoundException: 用户不存在时抛出404异常
    """
    return await service_delete_user(user_id, db)


# 登录路由
@router.post("/login")
async def login(credentials: dict, db: Session = Depends(get_db)):
    """
    用户登录
    
    Args:
        credentials: 登录凭证，包含用户名和密码
        db: 数据库会话
    
    Returns:
        dict: 登录成功后的用户信息
    
    Raises:
        AuthenticationException: 认证失败时抛出401异常
    """
    return await service_login_user(credentials, db)
