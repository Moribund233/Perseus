import pytest
import uuid
from datetime import datetime
from models.notification import Notification

class TestNotificationModel:
    def test_notification_creation(self):
        notif = Notification(
            user_id=uuid.uuid4(),
            type="pull_request",
            title="PR merged",
            message="PR #12 has been merged",
            repository_id=uuid.uuid4(),
            target_type="pull_request",
            target_id=uuid.uuid4(),
        )
        assert notif.user_id is not None
        assert notif.type == "pull_request"
        assert notif.read_at is None

    def test_notification_default_is_read_false(self):
        from sqlalchemy import inspect
        mapper = inspect(Notification)
        is_read_column = mapper.columns.is_read
        assert is_read_column.default.arg is False

    def test_notification_repr(self):
        notif = Notification(
            user_id=uuid.uuid4(),
            type="comment",
            title="Comment",
            message="New comment",
            repository_id=uuid.uuid4(),
            target_type="pull_request",
            target_id=uuid.uuid4(),
        )
        assert "Notification(id=" in repr(notif)

    def test_notification_table_name(self):
        assert Notification.__tablename__ == "notifications"