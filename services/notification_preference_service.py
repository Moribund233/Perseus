from typing import Dict, Any
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.notification_preference import NotificationPreference


def build_pref_response(pref: NotificationPreference) -> dict:
    return {
        "id": pref.id,
        "user_id": pref.user_id,
        "email_on_mention": pref.email_on_mention,
        "email_on_pr_review": pref.email_on_pr_review,
        "email_on_issue_comment": pref.email_on_issue_comment,
        "email_on_pr_merge": pref.email_on_pr_merge,
        "email_on_release": pref.email_on_release,
        "in_app_on_mention": pref.in_app_on_mention,
        "in_app_on_pr_review": pref.in_app_on_pr_review,
        "in_app_on_issue_comment": pref.in_app_on_issue_comment,
        "created_at": pref.created_at.isoformat() if pref.created_at else None,
        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None,
    }


async def get_or_create(db: AsyncSession, user_id: uuid.UUID) -> dict:
    stmt = select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    result = await db.execute(stmt)
    pref = result.scalar_one_or_none()
    if pref:
        return build_pref_response(pref)

    pref = NotificationPreference(user_id=user_id)
    db.add(pref)
    await db.commit()
    await db.refresh(pref)
    return build_pref_response(pref)


async def update_preferences(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> dict:
    stmt = select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    result = await db.execute(stmt)
    pref = result.scalar_one_or_none()
    if not pref:
        pref = NotificationPreference(user_id=user_id)
        db.add(pref)

    allowed_fields = {
        "email_on_mention", "email_on_pr_review", "email_on_issue_comment",
        "email_on_pr_merge", "email_on_release",
        "in_app_on_mention", "in_app_on_pr_review", "in_app_on_issue_comment",
    }
    for key, value in kwargs.items():
        if key in allowed_fields:
            setattr(pref, key, value)

    await db.commit()
    await db.refresh(pref)
    return build_pref_response(pref)


async def should_send_email(db: AsyncSession, user_id: uuid.UUID, event_type: str) -> bool:
    prefs = await get_or_create(db, user_id)
    mapping = {
        "mention": prefs["email_on_mention"],
        "pr_review": prefs["email_on_pr_review"],
        "issue_comment": prefs["email_on_issue_comment"],
        "pr_merge": prefs["email_on_pr_merge"],
        "release": prefs["email_on_release"],
    }
    return mapping.get(event_type, True)


async def should_send_in_app(db: AsyncSession, user_id: uuid.UUID, event_type: str) -> bool:
    prefs = await get_or_create(db, user_id)
    mapping = {
        "mention": prefs["in_app_on_mention"],
        "pr_review": prefs["in_app_on_pr_review"],
        "issue_comment": prefs["in_app_on_issue_comment"],
    }
    return mapping.get(event_type, True)
