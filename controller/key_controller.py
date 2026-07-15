"""
SSH Key 控制器层

F-020: SSH 认证集成
处理 SSH Key 相关的 HTTP 请求
"""
from typing import List
import uuid
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from api.dependencies import get_current_user
from core.exception import ValidationException, NotFoundException, AuthorizationException
from models.async_db import get_async_db
from models.user import User
from services import key_service
import uuid

# 创建路由实例
router = APIRouter(prefix=get_route_prefix("keys"), tags=["keys"])


class AddSSHKeyRequest(BaseModel):
    """添加 SSH Key 请求体"""
    name: str = Field(..., description="Key 名称", min_length=1, max_length=100)
    public_key: str = Field(..., description="SSH 公钥内容", min_length=1)


class SSHKeyResponse(BaseModel):
    """SSH Key 响应体"""
    id: uuid.UUID
    name: str
    public_key: str
    fingerprint: str
    user_id: uuid.UUID
    created_at: str

    class Config:
        from_attributes = True


@router.post(
    "",
    response_model=SSHKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="添加 SSH Key",
    description="为当前用户添加一个新的 SSH 公钥"
)
async def add_ssh_key(
    request: Request,
    key_data: AddSSHKeyRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    添加 SSH Key

    Args:
        request: HTTP 请求对象
        key_data: Key 数据（名称和公钥）
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        SSHKeyResponse: 创建的 Key 信息

    Raises:
        ValidationException: Key 格式无效或已存在
    """
    result = await key_service.add_ssh_key(
        db,
        user_id=current_user.id,
        name=key_data.name,
        public_key=key_data.public_key
    )
    return result


@router.get(
    "",
    response_model=List[SSHKeyResponse],
    summary="列出 SSH Keys",
    description="获取当前用户的所有 SSH Key"
)
async def list_ssh_keys(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    列出用户的 SSH Keys

    Args:
        request: HTTP 请求对象
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        List[SSHKeyResponse]: Key 列表
    """
    keys = await key_service.list_user_ssh_keys(db, current_user.id)
    return keys


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除 SSH Key",
    description="删除指定的 SSH Key"
)
async def delete_ssh_key(
    request: Request,
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除 SSH Key

    Args:
        request: HTTP 请求对象
        key_id: Key ID
        db: 数据库会话
        current_user: 当前认证用户

    Raises:
        NotFoundException: Key 不存在
        AuthorizationException: 无权删除
    """
    await key_service.delete_ssh_key(
        db,
        key_id=key_id,
        user_id=current_user.id
    )
