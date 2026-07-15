import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from models.notification import Notification
from services import notification_service
from core.exception import NotFoundException


@pytest.mark.asyncio
async def test_create_notification(async_db: AsyncSession, async_test_user):
    notif = await notification_service.create_notification(
        db=async_db,
        user_id=async_test_user.id,
        type="pull_request",
        title="PR merged",
        message="PR #12 has been merged",
        repository_id=None,
        target_type=None,
        target_id=None,
    )
    assert notif["type"] == "pull_request"
    assert notif["title"] == "PR merged"
    assert notif["is_read"] is False


@pytest.mark.asyncio
async def test_create_notification_with_repo(async_db: AsyncSession, async_test_user, async_test_repo):
    notif = await notification_service.create_notification(
        db=async_db,
        user_id=async_test_user.id,
        type="issue",
        title="Issue created",
        message="New issue in repo",
        repository_id=async_test_repo.id,
        target_type="issue",
        target_id=uuid.uuid4(),
    )
    assert notif["repository_id"] == async_test_repo.id


@pytest.mark.asyncio
async def test_get_user_notifications(async_db: AsyncSession, async_test_user):
    await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Comment 1", message="msg",
    )
    await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Comment 2", message="msg",
    )
    result = await notification_service.get_user_notifications(
        db=async_db, user_id=async_test_user.id
    )
    assert result["total"] == 2
    assert len(result["notifications"]) == 2


@pytest.mark.asyncio
async def test_get_unread_count(async_db: AsyncSession, async_test_user):
    await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Unread", message="msg",
    )
    count = await notification_service.get_unread_count(
        db=async_db, user_id=async_test_user.id
    )
    assert count == 1


@pytest.mark.asyncio
async def test_mark_as_read(async_db: AsyncSession, async_test_user):
    notif = await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Unread", message="msg",
    )
    result = await notification_service.mark_as_read(
        db=async_db, notification_id=notif["id"], user_id=async_test_user.id
    )
    assert result["is_read"] is True
    assert result["read_at"] is not None


@pytest.mark.asyncio
async def test_mark_as_read_not_found(async_db: AsyncSession, async_test_user):
    with pytest.raises(NotFoundException):
        await notification_service.mark_as_read(
            db=async_db, notification_id=uuid.uuid4(), user_id=async_test_user.id
        )


@pytest.mark.asyncio
async def test_mark_all_as_read(async_db: AsyncSession, async_test_user):
    await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="1", message="msg",
    )
    await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="2", message="msg",
    )
    count = await notification_service.mark_all_as_read(
        db=async_db, user_id=async_test_user.id
    )
    assert count == 2


@pytest.mark.asyncio
async def test_delete_notification(async_db: AsyncSession, async_test_user):
    notif = await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Delete me", message="msg",
    )
    result = await notification_service.delete_notification(
        db=async_db, notification_id=notif["id"], user_id=async_test_user.id
    )
    assert result is True


@pytest.mark.asyncio
async def test_delete_notification_not_found(async_db: AsyncSession, async_test_user):
    with pytest.raises(NotFoundException):
        await notification_service.delete_notification(
            db=async_db, notification_id=uuid.uuid4(), user_id=async_test_user.id
        )


@pytest.mark.asyncio
async def test_get_notifications_unread_only(async_db: AsyncSession, async_test_user):
    await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Unread", message="msg",
    )
    notif = await notification_service.create_notification(
        db=async_db, user_id=async_test_user.id,
        type="comment", title="Read", message="msg",
    )
    await notification_service.mark_as_read(
        db=async_db, notification_id=notif["id"], user_id=async_test_user.id
    )
    result = await notification_service.get_user_notifications(
        db=async_db, user_id=async_test_user.id, unread_only=True
    )
    assert result["total"] == 1
    assert result["notifications"][0]["title"] == "Unread"


@pytest.mark.asyncio
async def test_create_notification_sends_email(async_db: AsyncSession, async_test_user):
    from services import notification_preference_service
    await notification_preference_service.update_preferences(
        db=async_db, user_id=async_test_user.id, email_on_mention=True
    )
    async_test_user.email = "test@example.com"

    with patch("services.notification_service.send_notification_email", new_callable=AsyncMock) as mock_email:
        mock_email.return_value = True
        notif = await notification_service.create_notification(
            db=async_db,
            user_id=async_test_user.id,
            type="mention",
            title="You were mentioned",
            message="@you in PR #1",
            send_email=True,
        )
        assert notif["type"] == "mention"
        mock_email.assert_called_once_with(
            to_email="test@example.com",
            subject="You were mentioned",
            title="You were mentioned",
            message="@you in PR #1",
        )


@pytest.mark.asyncio
async def test_create_notification_no_email_when_disabled(async_db: AsyncSession, async_test_user):
    from services import notification_preference_service
    await notification_preference_service.update_preferences(
        db=async_db, user_id=async_test_user.id, email_on_mention=False
    )

    with patch("services.notification_service.send_notification_email", new_callable=AsyncMock) as mock_email:
        await notification_service.create_notification(
            db=async_db,
            user_id=async_test_user.id,
            type="mention",
            title="You were mentioned",
            message="@you in PR #1",
            send_email=True,
        )
        mock_email.assert_not_called()


@pytest.mark.asyncio
async def test_create_notification_email_failure(async_db: AsyncSession, async_test_user):
    from services import notification_preference_service
    await notification_preference_service.update_preferences(
        db=async_db, user_id=async_test_user.id, email_on_mention=True
    )
    async_test_user.email = "test@example.com"

    with patch("services.notification_service.send_notification_email", new_callable=AsyncMock) as mock_email:
        mock_email.return_value = False
        notif = await notification_service.create_notification(
            db=async_db,
            user_id=async_test_user.id,
            type="mention",
            title="You were mentioned",
            message="@you in PR #1",
            send_email=True,
        )
        assert notif["type"] == "mention"
        mock_email.assert_called_once_with(
            to_email="test@example.com",
            subject="You were mentioned",
            title="You were mentioned",
            message="@you in PR #1",
        )


@pytest.mark.asyncio
async def test_create_notification_sends_ws_push(async_db: AsyncSession, async_test_user):
    """创建通知后自动推送 WebSocket 通知"""
    mock_notify = AsyncMock(return_value=1)

    with patch("services.notification_service.notify_user", mock_notify):
        notif = await notification_service.create_notification(
            db=async_db,
            user_id=async_test_user.id,
            type="mention",
            title="You were mentioned",
            message="@you in PR #1",
        )

    assert notif["type"] == "mention"
    mock_notify.assert_awaited_once()
    args = mock_notify.call_args
    assert args[0][0] == async_test_user.id  # user_id
    assert args[0][1] == "mention"  # notification_type
    assert args[0][2]["id"] == notif["id"]  # data
    assert args[0][2]["title"] == "You were mentioned"
