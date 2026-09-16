"""F-203/F-040 Business Events Push — service tests"""
import json

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
    # Connection.send 实际调用 send_text (JSON 字符串), send_json 仅为兼容保留
    mock_ws.send_text = AsyncMock(return_value=True)
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

    @pytest.mark.asyncio
    async def test_broadcast_push_rebuilds_index_asynchronously(self, tmp_path, monkeypatch):
        """push 后索引重建应经 asyncio.to_thread 离开事件循环 (F-039)"""
        from services.realtime import event_service
        from services.search_service import SearchService, SearchIndex
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=1)

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("def pushed_func():\n    return 1\n")

        to_thread_targets = []

        async def fake_to_thread(fn, *args, **kwargs):
            to_thread_targets.append(fn)
            return fn(*args, **kwargs)

        monkeypatch.setattr(event_service.asyncio, "to_thread", fake_to_thread)

        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await event_service.broadcast_push(
                room_id=uuid.uuid4(), branch="main", commit_count=1,
                pusher_id=uuid.uuid4(), pusher_username="alice",
                repo_path=str(repo_dir),
            )

        assert count == 1
        assert SearchService.rebuild_index in to_thread_targets, \
            "索引重建应经 to_thread 调用, 避免大仓阻塞事件循环"
        index = SearchIndex(str(repo_dir))
        assert index.exists()
        assert len(index.search("pushed_func")) > 0

    @pytest.mark.asyncio
    async def test_broadcast_push_creates_build_for_commit(
        self, async_db, async_test_repo, async_test_user,
    ):
        """push 携带 commit 信息时应按 (repo, branch, commit) 去重建 pending build (F-046)"""
        from services.realtime.room_service import RoomService
        from services.build_service import BuildService
        from services.realtime.event_service import broadcast_push
        room = await RoomService.create_room(
            async_db, async_test_repo.id, "dev-room", async_test_user.id,
        )
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=1)
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_push(
                room_id=room.id, branch="main", commit_count=1,
                pusher_id=async_test_user.id, pusher_username="alice",
                db=async_db, commit_sha="abc123def456", commit_message="Push commit",
            )
        assert count == 2
        payloads = [call.args[1] for call in manager.send_to_room.call_args_list]
        assert payloads[0]["event"] == "push"
        assert payloads[1]["event"] == "build"
        assert payloads[1]["data"]["status"] == "pending"
        assert payloads[1]["data"]["commit_sha"] == "abc123def456"

        builds = await BuildService.get_builds_for_repository(
            db=async_db, repo_id=async_test_repo.id,
        )
        assert len(builds) == 1
        assert builds[0].branch == "main"
        assert builds[0].commit_sha == "abc123def456"
        assert builds[0].status == "pending"

    @pytest.mark.asyncio
    async def test_broadcast_push_build_dedup_by_commit(
        self, async_db, async_test_repo, async_test_user,
    ):
        """同 commit 已存在 build (如 PR merge 已创建) 时, push 不应重复建 build"""
        from services.realtime.room_service import RoomService
        from services.build_service import BuildService
        from services.realtime.event_service import broadcast_push
        room = await RoomService.create_room(
            async_db, async_test_repo.id, "dev-room", async_test_user.id,
        )
        await BuildService.ensure_build_for_commit(
            db=async_db, repo_id=async_test_repo.id, branch="main",
            commit_sha="abc123", triggered_by=async_test_user.id,
        )
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=1)
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_push(
                room_id=room.id, branch="main", commit_count=1,
                pusher_id=async_test_user.id, pusher_username="alice",
                db=async_db, commit_sha="abc123",
            )
        assert count == 1
        manager.send_to_room.assert_called_once()
        payload = manager.send_to_room.call_args[0][1]
        assert payload["event"] == "push"

        builds = await BuildService.get_builds_for_repository(
            db=async_db, repo_id=async_test_repo.id,
        )
        assert len(builds) == 1

    @pytest.mark.asyncio
    async def test_broadcast_push_no_build_event_without_db(
        self, async_db, async_test_repo, async_test_user,
    ):
        """未传 db/commit_sha 时保持原行为: 仅广播 push, 不建 build (向后兼容)"""
        from services.realtime.event_service import broadcast_push
        from services.build_service import BuildService
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=3)
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_push(
                room_id=uuid.uuid4(), branch="main", commit_count=3,
                pusher_id=async_test_user.id, pusher_username="alice",
            )
        assert count == 3
        manager.send_to_room.assert_called_once()
        payload = manager.send_to_room.call_args[0][1]
        assert payload["event"] == "push"
        builds = await BuildService.get_builds_for_repository(
            db=async_db, repo_id=async_test_repo.id,
        )
        assert builds == []

    @pytest.mark.asyncio
    async def test_broadcast_push_skips_build_when_room_missing(
        self, async_db, async_test_user,
    ):
        """room 不存在时建 build 应静默跳过, 不抛异常"""
        from services.realtime.event_service import broadcast_push
        manager = ConnectionManager()
        manager.send_to_room = AsyncMock(return_value=0)
        with patch("services.realtime.event_service.ConnectionManager", return_value=manager):
            count = await broadcast_push(
                room_id=uuid.uuid4(), branch="main", commit_count=1,
                pusher_id=async_test_user.id, pusher_username="alice",
                db=async_db, commit_sha="abc123",
            )
        assert count == 0


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
        mock_bob.send_text.reset_mock()
        count = await broadcast_pr_opened(
            room_id=room_id, pr_id=uuid.uuid4(), title="Test PR",
            opener_id=alice_id, opener_username="alice",
        )
        # alice excluded (opener), bob should receive
        assert count == 1
        assert mock_bob.send_text.called
        # Connection.send 通过 send_text 发送 JSON 字符串
        sent = json.loads(mock_bob.send_text.call_args[0][0])
        assert sent["type"] == "event"
        assert sent["event"] == "pr_opened"
