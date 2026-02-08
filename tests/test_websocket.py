"""
WebSocket单元测试模块

测试范围:
1. ConnectionManager - 连接管理器
2. Connection - 连接包装类
3. 消息处理器 - notification, sync, progress
4. 认证模块 - auth
5. WebSocket路由 - router
"""
import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from fastapi import WebSocket
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as StarletteTestClient
from starlette.websockets import WebSocketDisconnect

# 导入被测试的模块
from api.websocket.manager import ConnectionManager, Connection, manager
from api.websocket.auth import (
    WebSocketAuthError,
    extract_token_from_query,
    verify_token,
    authenticate_websocket,
    authenticate_websocket_optional,
)
from api.websocket.handlers.notification import (
    handle_ping,
    handle_subscribe,
    handle_unsubscribe,
    handle_broadcast,
    notify_commit_new,
    notify_branch_update,
    notify_user,
)
from api.websocket.handlers.sync import handle_sync_request, handle_sync_status
from api.websocket.handlers.progress import handle_progress_update


# ==================== Fixtures ====================

@pytest.fixture
def mock_websocket():
    """创建模拟WebSocket对象"""
    ws = Mock(spec=WebSocket)
    ws.send_json = AsyncMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.query_params = {}
    return ws


@pytest.fixture
def connection_manager():
    """创建新的ConnectionManager实例（重置单例）"""
    ConnectionManager._instance = None
    ConnectionManager._initialized = False
    return ConnectionManager()


@pytest.fixture
def sample_connection(mock_websocket, connection_manager):
    """创建示例连接"""
    return Connection(mock_websocket, "test_conn_001")


# ==================== Connection类测试 ====================

class TestConnection:
    """测试Connection类"""

    @pytest.mark.asyncio
    async def test_connection_send_success(self, sample_connection, mock_websocket):
        """测试发送消息成功"""
        message = {"type": "test", "data": "hello"}
        result = await sample_connection.send(message)

        assert result is True
        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_connection_send_failure(self, sample_connection, mock_websocket):
        """测试发送消息失败"""
        mock_websocket.send_json.side_effect = Exception("发送失败")

        message = {"type": "test", "data": "hello"}
        result = await sample_connection.send(message)

        assert result is False
        assert sample_connection.is_alive is False

    def test_connection_bind_user(self, sample_connection):
        """测试用户绑定"""
        sample_connection.bind_user(1, "testuser")

        assert sample_connection.user_id == 1
        assert sample_connection.username == "testuser"

    def test_connection_subscribe_repository(self, sample_connection):
        """测试订阅仓库"""
        sample_connection.subscribe_repository(123)

        assert 123 in sample_connection.repository_ids

    def test_connection_unsubscribe_repository(self, sample_connection):
        """测试取消订阅仓库"""
        sample_connection.subscribe_repository(123)
        sample_connection.unsubscribe_repository(123)

        assert 123 not in sample_connection.repository_ids

    def test_connection_update_ping(self, sample_connection):
        """测试更新心跳时间"""
        import time
        old_ping = sample_connection.last_ping
        time.sleep(0.01)  # 等待10毫秒确保时间变化
        sample_connection.update_ping()

        assert sample_connection.last_ping >= old_ping

    def test_connection_is_timeout(self, sample_connection):
        """测试连接超时检测"""
        # 设置心跳时间为很久以前
        sample_connection.last_ping = datetime.now() - timedelta(seconds=200)

        assert sample_connection.is_timeout(timeout_seconds=120) is True

    def test_connection_is_not_timeout(self, sample_connection):
        """测试连接未超时"""
        sample_connection.update_ping()

        assert sample_connection.is_timeout(timeout_seconds=120) is False

    def test_connection_to_dict(self, sample_connection):
        """测试转换为字典"""
        sample_connection.bind_user(1, "testuser")
        sample_connection.subscribe_repository(123)

        data = sample_connection.to_dict()

        assert data["connection_id"] == "test_conn_001"
        assert data["user_id"] == 1
        assert data["username"] == "testuser"
        assert 123 in data["repository_ids"]
        assert "connected_at" in data
        assert "last_ping" in data


# ==================== ConnectionManager测试 ====================

