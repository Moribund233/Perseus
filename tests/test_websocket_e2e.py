"""
WebSocket端到端测试脚本

这个脚本用于手动测试WebSocket功能，可以直接运行验证WebSocket是否正常工作。

使用方法:
    1. 启动FastAPI服务器:
       python -m uvicorn app:app --host 0.0.0.0 --port 8080

    2. 运行测试脚本:
       python tests/test_websocket_e2e.py

测试内容:
    1. 匿名连接测试
    2. 认证连接测试
    3. 心跳测试
    4. 订阅/取消订阅测试
    5. 同步请求测试
    6. 进度更新测试
    7. 多客户端测试
"""
import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any
import websockets

# 测试配置
WS_URL = "ws://localhost:8080/ws/"
WS_NOTIFICATIONS_URL = "ws://localhost:8080/ws/notifications"
TEST_TOKEN = "dev_test_token"


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")


class WebSocketTester:
    """WebSocket测试器"""

    def __init__(self, name: str):
        self.name = name
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connection_id: Optional[str] = None
        self.authenticated = False
        self.messages_received: list = []

    async def connect(self, url: str, token: Optional[str] = None) -> bool:
        """建立WebSocket连接"""
        try:
            full_url = url
            if token:
                full_url = f"{url}?token={token}"

            print_info(f"[{self.name}] 连接到 {full_url}")
            self.websocket = await websockets.connect(full_url)

            # 等待connected消息
            message = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            data = json.loads(message)
            self.messages_received.append(data)

            if data.get("type") == "connected":
                self.connection_id = data.get("connection_id")
                self.authenticated = data.get("authenticated", False)
                print_success(f"[{self.name}] 连接成功 (ID: {self.connection_id})")
                if self.authenticated:
                    print_info(f"[{self.name}] 已认证用户: {data.get('user', {})}")
                else:
                    print_info(f"[{self.name}] 匿名连接")
                return True
            else:
                print_error(f"[{self.name}] 未收到connected消息: {data}")
                return False

        except Exception as e:
            print_error(f"[{self.name}] 连接失败: {e}")
            return False

    async def send(self, message: Dict[str, Any]) -> bool:
        """发送消息"""
        try:
            if not self.websocket:
                print_error(f"[{self.name}] WebSocket未连接")
                return False

            await self.websocket.send(json.dumps(message))
            print_info(f"[{self.name}] 发送: {message}")
            return True
        except Exception as e:
            print_error(f"[{self.name}] 发送失败: {e}")
            return False

    async def receive(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """接收消息"""
        try:
            if not self.websocket:
                print_error(f"[{self.name}] WebSocket未连接")
                return None

            message = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            data = json.loads(message)
            self.messages_received.append(data)
            print_info(f"[{self.name}] 接收: {data}")
            return data
        except asyncio.TimeoutError:
            print_warning(f"[{self.name}] 接收超时")
            return None
        except Exception as e:
            print_error(f"[{self.name}] 接收失败: {e}")
            return None

    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            print_info(f"[{self.name}] 连接已关闭")


async def test_anonymous_connection():
    """测试1: 匿名连接"""
    print("\n" + "="*50)
    print("测试1: 匿名连接")
    print("="*50)

    tester = WebSocketTester("匿名客户端")
    try:
        success = await tester.connect(WS_URL)
        if success and not tester.authenticated:
            print_success("匿名连接测试通过")
            return True
        else:
            print_error("匿名连接测试失败")
            return False
    finally:
        await tester.close()


async def test_authenticated_connection():
    """测试2: 认证连接"""
    print("\n" + "="*50)
    print("测试2: 认证连接")
    print("="*50)

    tester = WebSocketTester("认证客户端")
    try:
        success = await tester.connect(WS_URL, token=TEST_TOKEN)
        if success and tester.authenticated:
            print_success("认证连接测试通过")
            return True
        else:
            print_error("认证连接测试失败")
            return False
    finally:
        await tester.close()


async def test_heartbeat():
    """测试3: 心跳检测"""
    print("\n" + "="*50)
    print("测试3: 心跳检测")
    print("="*50)

    tester = WebSocketTester("心跳测试客户端")
    try:
        await tester.connect(WS_URL, token=TEST_TOKEN)

        # 发送ping
        await tester.send({
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        })

        # 接收pong
        response = await tester.receive(timeout=2.0)
        if response and response.get("type") == "pong":
            print_success("心跳检测测试通过")
            return True
        else:
            print_error("心跳检测测试失败")
            return False
    finally:
        await tester.close()


async def test_subscription():
    """测试4: 订阅/取消订阅"""
    print("\n" + "="*50)
    print("测试4: 订阅/取消订阅")
    print("="*50)

    tester = WebSocketTester("订阅测试客户端")
    try:
        await tester.connect(WS_URL, token=TEST_TOKEN)

        # 订阅仓库
        print_info("订阅仓库 123...")
        await tester.send({
            "type": "subscribe",
            "channel": "repository",
            "repository_id": 123
        })

        response = await tester.receive(timeout=2.0)
        if not response or response.get("type") != "subscribed":
            print_error("订阅仓库测试失败")
            return False
        print_success("订阅仓库成功")

        # 订阅用户通知
        print_info("订阅用户通知...")
        await tester.send({
            "type": "subscribe",
            "channel": "user_notifications"
        })

        response = await tester.receive(timeout=2.0)
        if not response or response.get("type") != "subscribed":
            print_error("订阅用户通知测试失败")
            return False
        print_success("订阅用户通知成功")

        # 取消订阅
        print_info("取消订阅仓库 123...")
        await tester.send({
            "type": "unsubscribe",
            "channel": "repository",
            "repository_id": 123
        })

        response = await tester.receive(timeout=2.0)
        if not response or response.get("type") != "unsubscribed":
            print_error("取消订阅测试失败")
            return False
        print_success("取消订阅成功")

        print_success("订阅/取消订阅测试通过")
        return True
    finally:
        await tester.close()


async def test_sync_request():
    """测试5: 同步请求"""
    print("\n" + "="*50)
    print("测试5: 同步请求")
    print("="*50)

    tester = WebSocketTester("同步测试客户端")
    try:
        await tester.connect(WS_URL, token=TEST_TOKEN)

        # 先订阅仓库
        await tester.send({
            "type": "subscribe",
            "channel": "repository",
            "repository_id": 456
        })
        await tester.receive(timeout=2.0)

        # 发送同步请求
        print_info("发送同步请求...")
        await tester.send({
            "type": "sync_request",
            "repository_id": 456,
            "sync_type": "pull",
            "request_id": f"test_req_{int(time.time())}"
        })

        response = await tester.receive(timeout=2.0)
        if response and response.get("type") == "sync_response":
            if response.get("status") == "accepted":
                print_success("同步请求被接受")
            else:
                print_warning(f"同步请求被拒绝: {response.get('error')}")
            print_success("同步请求测试通过")
            return True
        else:
            print_error("同步请求测试失败")
            return False
    finally:
        await tester.close()


async def test_progress_update():
    """测试6: 进度更新"""
    print("\n" + "="*50)
    print("测试6: 进度更新")
    print("="*50)

    tester = WebSocketTester("进度测试客户端")
    try:
        await tester.connect(WS_URL, token=TEST_TOKEN)

        # 发送进度更新
        print_info("发送进度更新...")
        await tester.send({
            "type": "progress_update",
            "operation_id": f"op_{int(time.time())}",
            "operation_type": "clone",
            "progress": 50,
            "status": "running",
            "message": "Cloning repository..."
        })

        response = await tester.receive(timeout=2.0)
        if response and response.get("type") == "progress":
            print_success("进度更新测试通过")
            return True
        else:
            print_error("进度更新测试失败")
            return False
    finally:
        await tester.close()


async def test_unknown_message():
    """测试7: 未知消息类型"""
    print("\n" + "="*50)
    print("测试7: 未知消息类型")
    print("="*50)

    tester = WebSocketTester("错误测试客户端")
    try:
        await tester.connect(WS_URL, token=TEST_TOKEN)

        # 发送未知类型的消息
        print_info("发送未知类型消息...")
        await tester.send({
            "type": "unknown_type_xyz",
            "data": "test"
        })

        response = await tester.receive(timeout=2.0)
        if response and response.get("type") == "error":
            print_success("错误处理测试通过")
            return True
        else:
            print_error("错误处理测试失败")
            return False
    finally:
        await tester.close()


async def test_multiple_clients():
    """测试8: 多客户端连接"""
    print("\n" + "="*50)
    print("测试8: 多客户端连接")
    print("="*50)

    clients = []
    try:
        # 创建3个客户端
        for i in range(3):
            tester = WebSocketTester(f"客户端{i+1}")
            success = await tester.connect(WS_URL, token=TEST_TOKEN)
            if not success:
                print_error(f"客户端{i+1}连接失败")
                return False
            clients.append(tester)

        # 验证每个客户端都有唯一的connection_id
        connection_ids = [c.connection_id for c in clients]
        if len(set(connection_ids)) == 3:
            print_success("多客户端连接测试通过")
            return True
        else:
            print_error("多客户端connection_id不唯一")
            return False
    finally:
        for client in clients:
            await client.close()


async def test_notification_endpoint():
    """测试9: 通知专用端点"""
    print("\n" + "="*50)
    print("测试9: 通知专用端点")
    print("="*50)

    tester = WebSocketTester("通知端点客户端")
    try:
        success = await tester.connect(WS_NOTIFICATIONS_URL, token=TEST_TOKEN)
        if success:
            print_success("通知端点测试通过")
            return True
        else:
            print_error("通知端点测试失败")
            return False
    finally:
        await tester.close()


async def test_continuous_heartbeat():
    """测试10: 持续心跳"""
    print("\n" + "="*50)
    print("测试10: 持续心跳 (5秒)")
    print("="*50)

    tester = WebSocketTester("持续心跳客户端")
    try:
        await tester.connect(WS_URL, token=TEST_TOKEN)

        success_count = 0
        for i in range(5):
            await tester.send({
                "type": "ping",
                "timestamp": datetime.now().isoformat(),
                "seq": i
            })

            response = await tester.receive(timeout=2.0)
            if response and response.get("type") == "pong":
                success_count += 1
                print_success(f"心跳 {i+1}/5 成功")
            else:
                print_error(f"心跳 {i+1}/5 失败")

            await asyncio.sleep(1)

        if success_count >= 4:
            print_success("持续心跳测试通过")
            return True
        else:
            print_error("持续心跳测试失败")
            return False
    finally:
        await tester.close()


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*50)
    print("WebSocket端到端测试")
    print("="*50)
    print(f"服务器地址: {WS_URL}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    results = []

    # 运行所有测试
    tests = [
        ("匿名连接", test_anonymous_connection),
        ("认证连接", test_authenticated_connection),
        ("心跳检测", test_heartbeat),
        ("订阅/取消订阅", test_subscription),
        ("同步请求", test_sync_request),
        ("进度更新", test_progress_update),
        ("未知消息类型", test_unknown_message),
        ("多客户端连接", test_multiple_clients),
        ("通知专用端点", test_notification_endpoint),
        ("持续心跳", test_continuous_heartbeat),
    ]

    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"测试异常: {e}")
            results.append((name, False))

    # 打印测试结果汇总
    print("\n" + "="*50)
    print("测试结果汇总")
    print("="*50)

    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed

    for name, result in results:
        status = f"{Colors.GREEN}通过{Colors.RESET}" if result else f"{Colors.RED}失败{Colors.RESET}"
        print(f"  {name}: {status}")

    print("="*50)
    print(f"总计: {len(results)} | 通过: {Colors.GREEN}{passed}{Colors.RESET} | 失败: {Colors.RED}{failed}{Colors.RESET}")
    print("="*50)

    return failed == 0


def main():
    """主函数"""
    print("WebSocket端到端测试脚本")
    print("======================")
    print()
    print("请确保FastAPI服务器已启动:")
    print(f"  python -m uvicorn app:app --host 0.0.0.0 --port 8080")
    print()

    # 检查是否跳过确认
    if "--yes" not in sys.argv:
        response = input("服务器是否已启动? (y/n): ")
        if response.lower() != 'y':
            print("请先启动服务器再运行测试")
            return

    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print_error(f"测试运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
