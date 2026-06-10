"""
认证控制器层

处理用户认证相关的 HTTP 请求，包括登录、登出等
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from services.user_service import login_user as service_login_user

# 创建路由实例
router = APIRouter(prefix=get_route_prefix("auth"), tags=["auth"])


class LoginRequest(BaseModel):
    """登录请求体"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


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
