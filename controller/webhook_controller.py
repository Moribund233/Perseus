"""
Webhook 控制器层

F-031: Webhook 触发与投递
F-032: HMAC-SHA256 签名验证
F-033: 事件负载标准格式
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.routes_config import get_route_prefix
from api.dependencies import get_current_user
from models.async_db import get_async_db
from models.repository import Repository
from models.user import User
from core.exception import NotFoundException
from services import webhook_service
import uuid

# 创建路由实例
router = APIRouter(prefix=get_route_prefix("webhooks"), tags=["webhooks"])


class CreateWebhookRequest(BaseModel):
    """创建 WebHook 请求体"""
    url: str = Field(..., description="回调 URL")
    events: List[str] = Field(..., description="订阅的事件列表", min_length=1)
    secret: Optional[str] = Field(None, description="签名密钥")
    content_type: str = Field(default="application/json", description="Content-Type")
    is_active: bool = Field(default=True, description="是否激活")


class UpdateWebhookRequest(BaseModel):
    """更新 WebHook 请求体"""
    url: Optional[str] = Field(None, description="回调 URL")
    events: Optional[List[str]] = Field(None, description="订阅的事件列表")
    secret: Optional[str] = Field(None, description="签名密钥")
    content_type: Optional[str] = Field(None, description="Content-Type")
    is_active: Optional[bool] = Field(None, description="是否激活")


async def _get_repo(repo_id: uuid.UUID, db: AsyncSession) -> Repository:
    """
    获取仓库实例

    Args:
        repo_id: 仓库ID
        db: 数据库会话

    Returns:
        Repository: 仓库实例

    Raises:
        NotFoundException: 仓库不存在
    """
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found")
    return repo


@router.post("/{repo_id}/webhooks", status_code=status.HTTP_201_CREATED)
async def create_webhook(
    repo_id: uuid.UUID,
    data: CreateWebhookRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建 WebHook

    Args:
        repo_id: 仓库ID
        data: WebHook 数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 创建的 WebHook 数据
    """
    await _get_repo(repo_id, db)
    return await webhook_service.create_webhook(
        db=db,
        repository_id=repo_id,
        user_id=current_user.id,
        url=data.url,
        events=data.events,
        secret=data.secret,
        content_type=data.content_type,
        is_active=data.is_active
    )


@router.get("/{repo_id}/webhooks")
async def list_webhooks(
    repo_id: uuid.UUID,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取 WebHook 列表

    Args:
        repo_id: 仓库ID
        page: 页码
        limit: 每页数量
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: WebHook 列表和分页信息
    """
    await _get_repo(repo_id, db)
    return await webhook_service.list_webhooks(
        db=db,
        repository_id=repo_id,
        user_id=current_user.id,
        page=page,
        limit=limit
    )


@router.get("/{repo_id}/webhooks/{webhook_id}")
async def get_webhook(
    repo_id: uuid.UUID,
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取 WebHook 详情

    Args:
        repo_id: 仓库ID
        webhook_id: WebHook ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: WebHook 详情
    """
    await _get_repo(repo_id, db)
    return await webhook_service.get_webhook(
        db=db,
        repository_id=repo_id,
        webhook_id=webhook_id,
        user_id=current_user.id
    )


@router.patch("/{repo_id}/webhooks/{webhook_id}")
async def update_webhook(
    repo_id: uuid.UUID,
    webhook_id: uuid.UUID,
    data: UpdateWebhookRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新 WebHook

    Args:
        repo_id: 仓库ID
        webhook_id: WebHook ID
        data: 更新数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 更新后的 WebHook 数据
    """
    await _get_repo(repo_id, db)
    return await webhook_service.update_webhook(
        db=db,
        repository_id=repo_id,
        webhook_id=webhook_id,
        user_id=current_user.id,
        url=data.url,
        events=data.events,
        secret=data.secret,
        content_type=data.content_type,
        is_active=data.is_active
    )


@router.delete("/{repo_id}/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    repo_id: uuid.UUID,
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除 WebHook

    Args:
        repo_id: 仓库ID
        webhook_id: WebHook ID
        db: 数据库会话
        current_user: 当前认证用户
    """
    await _get_repo(repo_id, db)
    await webhook_service.delete_webhook(
        db=db,
        repository_id=repo_id,
        webhook_id=webhook_id,
        user_id=current_user.id
    )


@router.post("/{repo_id}/webhooks/{webhook_id}/test")
async def test_webhook(
    repo_id: uuid.UUID,
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    测试 WebHook

    发送测试事件到 WebHook URL

    Args:
        repo_id: 仓库ID
        webhook_id: WebHook ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 测试结果
    """
    await _get_repo(repo_id, db)
    return await webhook_service.test_webhook(
        db=db,
        repository_id=repo_id,
        webhook_id=webhook_id,
        user_id=current_user.id
    )


@router.get("/{repo_id}/webhooks/{webhook_id}/deliveries")
async def list_webhook_deliveries(
    repo_id: uuid.UUID,
    webhook_id: uuid.UUID,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取 WebHook 投递记录列表

    Args:
        repo_id: 仓库ID
        webhook_id: WebHook ID
        page: 页码
        limit: 每页数量
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 投递记录列表和分页信息
    """
    await _get_repo(repo_id, db)
    return await webhook_service.list_webhook_deliveries(
        db=db,
        repository_id=repo_id,
        webhook_id=webhook_id,
        user_id=current_user.id,
        page=page,
        limit=limit
    )


@router.get("/{repo_id}/webhooks/{webhook_id}/deliveries/{delivery_id}")
async def get_webhook_delivery(
    repo_id: uuid.UUID,
    webhook_id: uuid.UUID,
    delivery_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取 WebHook 投递记录详情

    Args:
        repo_id: 仓库ID
        webhook_id: WebHook ID
        delivery_id: 投递记录ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 投递记录详情
    """
    await _get_repo(repo_id, db)
    return await webhook_service.get_webhook_delivery(
        db=db,
        repository_id=repo_id,
        webhook_id=webhook_id,
        delivery_id=delivery_id,
        user_id=current_user.id
    )
