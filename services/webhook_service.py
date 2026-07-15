"""
WebHook 服务层

处理 WebHook 的创建、管理、触发和投递
"""
import json
import uuid
import hmac
import hashlib
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models import WebHook, WebHookDelivery
from models.webhook import WEBHOOK_EVENTS
import uuid
from core.exception import NotFoundException, ValidationException, AuthorizationException
from utils.permission_utils import check_repository_permission
from utils.db_utils import paginate
from utils.response_builder import build_pagination_response


# =============================================================================
# WebHook 管理
# =============================================================================

async def list_webhooks(
    db: AsyncSession,
    repository_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """
    获取 WebHook 列表

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        user_id: 当前用户ID
        page: 页码
        limit: 每页数量

    Returns:
        dict: 包含 WebHook 列表和分页信息

    Raises:
        AuthorizationException: 无权限查看
    """
    # 检查权限
    has_permission = await check_repository_permission(
        db, repository_id, user_id, "read"
    )
    if not has_permission:
        raise AuthorizationException(detail="Not authorized to view webhooks")

    stmt = select(WebHook).filter(
        WebHook.repository_id == repository_id
    ).order_by(WebHook.created_at.desc())

    webhooks, total = await paginate(db, stmt, page, limit)

    return build_pagination_response(
        items=[build_webhook_response(w) for w in webhooks],
        total=total,
        page=page,
        limit=limit
    )


async def get_webhook(
    db: AsyncSession,
    repository_id: uuid.UUID,
    webhook_id: uuid.UUID,
    user_id: uuid.UUID
) -> dict:
    """
    获取 WebHook 详情

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        webhook_id: WebHook ID
        user_id: 当前用户ID

    Returns:
        dict: WebHook 详情

    Raises:
        NotFoundException: WebHook 不存在
        AuthorizationException: 无权限查看
    """
    # 检查权限
    has_permission = await check_repository_permission(
        db, repository_id, user_id, "read"
    )
    if not has_permission:
        raise AuthorizationException(detail="Not authorized to view webhook")

    stmt = select(WebHook).filter(
        WebHook.id == webhook_id,
        WebHook.repository_id == repository_id
    )

    result = await db.execute(stmt)
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise NotFoundException(detail="Webhook not found")

    return build_webhook_response(webhook, include_secret=True)


async def create_webhook(
    db: AsyncSession,
    repository_id: uuid.UUID,
    user_id: uuid.UUID,
    url: str,
    events: List[str],
    secret: Optional[str] = None,
    content_type: str = "application/json",
    is_active: bool = True
) -> dict:
    """
    创建 WebHook

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        user_id: 当前用户ID
        url: 回调 URL
        events: 订阅的事件列表
        secret: 签名密钥
        content_type: Content-Type
        is_active: 是否激活

    Returns:
        dict: 创建的 WebHook 数据

    Raises:
        ValidationException: 参数验证失败
        AuthorizationException: 无权限创建
    """
    # 检查权限（需要管理员权限）
    has_permission = await check_repository_permission(
        db, repository_id, user_id, "admin"
    )
    if not has_permission:
        raise AuthorizationException(detail="Not authorized to create webhook")

    # 验证 URL
    if not url or not url.startswith(("http://", "https://")):
        raise ValidationException(detail="Invalid URL. Must start with http:// or https://")

    # 验证事件
    if not events:
        raise ValidationException(detail="At least one event must be specified")

    for event in events:
        if not _is_valid_event(event):
            raise ValidationException(detail=f"Invalid event: {event}")

    # 验证 content_type
    if content_type not in ["application/json", "application/x-www-form-urlencoded"]:
        raise ValidationException(detail="Invalid content_type. Must be application/json or application/x-www-form-urlencoded")

    # 创建 WebHook
    webhook = WebHook(
        repository_id=repository_id,
        url=url,
        secret=secret,
        content_type=content_type,
        is_active=is_active
    )
    webhook.set_events_list(events)

    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)

    return build_webhook_response(webhook, include_secret=True)


