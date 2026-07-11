import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from models.notification_preference import NotificationPreference
from services import notification_preference_service


@pytest.mark.asyncio
async def test_create_default_preferences(async_db: AsyncSession, async_test_user):
    prefs = await notification_preference_service.get_or_create(
        db=async_db, user_id=async_test_user.id
    )
    assert prefs["email_on_mention"] is True
    assert prefs["email_on_pr_review"] is True
    assert prefs["email_on_issue_comment"] is True
    assert prefs["in_app_on_mention"] is True


@pytest.mark.asyncio
async def test_update_preferences(async_db: AsyncSession, async_test_user):
    await notification_preference_service.get_or_create(
        db=async_db, user_id=async_test_user.id
    )
    updated = await notification_preference_service.update_preferences(
        db=async_db, user_id=async_test_user.id,
        email_on_mention=False, email_on_pr_review=False
    )
    assert updated["email_on_mention"] is False
    assert updated["email_on_pr_review"] is False
    assert updated["email_on_issue_comment"] is True  # unchanged


@pytest.mark.asyncio
async def test_get_preferences_returns_same(async_db: AsyncSession, async_test_user):
    prefs1 = await notification_preference_service.get_or_create(
        db=async_db, user_id=async_test_user.id
    )
    prefs2 = await notification_preference_service.get_or_create(
        db=async_db, user_id=async_test_user.id
    )
    assert prefs1["id"] == prefs2["id"]


@pytest.mark.asyncio
async def test_should_send_email(async_db: AsyncSession, async_test_user):
    await notification_preference_service.get_or_create(
        db=async_db, user_id=async_test_user.id
    )
    # Default is True
    assert await notification_preference_service.should_send_email(
        async_db, async_test_user.id, "mention"
    ) is True
    # Disable email on mention
    await notification_preference_service.update_preferences(
        async_db, async_test_user.id, email_on_mention=False
    )
    assert await notification_preference_service.should_send_email(
        async_db, async_test_user.id, "mention"
    ) is False
    # Unknown event type returns True
    assert await notification_preference_service.should_send_email(
        async_db, async_test_user.id, "unknown_event"
    ) is True


@pytest.mark.asyncio
async def test_should_send_in_app(async_db: AsyncSession, async_test_user):
    await notification_preference_service.get_or_create(
        db=async_db, user_id=async_test_user.id
    )
    # Default is True
    assert await notification_preference_service.should_send_in_app(
        async_db, async_test_user.id, "mention"
    ) is True
    # Disable in-app on mention
    await notification_preference_service.update_preferences(
        async_db, async_test_user.id, in_app_on_mention=False
    )
    assert await notification_preference_service.should_send_in_app(
        async_db, async_test_user.id, "mention"
    ) is False
    # Unknown event type returns True
    assert await notification_preference_service.should_send_in_app(
        async_db, async_test_user.id, "unknown_event"
    ) is True


@pytest.mark.asyncio
async def test_update_preferences_creates_when_not_exists(async_db: AsyncSession, async_test_user):
    updated = await notification_preference_service.update_preferences(
        db=async_db, user_id=async_test_user.id,
        email_on_mention=False, in_app_on_pr_review=False
    )
    assert updated["email_on_mention"] is False
    assert updated["in_app_on_pr_review"] is False
    assert updated["email_on_pr_review"] is True  # default


@pytest.mark.asyncio
async def test_build_pref_response_includes_timestamps(async_db: AsyncSession, async_test_user):
    prefs = await notification_preference_service.get_or_create(
        db=async_db, user_id=async_test_user.id
    )
    assert prefs["created_at"] is not None
    assert prefs["updated_at"] is not None
