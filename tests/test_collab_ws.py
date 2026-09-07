"""F-204 协作文本编辑 WS handler 与会话服务测试"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.websocket.manager import ConnectionManager
from services.realtime.collab_service import (
    ChangeSetError,
    CollabStaleError,
    CollabSession,
    apply_changeset,
    collab_service,
)


def _sent_payloads(mock_ws):
    """解析 mock 连接收到的全部 JSON 消息"""
    return [json.loads(c.args[0]) for c in mock_ws.send_text.await_args_list]


def _last_payload(mock_ws):
    assert mock_ws.send_text.await_count >= 1, "expected at least one send_text call"
    return json.loads(mock_ws.send_text.await_args[0][0])


@pytest.fixture(autouse=True)
def reset_manager():
    ConnectionManager.reset_instance()
    collab_service._sessions.clear()
    yield
    collab_service._sessions.clear()


async def _register_connection(manager, connection_id, user_id=None, username=None):
    mock_ws = MagicMock()
    mock_ws.send_text = AsyncMock(return_value=True)
    mock_ws.accept = AsyncMock(return_value=None)
    conn = await manager.connect(mock_ws)
    conn.connection_id = connection_id
    manager._connections[connection_id] = conn
    if user_id is not None:
        await manager.bind_user(conn, user_id, username or f"user_{user_id}")
    return conn, mock_ws


# ==================== ChangeSet 应用 ====================


class TestApplyChangeSet:
    def test_untouched_only(self):
        assert apply_changeset("hello", [5]) == "hello"

    def test_insertion(self):
        # 在位置 0 插入 "hi": 部件 [0, "hi"] + 未修改 5
        result = apply_changeset("hello", [[0, "hi"], 5])
        assert result == "hihello"

    def test_deletion(self):
        # 删除 "ell" (位置 1-4): [1, [3], 1]
        result = apply_changeset("hello", [1, [3], 1])
        assert result == "ho"

    def test_replacement_multiline(self):
        # 替换 5 个字符为两行文本
        result = apply_changeset("hello", [[5, "a", "b"]])
        assert result == "a\nb"

    def test_sequential_edits(self):
        # "hello world" -> 删除 "world" 前的空格并替换为换行
        result = apply_changeset("hello world", [5, [1, "\n"], 5])
        assert result == "hello\nworld"

    def test_beyond_document_rejected(self):
        with pytest.raises(ChangeSetError):
            apply_changeset("abc", [10])

    def test_invalid_part_rejected(self):
        with pytest.raises(ChangeSetError):
            apply_changeset("abc", [{"bad": 1}])

    def test_negative_rejected(self):
        with pytest.raises(ChangeSetError):
            apply_changeset("abc", [-1])


# ==================== 会话服务 ====================


class TestCollabSession:
    def _session(self, text="hello"):
        return CollabSession("k", uuid.uuid4(), "main", "f.txt", text)

    def test_push_advances_version_and_text(self):
        s = self._session()
        v = s.push("c1", 0, [[5, [0, " world"]]])  # 末尾追加
        assert v == 1
        assert s.text == "hello world"

    def test_push_stale_rejected(self):
        s = self._session()
        s.push("c1", 0, [[5, [0, "!"]]])
        with pytest.raises(CollabStaleError) as exc:
            s.push("c2", 0, [[5, [0, "?"]]])  # 版本 0 已过期
        assert exc.value.server_version == 1
        assert s.text == "hello!"  # 权威文本不变

    def test_missed_changes(self):
        s = self._session()
        s.push("c1", 0, [[5, [0, "!"]]])
        missed = s.missed_changes(0)
        assert len(missed) == 1
        assert missed[0]["clientID"] == "c1"

    def test_pull(self):
        s = self._session()
        s.push("c1", 0, [[5, [0, "!"]]])
        changes = s.pull(0)
        assert len(changes) == 1
        assert s.pull(1) == []

    def test_log_truncation_and_resync(self):
        from services.realtime.collab_service import MAX_LOG_ENTRIES

        s = self._session()
        for i in range(MAX_LOG_ENTRIES + 3):
            s.push(f"c{i}", s.version, [[[0, "x"]]])
        assert s.log_base == 3
        assert s.pull(1) is None  # 版本过旧
        assert s.pull(3) is not None

    def test_join_leave_participants(self):
        s = self._session()
        s.participants["conn1"] = {"clientID": "c1", "user_id": uuid.uuid4(), "username": "a", "cursor": None}
        assert not s.is_empty
        s.participants.pop("conn1")
        assert s.is_empty


# ==================== WS Handler 流程 ====================

REPO_ID = str(uuid.uuid4())


def _permission_mock(read: bool, write: bool) -> AsyncMock:
    """按角色集合区分读/写权限的 _check_permission mock"""
    from api.websocket.handlers.collab import READ_ROLES, WRITE_ROLES

    async def _check(repository_id, user_id, roles):
        if set(roles) == set(WRITE_ROLES):
            return write
        return read

    return AsyncMock(side_effect=_check)


async def _join_doc(manager, conn_id, username, client_id, monkeypatch, writable=True, readable=True):
    """辅助: 创建会话并加入, 返回 (conn, mock_ws, doc_key)"""
    monkeypatch.setattr(
        "api.websocket.handlers.collab._check_permission",
        _permission_mock(readable, writable),
    )
    monkeypatch.setattr(
        "api.websocket.handlers.collab._get_repo_path", AsyncMock(return_value="/tmp/repo")
    )
    monkeypatch.setattr(
        "services.repository_browser_service.get_blob_content",
        AsyncMock(return_value={"content": "hello", "is_binary": False}),
    )
    user_id = uuid.uuid4()
    conn, mock_ws = await _register_connection(manager, conn_id, user_id=user_id, username=username)
    from api.websocket.handlers.collab import handle_collab_message

    await handle_collab_message(conn, {
        "type": "collab_join",
        "repository_id": REPO_ID,
        "branch": "main",
        "path": "a.txt",
        "clientID": client_id,
    })
    doc_key = collab_service.make_doc_key(REPO_ID, "main", "a.txt")
    return conn, mock_ws, doc_key


class TestCollabHandlers:
    @pytest.mark.asyncio
    async def test_join_requires_auth(self, monkeypatch):
        from api.websocket.handlers.collab import handle_collab_message

        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(manager, "c1")
        await handle_collab_message(conn, {
            "type": "collab_join", "repository_id": REPO_ID,
            "branch": "main", "path": "a.txt", "clientID": "cl1",
        })
        assert _last_payload(mock_ws)["type"] == "error"

    @pytest.mark.asyncio
    async def test_join_missing_fields(self, monkeypatch):
        from api.websocket.handlers.collab import handle_collab_message

        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(
            manager, "c1", user_id=uuid.uuid4(), username="alice"
        )
        await handle_collab_message(conn, {"type": "collab_join", "repository_id": REPO_ID})
        assert _last_payload(mock_ws)["type"] == "error"

    @pytest.mark.asyncio
    async def test_join_creates_session_and_broadcasts(self, monkeypatch):
        from api.websocket.handlers.collab import handle_collab_message

        manager = ConnectionManager()
        conn1, ws1, doc_key = await _join_doc(manager, "c1", "alice", "cl1", monkeypatch)
        conn2, ws2 = await _register_connection(
            manager, "c2", user_id=uuid.uuid4(), username="bob"
        )

        await handle_collab_message(conn2, {
            "type": "collab_join",
            "repository_id": REPO_ID,
            "branch": "main",
            "path": "a.txt",
            "clientID": "cl2",
        })

        # init: 文档内容 + 版本 + 参与者
        payloads = _sent_payloads(ws2)
        init = [p for p in payloads if p["type"] == "collab_init"][0]
        assert init["doc"] == "hello"
        assert init["version"] == 0
        assert len(init["participants"]) == 2  # 含加入者自身

        # 已有参与者收到 peer_joined
        joined = [p for p in _sent_payloads(ws1) if p["type"] == "collab_peer_joined"]
        assert joined and joined[-1]["clientID"] == "cl2"

    @pytest.mark.asyncio
    async def test_push_accept_and_broadcast(self, monkeypatch):
        from api.websocket.handlers.collab import handle_collab_message

        manager = ConnectionManager()
        conn1, ws1, doc_key = await _join_doc(manager, "c1", "alice", "cl1", monkeypatch)
        conn2, ws2, _ = await _join_doc(manager, "c2", "bob", "cl2", monkeypatch)

        await handle_collab_message(conn1, {
            "type": "collab_push", "docKey": doc_key,
            "version": 0, "changes": [5, [0, "!"]], "clientID": "cl1",
        })

        # 发送者与协作者都收到变更 (发送者靠 clientID 识别自身并推进版本)
        updates1 = [p for p in _sent_payloads(ws1) if p["type"] == "collab_update"]
        assert updates1 and updates1[-1]["clientID"] == "cl1"
        assert updates1[-1]["version"] == 1

        updates2 = [p for p in _sent_payloads(ws2) if p["type"] == "collab_update"]
        assert updates2 and updates2[-1]["changes"] == [[5, [0, "!"]]]

        # 权威文本已应用
        assert collab_service.get_session(doc_key).text == "hello!"

    @pytest.mark.asyncio
    async def test_push_stale_rejects_with_missed_changes(self, monkeypatch):
        from api.websocket.handlers.collab import handle_collab_message

        manager = ConnectionManager()
        conn1, ws1, doc_key = await _join_doc(manager, "c1", "alice", "cl1", monkeypatch)
        conn2, ws2, _ = await _join_doc(manager, "c2", "bob", "cl2", monkeypatch)

        # alice 先推送版本 0
        await handle_collab_message(conn1, {
            "type": "collab_push", "docKey": doc_key,
            "version": 0, "changes": [5, [0, "!"]], "clientID": "cl1",
        })
        # bob 基于版本 0 推送 (已过期)
        ws2.send_text.reset_mock()
        await handle_collab_message(conn2, {
            "type": "collab_push", "docKey": doc_key,
            "version": 0, "changes": [5, [0, "?"]], "clientID": "cl2",
        })

        reject = _last_payload(ws2)
        assert reject["type"] == "collab_reject"
        assert reject["version"] == 1
        assert reject["changes"] == [{"changes": [5, [0, "!"]], "clientID": "cl1"}]

    @pytest.mark.asyncio
    async def test_push_requires_write_permission(self, monkeypatch):
        from api.websocket.handlers.collab import handle_collab_message

        manager = ConnectionManager()
        conn1, ws1, doc_key = await _join_doc(manager, "c1", "alice", "cl1", monkeypatch)
        # 只读协作者: 有读权限可加入会话, 但写权限被拒
        conn2, ws2, _ = await _join_doc(manager, "c2", "viewer", "cl2", monkeypatch, writable=False)
        inits = [p for p in _sent_payloads(ws2) if p["type"] == "collab_init"]
        assert inits  # 只读用户成功加入

        await handle_collab_message(conn2, {
            "type": "collab_push", "docKey": doc_key,
            "version": 0, "changes": [5, [0, "!"]], "clientID": "cl2",
        })
        assert _last_payload(ws2)["type"] == "error"

        # 会话文本未被修改
        assert collab_service.get_session(doc_key).text == "hello"

    @pytest.mark.asyncio
    async def test_push_uses_cached_permission(self, monkeypatch):
        """push/save 使用 join 时缓存的权限, 不再逐次查库"""
        from api.websocket.handlers.collab import handle_collab_message

        manager = ConnectionManager()
        conn1, ws1, doc_key = await _join_doc(manager, "c1", "alice", "cl1", monkeypatch)

        # join 之后替换新 mock: push 全程不应再触发权限查询
        permission_after_join = AsyncMock(return_value=False)
        monkeypatch.setattr(
            "api.websocket.handlers.collab._check_permission", permission_after_join
        )

        await handle_collab_message(conn1, {
            "type": "collab_push", "docKey": doc_key,
            "version": 0, "changes": [5, [0, "!"]], "clientID": "cl1",
        })
        assert permission_after_join.await_count == 0
        assert collab_service.get_session(doc_key).text == "hello!"

    @pytest.mark.asyncio
    async def test_push_empty_changes_rejected(self, monkeypatch):
        from api.websocket.handlers.collab import handle_collab_message

        manager = ConnectionManager()
        conn1, ws1, doc_key = await _join_doc(manager, "c1", "alice", "cl1", monkeypatch)

        await handle_collab_message(conn1, {
            "type": "collab_push", "docKey": doc_key,
            "version": 0, "changes": [], "clientID": "cl1",
        })
        assert _last_payload(ws1)["type"] == "error"
        assert collab_service.get_session(doc_key).version == 0

    @pytest.mark.asyncio
    async def test_save_requires_write_permission(self, monkeypatch):
        from api.websocket.handlers.collab import handle_collab_message

        manager = ConnectionManager()
        conn1, ws1, doc_key = await _join_doc(manager, "c1", "alice", "cl1", monkeypatch)
        conn2, ws2, _ = await _join_doc(manager, "c2", "viewer", "cl2", monkeypatch, writable=False)

        await handle_collab_message(conn2, {
            "type": "collab_save", "docKey": doc_key, "message": "view try",
        })
        assert _last_payload(ws2)["type"] == "error"

    @pytest.mark.asyncio
    async def test_pull(self, monkeypatch):
        from api.websocket.handlers.collab import handle_collab_message

        manager = ConnectionManager()
        conn1, ws1, doc_key = await _join_doc(manager, "c1", "alice", "cl1", monkeypatch)
        await handle_collab_message(conn1, {
            "type": "collab_push", "docKey": doc_key,
            "version": 0, "changes": [5, [0, "!"]], "clientID": "cl1",
        })

        await handle_collab_message(conn1, {"type": "collab_pull", "docKey": doc_key, "version": 0})
        update = _last_payload(ws1)
        assert update["type"] == "collab_update"
        assert update["version"] == 1
        # pull 响应与 push 广播同构: changes 为 ChangeSet JSON 数组 (非日志条目)
        assert update["changes"] == [[5, [0, "!"]]]

    @pytest.mark.asyncio
    async def test_cursor_broadcast(self, monkeypatch):
        from api.websocket.handlers.collab import handle_collab_message

        manager = ConnectionManager()
        conn1, ws1, doc_key = await _join_doc(manager, "c1", "alice", "cl1", monkeypatch)
        conn2, ws2, _ = await _join_doc(manager, "c2", "bob", "cl2", monkeypatch)

        await handle_collab_message(conn1, {
            "type": "collab_cursor", "docKey": doc_key, "anchor": 2, "head": 4,
        })

        cursor = [p for p in _sent_payloads(ws2) if p["type"] == "collab_cursor"]
        assert cursor and cursor[-1]["anchor"] == 2 and cursor[-1]["head"] == 4

    @pytest.mark.asyncio
    async def test_save_commits_and_broadcasts(self, monkeypatch):
        from api.websocket.handlers.collab import handle_collab_message

        commit_mock = AsyncMock(return_value={"commit_id": "abc1234"})
        manager = ConnectionManager()
        conn1, ws1, doc_key = await _join_doc(manager, "c1", "alice", "cl1", monkeypatch)
        conn2, ws2, _ = await _join_doc(manager, "c2", "bob", "cl2", monkeypatch)

        await handle_collab_message(conn1, {
            "type": "collab_push", "docKey": doc_key,
            "version": 0, "changes": [5, [0, "!"]], "clientID": "cl1",
        })
        ws1.send_text.reset_mock()

        # mock 用户查询与提交
        mock_user = MagicMock()
        mock_user.full_name = "Alice"
        mock_user.username = "alice"
        mock_user.email = "alice@test.com"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        class _FakeDb:
            async def __aenter__(self):
                db = MagicMock()
                db.execute = AsyncMock(return_value=mock_result)
                return db

            async def __aexit__(self, *args):
                return False

        def fake_db_context():
            return _FakeDb()

        with patch("models.async_db.get_async_db_context", fake_db_context), patch(
            "services.repository_browser_service.commit_file", commit_mock
        ):
            await handle_collab_message(conn1, {
                "type": "collab_save", "docKey": doc_key, "message": "collab edit",
            })

        # 提交内容为权威文本
        args = commit_mock.await_args[0]
        assert args[3] == "hello!"  # content
        assert args[6] == "collab edit"  # message

        acks = [p for p in _sent_payloads(ws1) if p["type"] == "collab_save_ack"]
        assert acks and acks[-1]["commit_id"] == "abc1234"
        saved = [p for p in _sent_payloads(ws2) if p["type"] == "collab_saved"]
        assert saved and saved[-1]["saved_by"] == "alice"

    @pytest.mark.asyncio
    async def test_leave_and_session_gc(self, monkeypatch):
        from api.websocket.handlers.collab import handle_collab_message

        manager = ConnectionManager()
        conn1, ws1, doc_key = await _join_doc(manager, "c1", "alice", "cl1", monkeypatch)
        conn2, ws2, _ = await _join_doc(manager, "c2", "bob", "cl2", monkeypatch)

        await handle_collab_message(conn1, {"type": "collab_leave", "docKey": doc_key})
        left = [p for p in _sent_payloads(ws2) if p["type"] == "collab_peer_left"]
        assert left

        # 最后一人离开后会话销毁
        await handle_collab_message(conn2, {"type": "collab_leave", "docKey": doc_key})
        assert collab_service.get_session(doc_key) is None

        # 会话已销毁: push 报错
        ws2.send_text.reset_mock()
        await handle_collab_message(conn2, {
            "type": "collab_push", "docKey": doc_key,
            "version": 0, "changes": [5, [0, "!"]], "clientID": "cl2",
        })
        assert _last_payload(ws2)["type"] == "error"

    @pytest.mark.asyncio
    async def test_cleanup_on_disconnect(self, monkeypatch):
        from api.websocket.handlers.collab import cleanup_connection_docs, handle_collab_message

        manager = ConnectionManager()
        conn1, ws1, doc_key = await _join_doc(manager, "c1", "alice", "cl1", monkeypatch)
        conn2, ws2, _ = await _join_doc(manager, "c2", "bob", "cl2", monkeypatch)

        await cleanup_connection_docs("c1")
        left = [p for p in _sent_payloads(ws2) if p["type"] == "collab_peer_left"]
        assert left and left[-1]["docKey"] == doc_key

        # alice 的会话引用已清理, bob 仍在
        session = collab_service.get_session(doc_key)
        assert "c1" not in session.participants
        assert "c2" in session.participants

    @pytest.mark.asyncio
    async def test_unknown_message_type(self, monkeypatch):
        from api.websocket.handlers.collab import handle_collab_message

        manager = ConnectionManager()
        conn, mock_ws = await _register_connection(
            manager, "c1", user_id=uuid.uuid4(), username="alice"
        )
        await handle_collab_message(conn, {"type": "collab_unknown"})
        payload = _last_payload(mock_ws)
        assert payload["type"] == "error"
        assert "collab_join" in payload["supported_types"]
