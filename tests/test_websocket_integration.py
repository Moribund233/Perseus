"""
WebSocket集成测试模块

测试范围:
1. 完整的WebSocket连接流程
2. 消息收发
3. 认证流程
4. 订阅/取消订阅
5. 通知推送
6. 多客户端交互

运行方式:
    pytest tests/test_websocket_integration.py -v

注意:
    这些测试需要启动FastAPI服务器才能运行
    可以使用: python -m uvicorn app:app --host 0.0.0.0 --port 8080
"""
import pytest
import asyncio
import json
import websockets
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

# 测试服务器配置
TEST_WS_URL = "ws://localhost:8080/ws/"
TEST_WS_NOTIFICATIONS_URL = "ws://localhost:8080/ws/notifications"
TEST_WS_REPOSITORY_URL = "ws://localhost:8080/ws/repository/{repository_id}"

# 测试Token（使用开发测试token）
TEST_TOKEN = "dev_test_token"


class WebSocketTestClient:
    """WebSocket测试客户端"""

    def __init__(self, url: str):
        self.url = url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.messages: List[Dict[str, Any]] = []
        self.connection_id: Optional[str] = None
        self.authenticated = False

    async def connect(self, token: Optional[str] = None):
        """建立WebSocket连接"""
        url = self.url
        if token:
            url = f"{url}?token={token}"

        self.websocket = await websockets.connect(url)

        # 等待connected消息
        try:
            message = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=5.0
            )
            data = json.loads(message)
            self.messages.append(data)

            if data.get("type") == "connected":
                self.connection_id = data.get("connection_id")
                self.authenticated = data.get("authenticated", False)

            return data
        except asyncio.TimeoutError:
            raise Exception("等待connected消息超时")

    async def send(self, message: Dict[str, Any]):
        """发送消息"""
        if not self.websocket:
            raise Exception("WebSocket未连接")
        await self.websocket.send(json.dumps(message))

    async def receive(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """接收消息"""
        if not self.websocket:
            raise Exception("WebSocket未连接")

        try:
            message = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=timeout
            )
            data = json.loads(message)
            self.messages.append(data)
            return data
        except asyncio.TimeoutError:
            return None

    async def receive_all(self, timeout: float = 1.0) -> List[Dict[str, Any]]:
        """接收所有可用消息"""
        messages = []
        while True:
            try:
                message = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=0.1
                )
                data = json.loads(message)
                self.messages.append(data)
                messages.append(data)
            except asyncio.TimeoutError:
                break
        return messages

    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

    async def ping(self) -> bool:
        """发送ping消息"""
        await self.send({
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        })

        # 等待pong响应
        response = await self.receive(timeout=2.0)
        return response is not None and response.get("type") == "pong"

    async def subscribe_repository(self, repository_id: int) -> bool:
        """订阅仓库"""
        await self.send({
            "type": "subscribe",
            "channel": "repository",
            "repository_id": repository_id
        })

        response = await self.receive(timeout=2.0)
        return response is not None and response.get("type") == "subscribed"

    async def unsubscribe_repository(self, repository_id: int) -> bool:
        """取消订阅仓库"""
        await self.send({
            "type": "unsubscribe",
            "channel": "repository",
            "repository_id": repository_id
        })

        response = await self.receive(timeout=2.0)
        return response is not None and response.get("type") == "unsubscribed"


@pytest.fixture
async def ws_client():
    """创建WebSocket测试客户端"""
    client = WebSocketTestClient(TEST_WS_URL)
    yield client
    await client.close()