async def update_webhook(
    db: AsyncSession,
    repository_id: uuid.UUID,
    webhook_id: uuid.UUID,
    user_id: uuid.UUID,
    url: Optional[str] = None,
    events: Optional[List[str]] = None,
    secret: Optional[str] = None,
    content_type: Optional[str] = None,
    is_active: Optional[bool] = None
) -> dict:
    """
    更新 WebHook

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        webhook_id: WebHook ID
        user_id: 当前用户ID
        url: 回调 URL
        events: 订阅的事件列表
        secret: 签名密钥
        content_type: Content-Type
        is_active: 是否激活

    Returns:
        dict: 更新后的 WebHook 数据

    Raises:
        NotFoundException: WebHook 不存在
        ValidationException: 参数验证失败
        AuthorizationException: 无权限更新
    """
    # 检查权限
    has_permission = await check_repository_permission(
        db, repository_id, user_id, "admin"
    )
    if not has_permission:
        raise AuthorizationException(detail="Not authorized to update webhook")

    stmt = select(WebHook).filter(
        WebHook.id == webhook_id,
        WebHook.repository_id == repository_id
    )

    result = await db.execute(stmt)
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise NotFoundException(detail="Webhook not found")

    # 更新字段
    if url is not None:
        if not url.startswith(("http://", "https://")):
            raise ValidationException(detail="Invalid URL")
        webhook.url = url

    if events is not None:
        for event in events:
            if not _is_valid_event(event):
                raise ValidationException(detail=f"Invalid event: {event}")
        webhook.set_events_list(events)

    if secret is not None:
        webhook.secret = secret

    if content_type is not None:
        if content_type not in ["application/json", "application/x-www-form-urlencoded"]:
            raise ValidationException(detail="Invalid content_type")
        webhook.content_type = content_type

    if is_active is not None:
        webhook.is_active = is_active

    await db.commit()
    await db.refresh(webhook)

    return build_webhook_response(webhook, include_secret=True)


async def delete_webhook(
    db: AsyncSession,
    repository_id: uuid.UUID,
    webhook_id: uuid.UUID,
    user_id: uuid.UUID
) -> None:
    """
    删除 WebHook

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        webhook_id: WebHook ID
        user_id: 当前用户ID

    Raises:
        NotFoundException: WebHook 不存在
        AuthorizationException: 无权限删除
    """
    # 检查权限
    has_permission = await check_repository_permission(
        db, repository_id, user_id, "admin"
    )
    if not has_permission:
        raise AuthorizationException(detail="Not authorized to delete webhook")

    stmt = select(WebHook).filter(
        WebHook.id == webhook_id,
        WebHook.repository_id == repository_id
    )

    result = await db.execute(stmt)
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise NotFoundException(detail="Webhook not found")

    await db.delete(webhook)
    await db.commit()


async def test_webhook(
    db: AsyncSession,
    repository_id: uuid.UUID,
    webhook_id: uuid.UUID,
    user_id: uuid.UUID
) -> dict:
    """
    测试 WebHook

    发送一个测试事件到 WebHook URL

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        webhook_id: WebHook ID
        user_id: 当前用户ID

    Returns:
        dict: 测试结果

    Raises:
        NotFoundException: WebHook 不存在
        AuthorizationException: 无权限测试
    """
    # 检查权限
    has_permission = await check_repository_permission(
        db, repository_id, user_id, "admin"
    )
    if not has_permission:
        raise AuthorizationException(detail="Not authorized to test webhook")

    stmt = select(WebHook).filter(
        WebHook.id == webhook_id,
        WebHook.repository_id == repository_id
    )

    result = await db.execute(stmt)
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise NotFoundException(detail="Webhook not found")

    # 构建测试 payload
    test_payload = {
        "event": "test",
        "repository": {
            "id": str(repository_id),
            "name": "test-repo"
        },
        "sender": {
            "id": str(user_id),
            "username": "test-user"
        },
        "message": "This is a test event from Perseus"
    }

    # 发送测试请求
    delivery = await _deliver_webhook(webhook, "test", test_payload)

    return {
        "success": delivery.is_success,
        "status_code": delivery.response_status,
        "response_body": delivery.response_body,
        "duration_ms": delivery.duration_ms,
        "error_message": delivery.error_message
    }


# =============================================================================
# WebHook 触发和投递
# =============================================================================

async def trigger_webhooks(
    db: AsyncSession,
    repository_id: uuid.UUID,
    event: str,
    payload: Dict[str, Any]
) -> None:
    """
    触发 WebHook

    异步触发所有订阅了指定事件的 WebHook

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        event: 事件类型
        payload: 事件数据
    """
    # 获取所有订阅了该事件的活跃 WebHook
    stmt = select(WebHook).filter(
        WebHook.repository_id == repository_id,
        WebHook.is_active == True
    )

    result = await db.execute(stmt)
    webhooks = result.scalars().all()

    # 筛选订阅了该事件的 WebHook
    subscribed_webhooks = [
        w for w in webhooks if w.is_subscribed_to(event)
    ]

    if not subscribed_webhooks:
        return

    # 构建完整 payload
    full_payload = {
        "event": event,
        "timestamp": datetime.utcnow().isoformat(),
        **payload
    }

    # 异步投递所有 WebHook
    tasks = [
        _deliver_webhook_async(w, event, full_payload)
        for w in subscribed_webhooks
    ]

    # 使用 gather 并发执行，但不等待结果（fire and forget）
    asyncio.create_task(asyncio.gather(*tasks, return_exceptions=True))


