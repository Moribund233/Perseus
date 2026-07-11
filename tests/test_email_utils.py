import pytest
from unittest.mock import AsyncMock, patch
from utils.email_utils import send_notification_email, build_notification_html


def test_build_notification_html():
    html = build_notification_html(
        title="New Mention",
        message="@user mentioned you in PR #12",
        action_url="https://example.com/pr/12",
        action_label="View PR",
    )
    assert "New Mention" in html
    assert "@user mentioned you in PR #12" in html
    assert "https://example.com/pr/12" in html
    assert "View PR" in html
    assert "<html" in html


@pytest.mark.asyncio
async def test_send_notification_email_success():
    with patch("utils.email_utils.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = None
        result = await send_notification_email(
            to_email="user@example.com",
            subject="Test Subject",
            title="Test Title",
            message="Test message",
            action_url="https://example.com",
        )
        assert result is True
        mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_send_notification_email_failure():
    with patch("utils.email_utils.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = Exception("SMTP connection failed")
        result = await send_notification_email(
            to_email="user@example.com",
            subject="Test",
            title="Test",
            message="Test",
        )
        assert result is False


def test_build_notification_html_no_action():
    html = build_notification_html(
        title="System Notice",
        message="Maintenance scheduled",
    )
    assert "System Notice" in html
    assert "Maintenance scheduled" in html