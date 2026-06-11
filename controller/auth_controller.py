"""
认证控制器层

处理用户认证相关的 HTTP 请求，包括登录、登出、Token 刷新等
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from core.exception import AuthenticationException
from models.async_db import get_async_db
from services.user_service import login_user as service_login_user
from services import token_service

# 创建路由实例
router = APIRouter(prefix=get_route_prefix("auth"), tags=["auth"])


class LoginRequest(BaseModel):
    """登录请求体"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求体"""
    refresh_token: str = Field(..., description="刷新令牌")


@router.post("/login")
async def login(
    request: Request,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    用户登录

    Args:
        request: HTTP请求对象（用于速率限制）
        credentials: 登录凭据（用户名和密码）
        db: 数据库会话

    Returns:
        dict: 登录成功信息和用户数据，包含访问令牌

    Raises:
        ValidationException: 请求参数不完整时抛出422异常
        AuthenticationException: 用户名或密码错误时抛出401异常

    Example:
        ```json
        {
            "username": "admin",
            "password": "password123"
        }
        ```
    """
    return await service_login_user(credentials.model_dump(), db)


@router.post("/refresh")
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    刷新访问令牌

    使用有效的刷新令牌获取新的访问令牌

    Args:
        request: 刷新令牌请求
        db: 数据库会话

    Returns:
        dict: 新的访问令牌和刷新令牌

    Raises:
        AuthenticationException: 刷新令牌无效或过期时抛出401异常

    Example:
        ```json
        {
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
        ```

    Response:
        ```json
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer"
        }
        ```
    """
    # 验证刷新令牌
    token_data = token_service.verify_token(request.refresh_token, token_type="refresh")
    if not token_data:
        raise AuthenticationException(detail="Invalid or expired refresh token")

    # 获取用户信息
    from sqlalchemy import select
    from models.user import User
    result = await db.execute(select(User).filter(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise AuthenticationException(detail="User not found or inactive")

    # 创建新的令牌对
    tokens = token_service.create_token_pair(user)

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer"
    }