async def _deliver_webhook_async(
    webhook: WebHook,
    event: str,
    payload: Dict[str, Any]
) -> None:
    """
    异步投递 WebHook（用于 fire and forget 模式）

    Args:
        webhook: WebHook 实例
        event: 事件类型
        payload: 事件数据
    """
    # 创建新的数据库会话
    from models.async_db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await _deliver_webhook(webhook, event, payload, db)


async def _deliver_webhook(
    webhook: WebHook,
    event: str,
    payload: Dict[str, Any],
    db: Optional[AsyncSession] = None
) -> WebHookDelivery:
    """
    投递 WebHook

    支持最多 3 次指数退避重试（1s, 2s, 4s），最终失败的投递记录会保留
    最后一次错误信息。

    Args:
        webhook: WebHook 实例
        event: 事件类型
        payload: 事件数据
        db: 数据库会话（可选）

    Returns:
        WebHookDelivery: 投递记录
    """
    import time

    start_time = time.time()

    # 准备请求头
    headers = {
        "User-Agent": "Perseus-WebHook/1.0",
        "X-GitHub-Event": event,  # 兼容 GitHub 格式
        "X-Perseus-Event": event,
        "X-Webhook-ID": str(webhook.id),
        "Content-Type": webhook.content_type
    }

    # 准备请求体
    class UUIDEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, uuid.UUID):
                return str(obj)
            return super().default(obj)
    payload_json = json.dumps(payload, ensure_ascii=False, cls=UUIDEncoder)

    # 如果有密钥，生成签名
    if webhook.secret:
        signature = _generate_signature(payload_json, webhook.secret)
        headers["X-Hub-Signature-256"] = signature
        headers["X-Webhook-Signature"] = signature

    # 根据 content_type 调整请求体格式
    if webhook.content_type == "application/x-www-form-urlencoded":
        from urllib.parse import urlencode
        body = urlencode({"payload": payload_json})
    else:
        body = payload_json

    # 创建投递记录
    delivery = WebHookDelivery(
        webhook_id=webhook.id,
        event=event,
        payload=payload_json,
        request_headers=json.dumps(headers)
    )

    if db:
        db.add(delivery)
        await db.commit()

    # F-031: 指数退避重试，最多 3 次
    max_retries = 3
    last_exception: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    webhook.url,
                    content=body,
                    headers=headers
                )

            duration_ms = int((time.time() - start_time) * 1000)

            # 更新投递记录
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:10000]  # 限制大小
            delivery.response_headers = json.dumps(dict(response.headers))
            delivery.duration_ms = duration_ms
            delivery.is_success = 200 <= response.status_code < 300
            delivery.error_message = None

            # 更新 WebHook 最后触发信息
            webhook.last_triggered_at = datetime.utcnow()
            webhook.last_response_status = response.status_code
            webhook.last_response_body = response.text[:1000]

            if delivery.is_success:
                break

            # 非 2xx 响应且还有重试次数时，记录为本次失败原因并继续
            last_exception = Exception(f"HTTP {response.status_code}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            last_exception = e

            delivery.response_status = 0
            delivery.duration_ms = duration_ms
            delivery.is_success = False
            delivery.error_message = str(e)[:1000]

            webhook.last_triggered_at = datetime.utcnow()
            webhook.last_response_status = 0
            webhook.last_response_body = str(e)[:1000]

            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)

    if db:
        await db.commit()
        await db.refresh(delivery)

    return delivery


def _generate_signature(payload: str, secret: str) -> str:
    """
    生成 HMAC-SHA256 签名

    Args:
        payload: 请求体
        secret: 密钥

    Returns:
        str: 签名，格式为 "sha256=<hex>"
    """
    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def _is_valid_event(event: str) -> bool:
    """
    验证事件名称是否有效

    Args:
        event: 事件名称

    Returns:
        bool: 是否有效
    """
    # 支持通配符
    if event.endswith(".*"):
        prefix = event[:-2]
        return any(e.startswith(prefix + ".") for e in WEBHOOK_EVENTS)

    return event in WEBHOOK_EVENTS


