"""
CI/CD Webhook Trigger Tests

Tests for trigger_push_event in utils/webhook_trigger.py
"""
import pytest
from unittest.mock import AsyncMock, patch

from utils.webhook_trigger import trigger_push_event


@pytest.mark.asyncio
async def test_ci_webhook_triggered_on_push(async_db, async_test_user, async_test_repo):
    """Push event should trigger webhooks if configured."""
    from services import webhook_service

    await webhook_service.create_webhook(
        db=async_db,
        repository_id=async_test_repo.id,
        user_id=async_test_user.id,
        url="https://ci.example.com/hook",
        events=["push"],
        secret="ci-secret",
    )

    with patch("utils.webhook_trigger.webhook_service.trigger_webhooks", new_callable=AsyncMock) as mock_trigger:
        await trigger_push_event(
            db=async_db,
            repository_id=async_test_repo.id,
            ref="refs/heads/main",
            before="0000000000000000000000000000000000000000",
            after="abc123def456",
            commits=[{"id": "abc123", "message": "feat: new feature"}],
            pusher={"name": "testuser", "email": "test@example.com"},
        )
        mock_trigger.assert_called_once()
        call_args = mock_trigger.call_args
        assert call_args[0][1] == async_test_repo.id
        assert call_args[0][2] == "push"


@pytest.mark.asyncio
async def test_ci_webhook_not_triggered_for_other_events(async_db, async_test_user, async_test_repo):
    """Push event should not trigger webhooks configured for other events."""
    from services import webhook_service

    await webhook_service.create_webhook(
        db=async_db,
        repository_id=async_test_repo.id,
        user_id=async_test_user.id,
        url="https://ci.example.com/hook",
        events=["release.created"],
        secret="ci-secret",
    )

    with patch("services.webhook_service._deliver_webhook_async", new_callable=AsyncMock) as mock_deliver:
        await trigger_push_event(
            db=async_db,
            repository_id=async_test_repo.id,
            ref="refs/heads/main",
            before="0000000000000000000000000000000000000000",
            after="abc123def456",
            commits=[],
            pusher={"name": "testuser", "email": "test@example.com"},
        )
        mock_deliver.assert_not_called()