class TestConnectionManager:
    """测试ConnectionManager类"""

    @pytest.mark.asyncio
    async def test_connect(self, connection_manager, mock_websocket):
        """测试接受新连接"""
        connection = await connection_manager.connect(mock_websocket)

        assert connection is not None
        assert connection.connection_id.startswith("conn_")
        assert connection.connection_id in connection_manager._connections
        mock_websocket.accept.assert_called_once()

    def test_disconnect(self, connection_manager, sample_connection):
        """测试断开连接"""
        # 先添加连接
        connection_manager._connections[sample_connection.connection_id] = sample_connection
        connection_manager.bind_user(sample_connection, 1, "testuser")
        connection_manager.subscribe_repository(sample_connection, 123)

        # 断开连接
        connection_manager.disconnect(sample_connection)

        assert sample_connection.connection_id not in connection_manager._connections
        assert sample_connection.is_alive is False

    def test_bind_user(self, connection_manager, sample_connection):
        """测试绑定用户"""
        connection_manager._connections[sample_connection.connection_id] = sample_connection

        connection_manager.bind_user(sample_connection, 1, "testuser")

        assert sample_connection.user_id == 1
        assert 1 in connection_manager._user_index
        assert sample_connection.connection_id in connection_manager._user_index[1]

    def test_subscribe_repository(self, connection_manager, sample_connection):
        """测试订阅仓库"""
        connection_manager._connections[sample_connection.connection_id] = sample_connection

        connection_manager.subscribe_repository(sample_connection, 123)

        assert 123 in sample_connection.repository_ids
        assert 123 in connection_manager._repository_index
        assert sample_connection.connection_id in connection_manager._repository_index[123]

    def test_unsubscribe_repository(self, connection_manager, sample_connection):
        """测试取消订阅仓库"""
        connection_manager._connections[sample_connection.connection_id] = sample_connection
        connection_manager.subscribe_repository(sample_connection, 123)

        connection_manager.unsubscribe_repository(sample_connection, 123)

        assert 123 not in sample_connection.repository_ids
        assert 123 not in connection_manager._repository_index

    @pytest.mark.asyncio
    async def test_send_to_connection(self, connection_manager, sample_connection, mock_websocket):
        """测试发送消息到指定连接"""
        connection_manager._connections[sample_connection.connection_id] = sample_connection

        message = {"type": "test"}
        result = await connection_manager.send_to_connection(sample_connection.connection_id, message)

        assert result is True
        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_user(self, connection_manager, mock_websocket):
        """测试发送消息给用户"""
        # 创建两个连接绑定到同一用户
        conn1 = Connection(mock_websocket, "conn_1")
        conn2 = Connection(mock_websocket, "conn_2")

        connection_manager._connections["conn_1"] = conn1
        connection_manager._connections["conn_2"] = conn2
        connection_manager.bind_user(conn1, 1, "testuser")
        connection_manager.bind_user(conn2, 1, "testuser")

        message = {"type": "notification"}
        count = await connection_manager.send_to_user(1, message)

        assert count == 2
        assert mock_websocket.send_json.call_count == 2

    @pytest.mark.asyncio
    async def test_send_to_repository(self, connection_manager, mock_websocket):
        """测试发送消息到仓库订阅者"""
        # 创建两个连接订阅同一仓库
        conn1 = Connection(mock_websocket, "conn_1")
        conn2 = Connection(mock_websocket, "conn_2")
        conn1.bind_user(1, "user1")
        conn2.bind_user(2, "user2")

        connection_manager._connections["conn_1"] = conn1
        connection_manager._connections["conn_2"] = conn2
        connection_manager.subscribe_repository(conn1, 123)
        connection_manager.subscribe_repository(conn2, 123)

        message = {"type": "commit_new"}
        count = await connection_manager.send_to_repository(123, message)

        assert count == 2

    @pytest.mark.asyncio
    async def test_send_to_repository_exclude_user(self, connection_manager, mock_websocket):
        """测试发送消息到仓库订阅者（排除特定用户）"""
        conn1 = Connection(mock_websocket, "conn_1")
        conn2 = Connection(mock_websocket, "conn_2")
        conn1.bind_user(1, "user1")
        conn2.bind_user(2, "user2")

        connection_manager._connections["conn_1"] = conn1
        connection_manager._connections["conn_2"] = conn2
        connection_manager.subscribe_repository(conn1, 123)
        connection_manager.subscribe_repository(conn2, 123)

        message = {"type": "commit_new"}
        count = await connection_manager.send_to_repository(123, message, exclude_user_id=1)

        assert count == 1

    @pytest.mark.asyncio
    async def test_broadcast(self, connection_manager, mock_websocket):
        """测试广播消息"""
        conn1 = Connection(mock_websocket, "conn_1")
        conn2 = Connection(mock_websocket, "conn_2")

        connection_manager._connections["conn_1"] = conn1
        connection_manager._connections["conn_2"] = conn2

        message = {"type": "system"}
        count = await connection_manager.broadcast(message)

        assert count == 2

    def test_register_handler(self, connection_manager):
        """测试注册消息处理器"""
        handler = Mock()

        connection_manager.register_handler("custom_type", handler)

        assert "custom_type" in connection_manager._message_handlers
        assert connection_manager._message_handlers["custom_type"] == handler

    @pytest.mark.asyncio
    async def test_handle_message_with_handler(self, connection_manager, sample_connection, mock_websocket):
        """测试处理已知类型的消息"""
        handler = AsyncMock()
        connection_manager.register_handler("test_type", handler)

        message = {"type": "test_type", "data": "test"}
        await connection_manager.handle_message(sample_connection, message)

        handler.assert_called_once_with(sample_connection, message)

    @pytest.mark.asyncio
    async def test_handle_message_unknown_type(self, connection_manager, sample_connection, mock_websocket):
        """测试处理未知类型的消息"""
        message = {"type": "unknown_type"}
        await connection_manager.handle_message(sample_connection, message)

        # 应该发送错误消息
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert "未知的消息类型" in call_args["error"]

    @pytest.mark.asyncio
    async def test_handle_message_handler_exception(self, connection_manager, sample_connection, mock_websocket):
        """测试消息处理器抛出异常"""
        handler = AsyncMock(side_effect=Exception("处理失败"))
        connection_manager.register_handler("test_type", handler)

        message = {"type": "test_type"}
        await connection_manager.handle_message(sample_connection, message)

        # 应该发送错误消息
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error"


