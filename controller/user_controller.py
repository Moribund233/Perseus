"""
用户控制器层

处理与用户相关的HTTP请求，调用服务层方法并返回响应
"""
from fastapi import APIRouter, Depends, Request, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models.user import User
from api.dependencies import get_current_user, get_current_admin_user
from services.user_service import (
    get_users as service_get_users,
    get_user_by_id as service_get_user_by_id,
    create_user as service_create_user,
    update_user as service_update_user,
    delete_user as service_delete_user,
    change_password as service_change_password,
    update_user_avatar as service_update_user_avatar,
    get_user_avatar as service_get_user_avatar,
)
from services.dashboard_service import get_user_dashboard as service_get_user_dashboard
from services.pull_request_service import list_pull_requests_for_user as service_list_pull_requests_for_user
from services.issue_service import list_issues_for_user as service_list_issues_for_user
import uuid

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


class ChangePasswordRequest(BaseModel):
    """修改密码请求体"""
    old_password: str = Field(..., min_length=1, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


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


@router.get("/me/dashboard", summary="获取当前用户 Dashboard")
async def get_current_user_dashboard(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户的 Dashboard 聚合数据

    Args:
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: Dashboard 数据
    """
    return await service_get_user_dashboard(db, current_user.id)


@router.get("/me/pull-requests", summary="获取当前用户的跨仓库 PR 列表")
async def get_current_user_pull_requests(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户相关的跨仓库 Pull Request 列表

    Args:
        status: 状态筛选（open/merged/closed）
        page: 页码
        limit: 每页数量
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 分页 PR 列表
    """
    return await service_list_pull_requests_for_user(
        db, current_user.id, status=status, page=page, limit=limit
    )


@router.get("/me/issues", summary="获取当前用户的跨仓库 Issue 列表")
async def get_current_user_issues(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户相关的跨仓库 Issue 列表

    Args:
        status: 状态筛选（open/closed）
        page: 页码
        limit: 每页数量
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 分页 Issue 列表
    """
    return await service_list_issues_for_user(
        db, current_user.id, status=status, page=page, limit=limit
    )


@router.post("/me/password", summary="修改当前用户密码")
async def change_current_user_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    修改当前登录用户的密码

    Args:
        data: 密码修改数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 操作成功消息
    """
    return await service_change_password(
        current_user, data.old_password, data.new_password, db
    )


@router.post("/me/avatar", summary="上传当前用户头像")
async def upload_current_user_avatar(
    file: UploadFile = File(..., description="头像图片文件（JPEG/PNG/GIF/WebP，最大5MB）"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传当前登录用户的头像

    Args:
        file: 头像图片文件
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 更新后的用户信息，包含 avatar_url

    Raises:
        ValidationException: 文件格式或大小不符合要求
    """
    file_data = await file.read()
    return await service_update_user_avatar(
        user=current_user,
        filename=file.filename or "avatar",
        content_type=file.content_type or "",
        file_data=file_data,
        db=db,
    )


@router.get("/{user_id}/avatar", summary="获取用户头像")
async def get_user_avatar_file(
    user_id: uuid.UUID
):
    """
    获取用户头像文件

    Args:
        user_id: 用户ID

    Returns:
        FileResponse: 头像图片文件

    Raises:
        NotFoundException: 头像不存在
    """
    file_path, content_type = await service_get_user_avatar(user_id)
    return FileResponse(path=str(file_path), media_type=content_type)


@router.get("/{user_id}", summary="根据ID获取用户")
async def get_user(
    user_id: uuid.UUID,
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
    user_id: uuid.UUID,
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
    user_id: uuid.UUID,
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
