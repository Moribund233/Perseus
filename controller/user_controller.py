"""
用户控制器层

处理与用户相关的HTTP请求，调用服务层方法并返回响应
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models.user import User
from api.dependencies import get_current_user, get_current_admin_user
from services.user_service import (
    get_users as service_get_users,
    get_user_by_id as service_get_user_by_id,
    create_user as service_create_user,
    update_user as service_update_user,
    delete_user as service_delete_user
)

# 创建路由实例
router = APIRouter(prefix=get_route_prefix("users"), tags=["users"])


class UserCreateRequest(BaseModel):
    """创建用户请求体"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    is_active: bool = Field(default=True, description="是否激活")
    # is_admin 不由注册接口设置；管理员只能通过环境变量 PERSEUS_ADMIN_* 引导创建


class UserUpdateRequest(BaseModel):
    """更新用户请求体"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    is_active: Optional[bool] = Field(None, description="是否激活")


@router.get("", summary="获取所有用户")
async def get_users(
    db: AsyncSession = Depends(get_async_db),
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
    return await service_get_users(db)


@router.get("/me", summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户信息

    Args:
        current_user: 当前认证用户

    Returns:
        User: 当前用户信息
    """
    return current_user


@router.get("/{user_id}", summary="根据ID获取用户")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
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
    return await service_get_user_by_id(user_id, db)


@router.post("", summary="创建新用户")
async def create_user(
    user_data: UserCreateRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    创建新用户

    Args:
        user_data: 用户创建数据，包含用户名、邮箱、密码等
        db: 数据库会话

    Returns:
        User: 创建的用户信息

    Raises:
        ConflictException: 用户名或邮箱已存在时抛出409异常
        ValidationException: 请求参数无效时抛出422异常
    """
    return await service_create_user(user_data.model_dump(), db)


@router.put("/{user_id}")
async def update_user(
    request: Request,
    user_id: int,
    user_data: UserUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新用户信息（需要认证）

    权限规则：
    - 普通用户只能更新自己的信息
    - 管理员可以更新任何用户的信息

    Args:
        request: HTTP请求对象（用于速率限制）
        user_id: 用户ID
        user_data: 更新的用户数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        User: 更新后的用户信息

    Raises:
        NotFoundException: 用户不存在时抛出404异常
        AuthorizationException: 无权限时抛出403异常
    """
    return await service_update_user(user_id, user_data.model_dump(exclude_unset=True), db, current_user)


@router.delete("/{user_id}")
async def delete_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
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
    return await service_delete_user(user_id, db)
