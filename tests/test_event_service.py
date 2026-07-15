"""F-203/F-040 Business Events Push — service tests"""
import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock, patch

from api.websocket.manager import Connection, ConnectionManager


@pytest.fixture(autouse=True)
def reset_manager():
    ConnectionManager.reset_instance()
    yield


async def _register_connection(manager, user_id=None, username=None):
    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock(return_value=True)
    mock_ws.accept = AsyncMock(return_value=None)
    conn = await manager.connect(mock_ws)
    if user_id is not None:
        await manager.bind_user(conn, user_id, username or f"user_{user_id}")
    return conn, mock_ws


class TestEventService:

    @pytest.mark.asyncio
    async def test_broadcast_event_sends_to_room(self):
        from services.realtime.event_service import broadcast_event
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=2)
        room_id = uuid.uuid4()
        exclude_id = uuid.uuid4()
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_event(
                room_id=room_id,
                event_type="pr_opened",
                event_data={"pr_id": 42, "title": "Fix bug"},
                exclude_user_id=exclude_id,
            )
        assert count == 2
        manager.send_to_room.assert_called_once()
        call_args = manager.send_to_room.call_args
        assert call_args[0][0] == room_id
        payload = call_args[0][1]
        assert payload["type"] == "event"
        assert payload["event"] == "pr_opened"
        assert payload["data"]["pr_id"] == 42
        assert call_args[1]["exclude_user_id"] == exclude_id

    @pytest.mark.asyncio
    async def test_broadcast_event_default_exclude_none(self):
        from services.realtime.event_service import broadcast_event
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=1)
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_event(
                room_id=uuid.uuid4(),
                event_type="issue_created",
                event_data={"issue_id": 10},
            )
        assert count == 1
        call_args = manager.send_to_room.call_args
        assert call_args[1].get("exclude_user_id") is None

    @pytest.mark.asyncio
    async def test_broadcast_pr_opened(self):
        from services.realtime.event_service import broadcast_pr_opened
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=1)
        opener_id = uuid.uuid4()
        pr_id = uuid.uuid4()
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_pr_opened(
                room_id=uuid.uuid4(), pr_id=pr_id, title="New feature",
                opener_id=opener_id, opener_username="alice",
            )
        assert count == 1
        payload = manager.send_to_room.call_args[0][1]
        assert payload["event"] == "pr_opened"
        assert payload["data"]["pr_id"] == pr_id
        assert payload["data"]["opener"]["username"] == "alice"

    @pytest.mark.asyncio
    async def test_broadcast_pr_merged(self):
        from services.realtime.event_service import broadcast_pr_merged
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=1)
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_pr_merged(
                room_id=uuid.uuid4(), pr_id=uuid.uuid4(), title="Bugfix",
                merger_id=uuid.uuid4(), merger_username="bob",
            )
        assert count == 1
        payload = manager.send_to_room.call_args[0][1]
        assert payload["event"] == "pr_merged"
        assert payload["data"]["merger"]["username"] == "bob"

    @pytest.mark.asyncio
    async def test_broadcast_issue_created(self):
        from services.realtime.event_service import broadcast_issue_created
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=1)
        issue_id = uuid.uuid4()
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_issue_created(
                room_id=uuid.uuid4(), issue_id=issue_id, title="Documentation bug",
                creator_id=uuid.uuid4(), creator_username="carol",
            )
        assert count == 1
        payload = manager.send_to_room.call_args[0][1]
        assert payload["event"] == "issue_created"
        assert payload["data"]["issue_id"] == issue_id

    @pytest.mark.asyncio
    async def test_broadcast_push(self):
        from services.realtime.event_service import broadcast_push
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=3)
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_push(
                room_id=uuid.uuid4(), branch="main", commit_count=3,
                pusher_id=uuid.uuid4(), pusher_username="alice",
            )
        assert count == 3
        payload = manager.send_to_room.call_args[0][1]
        assert payload["event"] == "push"
        assert payload["data"]["branch"] == "main"
        assert payload["data"]["commit_count"] == 3


class TestPREvents:

    @pytest.mark.asyncio
    async def test_broadcast_pr_closed(self):
        from services.realtime.event_service import broadcast_pr_closed
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=1)
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_pr_closed(
                room_id=uuid.uuid4(), pr_id=uuid.uuid4(), title="Close bugfix",
                closer_id=uuid.uuid4(), closer_username="alice",
            )
        assert count == 1
        payload = manager.send_to_room.call_args[0][1]
        assert payload["event"] == "pr_closed"
        assert payload["data"]["closer"]["username"] == "alice"

    @pytest.mark.asyncio
    async def test_broadcast_pr_reopened(self):
        from services.realtime.event_service import broadcast_pr_reopened
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=1)
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_pr_reopened(
                room_id=uuid.uuid4(), pr_id=uuid.uuid4(), title="Reopen feature",
                reopens_id=uuid.uuid4(), reopens_username="bob",
            )
        assert count == 1
        payload = manager.send_to_room.call_args[0][1]
        assert payload["event"] == "pr_reopened"

    @pytest.mark.asyncio
    async def test_broadcast_pr_comment_added(self):
        from services.realtime.event_service import broadcast_pr_comment_added
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=1)
        comment_id = uuid.uuid4()
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_pr_comment_added(
                room_id=uuid.uuid4(), pr_id=uuid.uuid4(), comment_id=comment_id,
                commenter_id=uuid.uuid4(), commenter_username="carol",
                content="LGTM!",
            )
        assert count == 1
        payload = manager.send_to_room.call_args[0][1]
        assert payload["event"] == "pr_comment_added"
        assert payload["data"]["comment_id"] == comment_id
        assert payload["data"]["commenter"]["username"] == "carol"

    @pytest.mark.asyncio
    async def test_broadcast_pr_review_submitted(self):
        from services.realtime.event_service import broadcast_pr_review_submitted
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=1)
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_pr_review_submitted(
                room_id=uuid.uuid4(), pr_id=uuid.uuid4(), review_id=uuid.uuid4(),
                reviewer_id=uuid.uuid4(), reviewer_username="dave",
                state="approved",
            )
        assert count == 1
        payload = manager.send_to_room.call_args[0][1]
        assert payload["event"] == "pr_review_submitted"
        assert payload["data"]["state"] == "approved"
        assert payload["data"]["reviewer"]["username"] == "dave"

    @pytest.mark.asyncio
    async def test_pr_change_broadcasts_to_subscribers(self):
        """F-040 acceptance: PR event reaches room subscribers"""
        from services.realtime.event_service import broadcast_pr_opened
        manager = ConnectionManager()
        room_id = uuid.uuid4()
        alice_id = uuid.uuid4()
        conn_alice, mock_alice = await _register_connection(manager, user_id=alice_id, username="alice")
        conn_bob, mock_bob = await _register_connection(manager, user_id=uuid.uuid4(), username="bob")
        await manager.subscribe_room(conn_alice, room_id)
        await manager.subscribe_room(conn_bob, room_id)
        mock_bob.send_json.reset_mock()
        count = await broadcast_pr_opened(
            room_id=room_id, pr_id=uuid.uuid4(), title="Test PR",
            opener_id=alice_id, opener_username="alice",
        )
        # alice excluded (opener), bob should receive
        assert count == 1
        assert mock_bob.send_json.called
        sent = mock_bob.send_json.call_args[0][0]
        assert sent["type"] == "event"
        assert sent["event"] == "pr_opened"