# =============================================================================
# 投递记录查询
# =============================================================================

async def list_webhook_deliveries(
    db: AsyncSession,
    repository_id: uuid.UUID,
    webhook_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """
    获取 WebHook 投递记录列表

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        webhook_id: WebHook ID
        user_id: 当前用户ID
        page: 页码
        limit: 每页数量

    Returns:
        dict: 包含投递记录列表和分页信息

    Raises:
        AuthorizationException: 无权限查看
    """
    # 检查权限
    has_permission = await check_repository_permission(
        db, repository_id, user_id, "admin"
    )
    if not has_permission:
        raise AuthorizationException(detail="Not authorized to view deliveries")

    # 验证 WebHook 存在且属于该仓库
    webhook_stmt = select(WebHook).filter(
        WebHook.id == webhook_id,
        WebHook.repository_id == repository_id
    )
    result = await db.execute(webhook_stmt)
    if not result.scalar_one_or_none():
        raise NotFoundException(detail="Webhook not found")

    stmt = select(WebHookDelivery).filter(
        WebHookDelivery.webhook_id == webhook_id
    ).order_by(WebHookDelivery.created_at.desc())

    deliveries, total = await paginate(db, stmt, page, limit)

    return build_pagination_response(
        items=[build_delivery_response(d) for d in deliveries],
        total=total,
        page=page,
        limit=limit
    )


async def get_webhook_delivery(
    db: AsyncSession,
    repository_id: uuid.UUID,
    webhook_id: uuid.UUID,
    delivery_id: uuid.UUID,
    user_id: uuid.UUID
) -> dict:
    """
    获取 WebHook 投递记录详情

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        webhook_id: WebHook ID
        delivery_id: 投递记录ID
        user_id: 当前用户ID

    Returns:
        dict: 投递记录详情

    Raises:
        NotFoundException: 记录不存在
        AuthorizationException: 无权限查看
    """
    # 检查权限
    has_permission = await check_repository_permission(
        db, repository_id, user_id, "admin"
    )
    if not has_permission:
        raise AuthorizationException(detail="Not authorized to view delivery")

    # 验证 WebHook 存在且属于该仓库
    webhook_stmt = select(WebHook).filter(
        WebHook.id == webhook_id,
        WebHook.repository_id == repository_id
    )
    result = await db.execute(webhook_stmt)
    if not result.scalar_one_or_none():
        raise NotFoundException(detail="Webhook not found")

    stmt = select(WebHookDelivery).filter(
        WebHookDelivery.id == delivery_id,
        WebHookDelivery.webhook_id == webhook_id
    )

    result = await db.execute(stmt)
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise NotFoundException(detail="Delivery not found")

    return build_delivery_response(delivery, include_details=True)


# =============================================================================
# 响应构建函数
# =============================================================================

def build_webhook_response(webhook: WebHook, include_secret: bool = False) -> dict:
    """
    构建 WebHook 响应数据

    Args:
        webhook: WebHook 模型实例
        include_secret: 是否包含密钥

    Returns:
        dict: 响应数据
    """
    data = {
        "id": webhook.id,
        "url": webhook.url,
        "events": webhook.get_events_list(),
        "content_type": webhook.content_type,
        "is_active": webhook.is_active,
        "last_triggered_at": webhook.last_triggered_at.isoformat() if webhook.last_triggered_at else None,
        "last_response_status": webhook.last_response_status,
        "created_at": webhook.created_at.isoformat() if webhook.created_at else None,
        "updated_at": webhook.updated_at.isoformat() if webhook.updated_at else None
    }

    if include_secret and webhook.secret:
        # 只显示密钥的部分内容
        data["secret"] = webhook.secret[:4] + "*" * (len(webhook.secret) - 4)

    return data


def build_delivery_response(delivery: WebHookDelivery, include_details: bool = False) -> dict:
    """
    构建 WebHook 投递记录响应数据

    Args:
        delivery: WebHookDelivery 模型实例
        include_details: 是否包含详细信息

    Returns:
        dict: 响应数据
    """
    data = {
        "id": delivery.id,
        "event": delivery.event,
        "is_success": delivery.is_success,
        "response_status": delivery.response_status,
        "duration_ms": delivery.duration_ms,
        "created_at": delivery.created_at.isoformat() if delivery.created_at else None
    }

    if include_details:
        data["payload"] = delivery.payload
        data["request_headers"] = delivery.request_headers
        data["response_body"] = delivery.response_body
        data["response_headers"] = delivery.response_headers
        data["error_message"] = delivery.error_message

    return data