@pytest.fixture
async def authenticated_client():
    """创建已认证的WebSocket测试客户端"""
    client = WebSocketTestClient(TEST_WS_URL)
    await client.connect(token=TEST_TOKEN)
    yield client
    await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestWebSocketConnection:
    """测试WebSocket连接"""

    async def test_anonymous_connection(self):
        """测试匿名连接"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            response = await client.connect()

            assert response["type"] == "connected"
            assert response["authenticated"] is False
            assert "connection_id" in response
            assert "匿名模式" in response["message"]
        finally:
            await client.close()

    async def test_authenticated_connection(self):
        """测试认证连接"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            response = await client.connect(token=TEST_TOKEN)

            assert response["type"] == "connected"
            assert response["authenticated"] is True
            assert "connection_id" in response
            assert "user" in response
            assert response["user"]["id"] == 1
            assert response["user"]["username"] == "developer"
        finally:
            await client.close()

    async def test_invalid_token_connection(self):
        """测试无效token连接"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            # 尝试用无效token连接
            url = f"{TEST_WS_URL}?token=invalid_token"
            ws = await websockets.connect(url)

            # 应该收到错误并断开
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=2.0)
                # 如果收到消息，应该是错误消息
                data = json.loads(message)
                # 或者连接应该被关闭
            except websockets.exceptions.ConnectionClosed:
                pass  # 预期行为
            finally:
                await ws.close()
        except websockets.exceptions.ConnectionClosed:
            pass  # 预期行为

    async def test_multiple_connections(self):
        """测试多个并发连接"""
        clients = []
        try:
            # 创建5个并发连接
            for i in range(5):
                client = WebSocketTestClient(TEST_WS_URL)
                response = await client.connect(token=TEST_TOKEN)
                assert response["type"] == "connected"
                clients.append(client)

            # 验证所有连接都有唯一的connection_id
            connection_ids = [c.connection_id for c in clients]
            assert len(set(connection_ids)) == 5

        finally:
            for client in clients:
                await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestWebSocketMessages:
    """测试WebSocket消息"""

    async def test_ping_pong(self):
        """测试心跳消息"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            # 发送ping
            await client.send({
                "type": "ping",
                "timestamp": datetime.now().isoformat()
            })

            # 接收pong
            response = await client.receive(timeout=2.0)
            assert response is not None
            assert response["type"] == "pong"
            assert "server_time" in response

        finally:
            await client.close()

    async def test_unknown_message_type(self):
        """测试未知消息类型"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            # 发送未知类型的消息
            await client.send({
                "type": "unknown_type",
                "data": "test"
            })

            # 应该收到错误消息
            response = await client.receive(timeout=2.0)
            assert response is not None
            assert response["type"] == "error"
            assert "未知的消息类型" in response["error"]

        finally:
            await client.close()

    async def test_malformed_json(self):
        """测试无效的JSON消息"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            # 发送无效的JSON
            await client.websocket.send("invalid json {")

            # 等待可能的错误响应或连接关闭
            try:
                response = await client.receive(timeout=2.0)
                # 可能收到错误消息
            except websockets.exceptions.ConnectionClosed:
                pass  # 连接可能被关闭

        finally:
            await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestWebSocketSubscription:
    """测试WebSocket订阅功能"""

    async def test_subscribe_repository(self):
        """测试订阅仓库"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            # 订阅仓库
            await client.send({
                "type": "subscribe",
                "channel": "repository",
                "repository_id": 123
            })

            response = await client.receive(timeout=2.0)
            assert response is not None
            assert response["type"] == "subscribed"
            assert response["channel"] == "repository"
            assert response["repository_id"] == 123

        finally:
            await client.close()

    async def test_subscribe_repository_missing_id(self):
        """测试订阅仓库缺少ID"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            # 订阅仓库但不提供repository_id
            await client.send({
                "type": "subscribe",
                "channel": "repository"
            })

            response = await client.receive(timeout=2.0)
            assert response is not None
            assert response["type"] == "error"
            assert "repository_id" in response["error"]

        finally:
            await client.close()

    async def test_unsubscribe_repository(self):
        """测试取消订阅仓库"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            # 先订阅
            await client.subscribe_repository(123)

            # 取消订阅
            await client.send({
                "type": "unsubscribe",
                "channel": "repository",
                "repository_id": 123
            })

            response = await client.receive(timeout=2.0)
            assert response is not None
            assert response["type"] == "unsubscribed"

        finally:
            await client.close()

    async def test_subscribe_user_notifications(self):
        """测试订阅用户通知"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            await client.send({
                "type": "subscribe",
                "channel": "user_notifications"
            })

            response = await client.receive(timeout=2.0)
            assert response is not None
            assert response["type"] == "subscribed"
            assert response["channel"] == "user_notifications"

        finally:
            await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestWebSocketSync:
    """测试WebSocket同步功能"""

    async def test_sync_request_without_subscription(self):
        """测试未订阅时发送同步请求"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            # 发送同步请求（未订阅仓库）
            await client.send({
                "type": "sync_request",
                "repository_id": 123,
                "sync_type": "pull",
                "request_id": str(uuid.uuid4())
            })

            response = await client.receive(timeout=2.0)
            assert response is not None
            assert response["type"] == "sync_response"
            assert response["status"] == "rejected"
            assert "未订阅该仓库" in response["error"]

        finally:
            await client.close()

    async def test_sync_request_with_subscription(self):
        """测试订阅后发送同步请求"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            # 先订阅仓库
            await client.subscribe_repository(123)

            # 发送同步请求
            request_id = str(uuid.uuid4())
            await client.send({
                "type": "sync_request",
                "repository_id": 123,
                "sync_type": "pull",
                "request_id": request_id
            })

            response = await client.receive(timeout=2.0)
            assert response is not None
            assert response["type"] == "sync_response"
            assert response["status"] == "accepted"
            assert response["request_id"] == request_id

        finally:
            await client.close()

    async def test_sync_status_update(self):
        """测试同步状态更新"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)
            await client.subscribe_repository(123)

            # 发送同步状态更新
            await client.send({
                "type": "sync_status",
                "repository_id": 123,
                "status": "in_progress",
                "progress": 50,
                "message": "Syncing..."
            })

            # 同步状态更新可能不会收到响应，取决于实现
            # 这里主要测试消息能被正确处理而不报错

        finally:
            await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestWebSocketProgress:
    """测试WebSocket进度功能"""

    async def test_progress_update(self):
        """测试进度更新"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            operation_id = str(uuid.uuid4())

            # 发送进度更新
            await client.send({
                "type": "progress_update",
                "operation_id": operation_id,
                "operation_type": "clone",
                "progress": 50,
                "status": "running",
                "message": "Cloning repository..."
            })

            # 应该收到进度推送
            response = await client.receive(timeout=2.0)
            assert response is not None
            assert response["type"] == "progress"
            assert response["operation_id"] == operation_id
            assert response["progress"] == 50

        finally:
            await client.close()

    async def test_progress_update_missing_operation_id(self):
        """测试进度更新缺少operation_id"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            # 发送进度更新（缺少operation_id）
            await client.send({
                "type": "progress_update",
                "progress": 50
            })

            response = await client.receive(timeout=2.0)
            assert response is not None
            assert response["type"] == "error"
            assert "operation_id" in response["error"]

        finally:
            await client.close()

    async def test_progress_completed(self):
        """测试进度完成"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            operation_id = str(uuid.uuid4())

            # 发送完成的进度
            await client.send({
                "type": "progress_update",
                "operation_id": operation_id,
                "operation_type": "clone",
                "progress": 100,
                "status": "completed",
                "message": "Clone completed"
            })

            response = await client.receive(timeout=2.0)
            assert response is not None
            assert response["type"] == "progress"
            assert response["status"] == "completed"

        finally:
            await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestWebSocketNotifications:
    """测试WebSocket通知功能"""

    async def test_notification_endpoint(self):
        """测试通知专用端点"""
        client = WebSocketTestClient(TEST_WS_NOTIFICATIONS_URL)
        try:
            # 通知端点需要认证
            response = await client.connect(token=TEST_TOKEN)

            assert response["type"] == "connected"
            assert response["channel"] == "user_notifications"

        finally:
            await client.close()

    async def test_notification_endpoint_without_token(self):
        """测试通知端点无token"""
        client = WebSocketTestClient(TEST_WS_NOTIFICATIONS_URL)
        try:
            # 尝试无token连接
            await client.connect()
            # 应该失败或收到错误
        except Exception:
            pass  # 预期行为
        finally:
            await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestWebSocketMultiClient:
    """测试多客户端交互"""

    async def test_broadcast_to_subscribers(self):
        """测试广播给订阅者"""
        client1 = WebSocketTestClient(TEST_WS_URL)
        client2 = WebSocketTestClient(TEST_WS_URL)

        try:
            # 两个客户端都连接并订阅同一个仓库
            await client1.connect(token=TEST_TOKEN)
            await client2.connect(token=TEST_TOKEN)

            await client1.subscribe_repository(123)
            await client2.subscribe_repository(123)

            # 注意：实际测试广播需要服务器端触发
            # 这里主要测试订阅功能正常

        finally:
            await client1.close()
            await client2.close()

    async def test_multiple_subscriptions(self):
        """测试多个订阅"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            # 订阅多个仓库
            for repo_id in [1, 2, 3]:
                success = await client.subscribe_repository(repo_id)
                assert success is True

            # 取消订阅其中一个
            success = await client.unsubscribe_repository(2)
            assert success is True

        finally:
            await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestWebSocketStress:
    """WebSocket压力测试"""

    async def test_rapid_messages(self):
        """测试快速发送消息"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            # 快速发送10条ping消息
            for i in range(10):
                await client.send({
                    "type": "ping",
                    "timestamp": datetime.now().isoformat(),
                    "seq": i
                })

            # 接收所有响应
            await asyncio.sleep(0.5)
            messages = await client.receive_all(timeout=1.0)

            # 应该收到pong响应
            pong_count = sum(1 for m in messages if m.get("type") == "pong")
            assert pong_count >= 5  # 至少收到一半响应

        finally:
            await client.close()

    async def test_large_message(self):
        """测试大消息"""
        client = WebSocketTestClient(TEST_WS_URL)
        try:
            await client.connect(token=TEST_TOKEN)

            # 发送较大的消息
            large_data = "x" * 10000
            await client.send({
                "type": "ping",
                "data": large_data
            })

            # 应该能正常处理
            response = await client.receive(timeout=2.0)
            assert response is not None

        finally:
            await client.close()


# 运行测试的辅助函数
def run_integration_tests():
    """运行所有集成测试"""
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "integration"
    ])


if __name__ == "__main__":
    print("WebSocket集成测试")
    print("================")
    print(f"测试服务器: {TEST_WS_URL}")
    print()
    print("请确保FastAPI服务器已启动:")
    print("  python -m uvicorn app:app --host 0.0.0.0 --port 8080")
    print()
    print("运行测试:")
    print("  pytest tests/test_websocket_integration.py -v")
