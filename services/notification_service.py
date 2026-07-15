import logging
from datetime import datetime, timezone
from typing import Optional
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.notification import Notification
from models.user import User
from core.exception import NotFoundException
from utils.email_utils import send_notification_email
from services import notification_preference_service
from api.websocket.handlers.notification import notify_user

logger = logging.getLogger(__name__)


def build_notification_response(notif: Notification) -> dict:
    return {
        "id": notif.id,
        "type": notif.type,
        "title": notif.title,
        "message": notif.message,
        "repository_id": notif.repository_id,
        "target_type": notif.target_type,
        "target_id": notif.target_id,
        "is_read": notif.is_read,
        "created_at": notif.created_at.isoformat() if notif.created_at else None,
        "read_at": notif.read_at.isoformat() if notif.read_at else None,
    }


async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    type: str,
    title: str,
    message: str,
    repository_id: Optional[uuid.UUID] = None,
    target_type: Optional[str] = None,
    target_id: Optional[uuid.UUID] = None,
    send_email: bool = False,
) -> dict:
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        repository_id=repository_id,
        target_type=target_type,
        target_id=target_id,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)

    if send_email:
        should_send = await notification_preference_service.should_send_email(
            db, user_id, type
        )
        if should_send:
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if user and user.email:
                success = await send_notification_email(
                    to_email=user.email,
                    subject=title,
                    title=title,
                    message=message,
                )
                if not success:
                    logger.warning("Failed to send notification email to %s for notification type '%s'", user.email, type)

    result_data = build_notification_response(notif)
    try:
        await notify_user(user_id, type, result_data)
    except Exception as e:
        logger.warning("Failed to push WebSocket notification for user %d: %s", user_id, e)

    return result_data


async def get_user_notifications(
    db: AsyncSession,
    user_id: uuid.UUID,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> dict:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)
    stmt = stmt.order_by(Notification.created_at.desc())

    count_stmt = select(func.count(Notification.id)).where(Notification.user_id == user_id)
    if unread_only:
        count_stmt = count_stmt.where(Notification.is_read == False)

    result = await db.execute(stmt.offset(skip).limit(limit))
    notifications = result.scalars().all()

    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    return {
        "notifications": [build_notification_response(n) for n in notifications],
        "total": total,
    }


async def get_unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    stmt = select(func.count(Notification.id)).where(
        Notification.user_id == user_id,
        Notification.is_read == False,
    )
    result = await db.execute(stmt)
    return result.scalar()


async def mark_as_read(db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    result = await db.execute(stmt)
    notif = result.scalar_one_or_none()
    if not notif:
        raise NotFoundException(detail="Notification not found")

    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(notif)
    return build_notification_response(notif)


async def mark_all_as_read(db: AsyncSession, user_id: uuid.UUID) -> int:
    stmt = select(Notification).where(
        Notification.user_id == user_id,
        Notification.is_read == False,
    )
    result = await db.execute(stmt)
    notifications = result.scalars().all()

    for notif in notifications:
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)

    await db.commit()
    return len(notifications)


async def delete_notification(db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    result = await db.execute(stmt)
    notif = result.scalar_one_or_none()
    if not notif:
        raise NotFoundException(detail="Notification not found")

    await db.delete(notif)
    await db.commit()
    return True