# ==================== 认证模块测试 ====================

class TestWebSocketAuth:
    """测试WebSocket认证模块"""

    @pytest.mark.asyncio
    async def test_extract_token_from_query(self):
        """测试从query参数提取token"""
        ws = Mock()
        ws.query_params = {"token": "test_token_123"}

        token = await extract_token_from_query(ws)

        assert token == "test_token_123"

    @pytest.mark.asyncio
    async def test_extract_token_from_access_token_param(self):
        """测试从access_token参数提取token"""
        ws = Mock()
        ws.query_params = {"access_token": "test_token_456"}

        token = await extract_token_from_query(ws)

        assert token == "test_token_456"

    @pytest.mark.asyncio
    async def test_extract_token_not_found(self):
        """测试token不存在"""
        ws = Mock()
        ws.query_params = {}

        token = await extract_token_from_query(ws)

        assert token is None

    @pytest.mark.asyncio
    async def test_verify_token_dev_token(self):
        """测试开发测试token验证"""
        result = await verify_token("dev_test_token")

        assert result is not None
        assert result["user_id"] == 1
        assert result["username"] == "developer"
        assert result["is_admin"] is True

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self):
        """测试无效token验证"""
        result = await verify_token("invalid_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_websocket_success(self):
        """测试WebSocket认证成功"""
        ws = Mock()
        ws.query_params = {"token": "dev_test_token"}

        result = await authenticate_websocket(ws)

        assert result is not None
        assert result["user_id"] == 1

    @pytest.mark.asyncio
    async def test_authenticate_websocket_no_token(self):
        """测试WebSocket没有token"""
        ws = Mock()
        ws.query_params = {}

        with pytest.raises(WebSocketAuthError) as exc_info:
            await authenticate_websocket(ws)

        assert exc_info.value.code == 1008

    @pytest.mark.asyncio
    async def test_authenticate_websocket_optional_with_token(self):
        """测试可选认证（有token）"""
        ws = Mock()
        ws.query_params = {"token": "dev_test_token"}

        result = await authenticate_websocket_optional(ws)

        assert result is not None

    @pytest.mark.asyncio
    async def test_authenticate_websocket_optional_without_token(self):
        """测试可选认证（无token）"""
        ws = Mock()
        ws.query_params = {}

        result = await authenticate_websocket_optional(ws)

        assert result is None


# ==================== 消息处理器测试 ====================

class TestNotificationHandlers:
    """测试通知消息处理器"""

    @pytest.mark.asyncio
    async def test_handle_ping(self, sample_connection, mock_websocket):
        """测试处理ping消息"""
        message = {"type": "ping", "timestamp": "2024-01-01T00:00:00Z"}

        await handle_ping(sample_connection, message)

        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert response["type"] == "pong"
        assert response["timestamp"] == "2024-01-01T00:00:00Z"
        assert "server_time" in response

    @pytest.mark.asyncio
    async def test_handle_subscribe_repository(self, sample_connection, mock_websocket, connection_manager):
        """测试处理仓库订阅请求"""
        connection_manager._connections[sample_connection.connection_id] = sample_connection

        message = {"type": "subscribe", "channel": "repository", "repository_id": 123}
        await handle_subscribe(sample_connection, message)

        assert 123 in sample_connection.repository_ids
        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert response["type"] == "subscribed"

    @pytest.mark.asyncio
    async def test_handle_subscribe_repository_missing_id(self, sample_connection, mock_websocket):
        """测试订阅仓库缺少ID"""
        message = {"type": "subscribe", "channel": "repository"}
        await handle_subscribe(sample_connection, message)

        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert response["type"] == "error"

    @pytest.mark.asyncio
    async def test_handle_subscribe_user_notifications(self, sample_connection, mock_websocket):
        """测试处理用户通知订阅"""
        message = {"type": "subscribe", "channel": "user_notifications"}
        await handle_subscribe(sample_connection, message)

        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert response["type"] == "subscribed"
        assert response["channel"] == "user_notifications"

    @pytest.mark.asyncio
    async def test_handle_unsubscribe_repository(self, sample_connection, mock_websocket, connection_manager):
        """测试处理取消订阅仓库"""
        connection_manager._connections[sample_connection.connection_id] = sample_connection
        connection_manager.subscribe_repository(sample_connection, 123)

        message = {"type": "unsubscribe", "channel": "repository", "repository_id": 123}
        await handle_unsubscribe(sample_connection, message)

        assert 123 not in sample_connection.repository_ids

    @pytest.mark.asyncio
    async def test_handle_broadcast_admin(self, sample_connection, mock_websocket):
        """测试管理员广播消息"""
        sample_connection.metadata["is_admin"] = True
        sample_connection.username = "admin"

        message = {
            "type": "broadcast",
            "content": {"type": "system_notification", "message": "系统维护"}
        }
        await handle_broadcast(sample_connection, message)

        # 广播应该成功
        mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_handle_broadcast_not_admin(self, sample_connection, mock_websocket):
        """测试非管理员广播消息"""
        sample_connection.metadata["is_admin"] = False

        message = {"type": "broadcast", "content": {"message": "test"}}
        await handle_broadcast(sample_connection, message)

        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert response["type"] == "error"
        assert "权限不足" in response["error"]


class TestSyncHandlers:
    """测试同步消息处理器"""

    @pytest.mark.asyncio
    async def test_handle_sync_request_missing_repo_id(self, sample_connection, mock_websocket):
        """测试同步请求缺少仓库ID"""
        message = {"type": "sync_request", "sync_type": "pull"}
        await handle_sync_request(sample_connection, message)

        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert response["type"] == "sync_response"
        assert response["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_handle_sync_request_not_subscribed(self, sample_connection, mock_websocket):
        """测试同步请求未订阅仓库"""
        message = {"type": "sync_request", "repository_id": 123, "sync_type": "pull"}
        await handle_sync_request(sample_connection, message)

        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert response["status"] == "rejected"
        assert "未订阅该仓库" in response["error"]


class TestProgressHandlers:
    """测试进度消息处理器"""

    @pytest.mark.asyncio
    async def test_handle_progress_update(self, sample_connection, mock_websocket):
        """测试处理进度更新"""
        message = {
            "type": "progress_update",
            "operation_id": "op_123",
            "operation_type": "clone",
            "progress": 50,
            "status": "running",
            "message": "正在克隆..."
        }
        await handle_progress_update(sample_connection, message)

        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert response["type"] == "progress"
        assert response["operation_id"] == "op_123"
        assert response["progress"] == 50

    @pytest.mark.asyncio
    async def test_handle_progress_update_missing_operation_id(self, sample_connection, mock_websocket):
        """测试进度更新缺少operation_id"""
        message = {"type": "progress_update", "progress": 50}
        await handle_progress_update(sample_connection, message)

        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert response["type"] == "error"


# ==================== 通知推送函数测试 ====================

class TestNotificationPushFunctions:
    """测试通知推送函数"""

    @pytest.mark.asyncio
    async def test_notify_commit_new(self, mock_websocket):
        """测试推送新提交通知"""
        # 重置manager
        ConnectionManager._instance = None
        ConnectionManager._initialized = False
        test_manager = ConnectionManager()

        # 创建连接并订阅仓库
        conn = Connection(mock_websocket, "conn_1")
        conn.bind_user(1, "user1")
        test_manager._connections["conn_1"] = conn
        test_manager.subscribe_repository(conn, 123)

        commit_data = {"hash": "abc123", "message": "Fix bug"}
        count = await notify_commit_new(123, commit_data)

        assert count >= 0

    @pytest.mark.asyncio
    async def test_notify_branch_update(self, mock_websocket):
        """测试推送分支更新通知"""
        ConnectionManager._instance = None
        ConnectionManager._initialized = False
        test_manager = ConnectionManager()

        conn = Connection(mock_websocket, "conn_1")
        test_manager._connections["conn_1"] = conn
        test_manager.subscribe_repository(conn, 123)

        branch_data = {"name": "main", "commit": "def456"}
        count = await notify_branch_update(123, branch_data)

        assert count >= 0

    @pytest.mark.asyncio
    async def test_notify_user(self, mock_websocket):
        """测试推送用户通知"""
        ConnectionManager._instance = None
        ConnectionManager._initialized = False
        test_manager = ConnectionManager()

        conn = Connection(mock_websocket, "conn_1")
        conn.bind_user(1, "user1")
        test_manager._connections["conn_1"] = conn
        test_manager.bind_user(conn, 1, "user1")

        count = await notify_user(1, "test_notification", {"message": "Hello"})

        assert count >= 0


# ==================== 单例模式测试 ====================

class TestSingletonPattern:
    """测试单例模式"""

    def test_manager_singleton(self):
        """测试manager是单例"""
        from api.websocket.manager import manager as manager1
        from api.websocket.manager import ConnectionManager

        # 重置单例以获取新实例
        ConnectionManager._instance = None
        ConnectionManager._initialized = False

        manager2 = ConnectionManager()
        manager3 = ConnectionManager()

        assert manager2 is manager3

    def test_manager_initialized_once(self):
        """测试manager只初始化一次"""
        ConnectionManager._instance = None
        ConnectionManager._initialized = False

        manager1 = ConnectionManager()
        # 修改一个属性
        manager1._connection_counter = 100

        manager2 = ConnectionManager()
        # 第二个实例应该共享相同的属性
        assert manager2._connection_counter == 100


# ==================== 集成测试 ====================

@pytest.mark.asyncio
async def test_full_message_flow(connection_manager, mock_websocket):
    """测试完整的消息流程"""
    # 1. 建立连接
    connection = await connection_manager.connect(mock_websocket)

    # 2. 绑定用户
    connection_manager.bind_user(connection, 1, "testuser")

    # 3. 订阅仓库
    connection_manager.subscribe_repository(connection, 123)

    # 4. 注册测试处理器
    test_handler = AsyncMock()
    connection_manager.register_handler("test_action", test_handler)

    # 5. 发送消息
    message = {"type": "test_action", "data": "test_data"}
    await connection_manager.handle_message(connection, message)

    # 6. 验证处理器被调用
    test_handler.assert_called_once_with(connection, message)

    # 7. 断开连接
    connection_manager.disconnect(connection)
    assert connection.connection_id not in connection_manager._connections
