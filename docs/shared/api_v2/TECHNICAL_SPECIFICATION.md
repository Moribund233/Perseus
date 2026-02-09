# LanGit API v2 技术细节文档

> 本文档基于现有项目结构，提供 API v2 各阶段功能的技术实现细节
> 
> 最后更新：2026-02-10

---

## 目录

1. [项目技术栈概览](#1-项目技术栈概览)
2. [现有基础设施分析](#2-现有基础设施分析)
3. [Phase 1: WebSocket 基础设施完善](#3-phase-1-websocket-基础设施完善)
4. [Phase 2: 实时消息通知服务](#4-phase-2-实时消息通知服务)
5. [Phase 3: Webhook 系统](#5-phase-3-webhook-系统)
6. [Phase 4: 简易组内聊天室](#6-phase-4-简易组内聊天室)
7. [数据模型设计](#7-数据模型设计)
8. [目录结构规划](#8-目录结构规划)
9. [测试策略](#9-测试策略)

---

## 1. 项目技术栈概览

### 1.1 后端技术栈

| 组件 | 版本 | 用途 |
|-----|------|------|
| Python | 3.12 | 运行时 |
| FastAPI | ^0.115.4 | Web 框架 |
| SQLAlchemy | ^2.0.34 | ORM |
| pygit2 | ^1.19.1 | Git 操作 |
| uvicorn | ^0.32.0 | ASGI 服务器 |
| python-jose | ^3.3.0 | JWT 认证 |
| passlib | ^1.7.4 | 密码哈希 |

### 1.2 前端技术栈

| 组件 | 版本 | 用途 |
|-----|------|------|
| Vue | 3.x | 框架 |
| TypeScript | 5.x | 语言 |
| Vite | 6.x | 构建工具 |
| Pinia | - | 状态管理 |

### 1.3 现有 WebSocket 架构

```
api/websocket/
├── __init__.py          # 路由导出
├── auth.py              # WebSocket 认证
├── manager.py           # 连接管理器（单例）
├── router.py            # WebSocket 端点定义
└── handlers/
    ├── __init__.py      # 处理器注册
    ├── notification.py  # 通知处理器
    ├── progress.py      # 进度处理器
    └── sync.py          # 同步处理器
```

---

## 2. 现有基础设施分析

### 2.1 ConnectionManager 能力

```python
# 核心功能
- 连接注册/注销
- 用户索引 (user_id -> connection_ids)
- 仓库索引 (repository_id -> connection_ids)
- 消息广播（全部/按用户/按仓库）
- 心跳检测
- 消息处理器注册
```

### 2.2 认证系统

```python
# 已支持
- JWT Token 验证（通过 URL query 参数）
- 可选认证（authenticate_websocket_optional）
- 强制认证（authenticate_websocket）
- 用户权限信息传递（is_admin）
```

### 2.3 前端 WebSocket SDK

```typescript
// 已支持功能
- 自动重连（指数退避）
- 心跳保活
- 消息处理器注册
- 连接状态管理
- TypeScript 类型支持
```

---

## 3. Phase 1: WebSocket 基础设施完善

### 3.1 连接管理优化

#### 3.1.1 心跳检测增强

**现有实现**: 基础心跳（ping/pong）

**需要增强**:
```python
# api/websocket/heartbeat.py
class HeartbeatManager:
    """
    心跳管理器
    
    功能：
    - 服务端主动发送 ping
    - 客户端 pong 响应检测
    - 超时自动断开
    - 多设备心跳同步
    """
    
    PING_INTERVAL = 30  # 秒
    PONG_TIMEOUT = 10   # 秒
    
    async def start_monitoring(self, connection: Connection):
        """启动心跳监控"""
        pass
    
    async def handle_pong(self, connection: Connection, data: dict):
        """处理 pong 响应"""
        pass
```

#### 3.1.2 断线重连支持

**服务端需要增加**:
```python
# 在 Connection 类中增加
class Connection:
    def __init__(self, ...):
        # 新增字段
        self.session_id: Optional[str] = None  # 用于断线重连识别
        self.device_id: Optional[str] = None   # 设备标识
        self.last_sequence: int = 0            # 最后消息序号
```

#### 3.1.3 多设备同步

```python
# api/websocket/device_sync.py
class DeviceSyncManager:
    """
    多设备同步管理器
    
    功能：
    - 同一用户多设备连接管理
    - 已读状态同步
    - 订阅状态同步
    """
    
    async def sync_subscription(self, user_id: int, device_id: str):
        """同步订阅状态到新设备"""
        pass
```

### 3.2 身份验证增强

#### 3.2.1 Token 刷新机制

```python
# api/websocket/auth.py 增强
async def refresh_websocket_token(
    connection: Connection, 
    refresh_token: str
) -> Optional[Dict[str, Any]]:
    """
    刷新 WebSocket 连接的 Token
    
    Args:
        connection: 当前连接
        refresh_token: 刷新令牌
        
    Returns:
        新的 token 信息
    """
    pass
```

#### 3.2.2 权限校验中间件

```python
# middleware/websocket_permission.py
class WebSocketPermissionMiddleware:
    """
    WebSocket 权限校验中间件
    
    功能：
    - 检查用户是否有权订阅特定仓库
    - 检查用户是否有权发送消息到聊天室
    """
    pass
```

### 3.3 消息队列（离线消息）

#### 3.3.1 Redis 集成

**依赖**: 需要新增 `redis` 依赖到 `pyproject.toml`

```python
# utils/redis_client.py
import redis.asyncio as redis
from config import get_config

class RedisClient:
    """Redis 客户端单例"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def init(self):
        config = get_config()
        self.client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            decode_responses=True
        )
```

#### 3.3.2 离线消息存储

```python
# services/offline_message_service.py
class OfflineMessageService:
    """
    离线消息服务
    
    功能：
    - 存储用户离线期间的消息
    - 用户上线后推送离线消息
    - 消息过期清理
    """
    
    MESSAGE_TTL = 7 * 24 * 3600  # 7天过期
    
    async def store_offline_message(
        self, 
        user_id: int, 
        message: dict
    ):
        """存储离线消息到 Redis"""
        key = f"offline:messages:{user_id}"
        await redis_client.lpush(key, json.dumps(message))
        await redis_client.expire(key, self.MESSAGE_TTL)
    
    async def get_offline_messages(self, user_id: int) -> List[dict]:
        """获取并清空用户的离线消息"""
        key = f"offline:messages:{user_id}"
        messages = await redis_client.lrange(key, 0, -1)
        await redis_client.delete(key)
        return [json.loads(m) for m in messages]
```

---

## 4. Phase 2: 实时消息通知服务

### 4.1 事件订阅系统

#### 4.1.1 数据模型

```python
# models/notification_subscription.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from models.base import BaseModel

class NotificationSubscription(BaseModel):
    """
    通知订阅模型
    
    用户可订阅特定仓库的特定事件类型
    """
    __tablename__ = "notification_subscriptions"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True, index=True)
    # repository_id 为 None 表示订阅所有仓库
    
    event_types = Column(JSON, default=list)  # ["push", "pull_request.opened", ...]
    channels = Column(JSON, default=lambda: ["websocket"])  # ["websocket", "email", "desktop"]
    
    is_active = Column(Boolean, default=True)
```

#### 4.1.2 订阅管理 API

```python
# controller/notification_controller.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v2/notifications", tags=["notifications"])

@router.get("/subscriptions")
async def get_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的所有订阅"""
    pass

@router.post("/subscriptions")
async def create_subscription(
    subscription: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新的订阅"""
    pass

@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消订阅"""
    pass
```

### 4.2 推送通知实现

#### 4.2.1 事件发布器

```python
# services/event_publisher.py
class EventPublisher:
    """
    事件发布器
    
    功能：
    - 接收业务事件（push、PR、Issue 等）
    - 查询订阅者
    - 分发到不同渠道
    """
    
    async def publish(self, event_type: str, repository_id: int, payload: dict):
        """
        发布事件
        
        Args:
            event_type: 事件类型（push, pull_request.opened 等）
            repository_id: 仓库ID
            payload: 事件数据
        """
        # 1. 查询订阅者
        subscribers = await self._get_subscribers(event_type, repository_id)
        
        # 2. 分发到不同渠道
        for subscriber in subscribers:
            for channel in subscriber.channels:
                if channel == "websocket":
                    await self._send_websocket(subscriber.user_id, event_type, payload)
                elif channel == "email":
                    await self._send_email(subscriber.user_id, event_type, payload)
```

#### 4.2.2 事件监听装饰器

```python
# utils/event_listener.py
def on_event(event_type: str):
    """
    事件监听装饰器
    
    用法：
        @on_event("push")
        async def handle_push_event(payload):
            pass
    """
    def decorator(func):
        EventPublisher.register_handler(event_type, func)
        return func
    return decorator
```

### 4.3 通知中心

#### 4.3.1 通知历史模型

```python
# models/notification.py
class Notification(BaseModel):
    """
    通知记录模型
    
    存储所有发送的通知，用于历史查询
    """
    __tablename__ = "notifications"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    content = Column(Text)
    link = Column(String(500))
    
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # 通知渠道和状态
    channels = Column(JSON)  # {"websocket": "delivered", "email": "failed"}
```

#### 4.3.2 通知查询 API

```python
# controller/notification_controller.py 补充

@router.get("/history")
async def get_notification_history(
    is_read: Optional[bool] = None,
    event_type: Optional[str] = None,
    repository_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取通知历史
    
    支持筛选：
    - is_read: 是否已读
    - event_type: 事件类型
    - repository_id: 仓库ID
    """
    pass

@router.post("/history/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """标记通知为已读"""
    pass

@router.post("/history/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """标记所有通知为已读"""
    pass
```

---

## 5. Phase 3: Webhook 系统

### 5.1 数据模型

```python
# models/webhook.py
class Webhook(BaseModel):
    """
    Webhook 配置模型
    """
    __tablename__ = "webhooks"
    
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    
    url = Column(String(500), nullable=False)  # 推送目标 URL
    secret = Column(String(255), nullable=False)  # 签名密钥
    
    events = Column(JSON, default=list)  # ["push", "pull_request.opened", ...]
    active = Column(Boolean, default=True)
    
    # 重试配置
    max_retries = Column(Integer, default=3)
    retry_interval = Column(Integer, default=60)  # 秒
    
    # 统计信息
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_delivered_at = Column(DateTime(timezone=True), nullable=True)


class WebhookDelivery(BaseModel):
    """
    Webhook 投递记录模型
    """
    __tablename__ = "webhook_deliveries"
    
    webhook_id = Column(Integer, ForeignKey("webhooks.id"), nullable=False, index=True)
    
    event = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    
    # 投递状态
    status = Column(String(20), default="pending")  # pending, success, failed
    
    # HTTP 响应
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_headers = Column(JSON, nullable=True)
    
    # 时间和性能
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
```

### 5.2 Webhook 管理 API

```python
# controller/webhook_controller.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v2/repositories/{repo_id}/webhooks", tags=["webhooks"])

@router.get("/")
async def list_webhooks(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取仓库的 Webhook 列表"""
    pass

@router.post("/")
async def create_webhook(
    repo_id: int,
    webhook: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建 Webhook"""
    pass

@router.get("/{hook_id}")
async def get_webhook(
    repo_id: int,
    hook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 Webhook 详情"""
    pass

@router.patch("/{hook_id}")
async def update_webhook(
    repo_id: int,
    hook_id: int,
    webhook: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新 Webhook"""
    pass

@router.delete("/{hook_id}")
async def delete_webhook(
    repo_id: int,
    hook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除 Webhook"""
    pass

@router.post("/{hook_id}/test")
async def test_webhook(
    repo_id: int,
    hook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """测试 Webhook"""
    pass
```

### 5.3 投递记录 API

```python
# controller/webhook_controller.py 补充

@router.get("/{hook_id}/deliveries")
async def list_deliveries(
    repo_id: int,
    hook_id: int,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 Webhook 投递记录"""
    pass

@router.get("/{hook_id}/deliveries/{delivery_id}")
async def get_delivery(
    repo_id: int,
    hook_id: int,
    delivery_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取投递详情"""
    pass

@router.post("/{hook_id}/deliveries/{delivery_id}/redeliver")
async def redeliver(
    repo_id: int,
    hook_id: int,
    delivery_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """重新投递"""
    pass
```

### 5.4 Webhook 执行服务

```python
# services/webhook_service.py
import hmac
import hashlib
import httpx
from datetime import datetime

class WebhookService:
    """
    Webhook 执行服务
    
    功能：
    - 签名生成
    - HTTP 推送
    - 重试机制
    - 投递记录
    """
    
    async def deliver(
        self, 
        webhook: Webhook, 
        event: str, 
        payload: dict
    ) -> WebhookDelivery:
        """
        执行 Webhook 投递
        
        Args:
            webhook: Webhook 配置
            event: 事件类型
            payload: 事件数据
            
        Returns:
            WebhookDelivery: 投递记录
        """
        # 1. 创建投递记录
        delivery = await self._create_delivery(webhook, event, payload)
        
        # 2. 准备请求
        headers = self._prepare_headers(webhook, event, delivery)
        body = self._prepare_payload(webhook, event, payload)
        
        # 3. 发送请求
        start_time = datetime.now()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    webhook.url,
                    headers=headers,
                    json=body
                )
                
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            # 4. 更新投递记录
            delivery.status = "success" if response.status_code < 400 else "failed"
            delivery.response_status = response.status_code
            delivery.response_body = response.text
            delivery.delivered_at = datetime.now()
            delivery.duration_ms = int(duration)
            
        except Exception as e:
            delivery.status = "failed"
            delivery.error_message = str(e)
            
        await self._save_delivery(delivery)
        return delivery
    
    def _prepare_headers(self, webhook: Webhook, event: str, delivery: WebhookDelivery) -> dict:
        """准备请求头"""
        payload_bytes = json.dumps({}).encode()  # 实际 payload
        signature = self._generate_signature(payload_bytes, webhook.secret)
        
        return {
            "Content-Type": "application/json",
            "X-LanGit-Event": event,
            "X-LanGit-Delivery": str(delivery.id),
            "X-LanGit-Signature": f"sha256={signature}",
            "User-Agent": "LanGit-WebHook/1.0"
        }
    
    def _generate_signature(self, payload: bytes, secret: str) -> str:
        """生成 HMAC-SHA256 签名"""
        return hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
```

### 5.5 签名验证工具

```python
# utils/webhook_signature.py
def verify_webhook_signature(
    payload: bytes, 
    secret: str, 
    signature: str
) -> bool:
    """
    验证 Webhook 签名
    
    Args:
        payload: 请求体字节
        secret: Webhook 密钥
        signature: 请求头中的签名（格式：sha256=xxx）
        
    Returns:
        bool: 验证是否通过
        
    Example:
        >>> verify_webhook_signature(
        ...     b'{"event": "push"}',
        ...     "my-secret",
        ...     "sha256=abc123..."
        ... )
        True
    """
    if not signature.startswith("sha256="):
        return False
    
    expected = 'sha256=' + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)
```

---

## 6. Phase 4: 简易组内聊天室

### 6.1 数据模型

```python
# models/chat_room.py
class ChatRoom(BaseModel):
    """
    聊天室模型
    
    支持两种类型：
    - repository: 仓库级别聊天室
    - organization: 组织级别聊天室
    - direct: 私聊
    """
    __tablename__ = "chat_rooms"
    
    name = Column(String(100), nullable=False)
    room_type = Column(String(20), default="repository")  # repository, organization, direct
    
    # 关联
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    
    # 创建者
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 设置
    is_public = Column(Boolean, default=True)  # 是否公开
    is_archived = Column(Boolean, default=False)
    
    # 成员数缓存
    member_count = Column(Integer, default=0)


class ChatRoomMember(BaseModel):
    """
    聊天室成员模型
    """
    __tablename__ = "chat_room_members"
    
    room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 角色
    role = Column(String(20), default="member")  # owner, admin, member
    
    # 状态
    is_muted = Column(Boolean, default=False)
    muted_until = Column(DateTime(timezone=True), nullable=True)
    
    # 最后阅读
    last_read_message_id = Column(Integer, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('room_id', 'user_id', name='uix_room_member'),
    )


class ChatMessage(BaseModel):
    """
    聊天消息模型
    """
    __tablename__ = "chat_messages"
    
    room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 消息内容
    content = Column(Text, nullable=False)
    content_type = Column(String(20), default="text")  # text, image, code, file
    
    # 回复
    reply_to = Column(Integer, ForeignKey("chat_messages.id"), nullable=True)
    
    # 编辑
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime(timezone=True), nullable=True)
    
    # 删除
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 元数据（图片URL、代码语言等）
    metadata = Column(JSON, default=dict)
```

### 6.2 聊天室 API

```python
# controller/chat_controller.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v2/chat", tags=["chat"])

# ========== 聊天室管理 ==========

@router.get("/rooms")
async def list_rooms(
    room_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户加入的聊天室列表"""
    pass

@router.post("/rooms")
async def create_room(
    room: RoomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建聊天室"""
    pass

@router.get("/rooms/{room_id}")
async def get_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取聊天室详情"""
    pass

@router.patch("/rooms/{room_id}")
async def update_room(
    room_id: int,
    room: RoomUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新聊天室"""
    pass

# ========== 成员管理 ==========

@router.get("/rooms/{room_id}/members")
async def list_members(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取聊天室成员列表"""
    pass

@router.post("/rooms/{room_id}/members")
async def add_member(
    room_id: int,
    member: MemberAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加成员"""
    pass

@router.delete("/rooms/{room_id}/members/{user_id}")
async def remove_member(
    room_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """移除成员"""
    pass

# ========== 消息管理 ==========

@router.get("/rooms/{room_id}/messages")
async def list_messages(
    room_id: int,
    before_id: Optional[int] = None,
    after_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取聊天室消息
    
    支持分页：
    - before_id: 获取此ID之前的消息（向上翻页）
    - after_id: 获取此ID之后的消息（向下翻页/新消息）
    """
    pass

@router.post("/rooms/{room_id}/messages")
async def send_message(
    room_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发送消息（REST API 方式）"""
    pass

@router.patch("/rooms/{room_id}/messages/{message_id}")
async def edit_message(
    room_id: int,
    message_id: int,
    message: MessageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """编辑消息"""
    pass

@router.delete("/rooms/{room_id}/messages/{message_id}")
async def delete_message(
    room_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除消息（软删除）"""
    pass
```

### 6.3 WebSocket 聊天处理器

```python
# api/websocket/handlers/chat.py
from api.websocket.manager import manager

async def handle_chat_join(connection: Connection, data: dict):
    """
    处理加入聊天室
    
    消息格式：
    {
        "type": "chat_join",
        "room_id": 123
    }
    """
    room_id = data.get("room_id")
    
    # 检查权限
    if not await check_room_permission(connection.user_id, room_id):
        await connection.send({
            "type": "error",
            "error": "无权访问该聊天室"
        })
        return
    
    # 加入房间（使用 ConnectionManager 的分组功能）
    manager.subscribe_repository(connection, room_id)  # 复用仓库订阅机制
    
    # 发送最近消息
    recent_messages = await get_recent_messages(room_id)
    await connection.send({
        "type": "chat_history",
        "room_id": room_id,
        "messages": recent_messages
    })
    
    # 广播用户加入
    await manager.broadcast_to_repository(room_id, {
        "type": "chat_user_joined",
        "room_id": room_id,
        "user": {
            "id": connection.user_id,
            "username": connection.username
        }
    })


async def handle_chat_message(connection: Connection, data: dict):
    """
    处理聊天消息
    
    消息格式：
    {
        "type": "chat_message",
        "room_id": 123,
        "content": "Hello",
        "content_type": "text",
        "reply_to": null
    }
    """
    room_id = data.get("room_id")
    
    # 保存消息到数据库
    message = await save_message(
        room_id=room_id,
        sender_id=connection.user_id,
        content=data.get("content"),
        content_type=data.get("content_type", "text"),
        reply_to=data.get("reply_to")
    )
    
    # 广播给房间所有成员
    await manager.broadcast_to_repository(room_id, {
        "type": "chat_message",
        "message": {
            "id": message.id,
            "room_id": room_id,
            "sender": {
                "id": connection.user_id,
                "username": connection.username
            },
            "content": message.content,
            "content_type": message.content_type,
            "reply_to": message.reply_to,
            "created_at": message.created_at.isoformat()
        }
    })


async def handle_chat_typing(connection: Connection, data: dict):
    """
    处理正在输入状态
    
    消息格式：
    {
        "type": "chat_typing",
        "room_id": 123,
        "is_typing": true
    }
    """
    room_id = data.get("room_id")
    
    # 广播输入状态（不发送给自己）
    await manager.broadcast_to_repository(room_id, {
        "type": "chat_typing",
        "room_id": room_id,
        "user": {
            "id": connection.user_id,
            "username": connection.username
        },
        "is_typing": data.get("is_typing", True)
    }, exclude_connection=connection)
```

### 6.4 聊天室 WebSocket 端点

```python
# api/websocket/router.py 补充

@router.websocket("/chat/{room_id}")
async def chat_websocket(
    websocket: WebSocket,
    room_id: int,
    token: str = Query(..., description="认证token（必需）")
):
    """
    聊天室专用 WebSocket 端点
    
    此端点自动加入指定聊天室，简化的聊天协议
    """
    connection = None
    
    try:
        # 必须认证
        user_info = await authenticate_websocket(websocket)
        
        # 检查聊天室权限
        if not await check_room_permission(user_info["user_id"], room_id):
            await websocket.close(code=1008, reason="无权访问该聊天室")
            return
        
        # 建立连接
        connection = await manager.connect(websocket)
        manager.bind_user(connection, user_info["user_id"], user_info["username"])
        
        # 加入聊天室
        manager.subscribe_repository(connection, room_id)
        
        # 发送欢迎消息
        await connection.send({
            "type": "chat_connected",
            "room_id": room_id,
            "user": {
                "id": user_info["user_id"],
                "username": user_info["username"]
            }
        })
        
        # 消息循环
        while connection.is_alive:
            data = await websocket.receive_json()
            
            # 处理聊天相关消息
            if data.get("type") == "chat_message":
                await handle_chat_message(connection, data)
            elif data.get("type") == "chat_typing":
                await handle_chat_typing(connection, data)
            elif data.get("type") == "ping":
                await connection.send({"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info(f"聊天室连接断开: room_id={room_id}")
    finally:
        if connection:
            # 广播离开消息
            await manager.broadcast_to_repository(room_id, {
                "type": "chat_user_left",
                "room_id": room_id,
                "user": {
                    "id": connection.user_id,
                    "username": connection.username
                }
            })
            manager.disconnect(connection)
```

---

## 7. 数据模型设计

### 7.1 新增模型汇总

```
models/
├── __init__.py
├── base.py              # 基础模型（已存在）
├── db.py                # 数据库会话（已存在）
├── user.py              # 用户模型（已存在）
├── repository.py        # 仓库模型（已存在）
├── ...                  # 其他现有模型
├── notification.py      # 【新增】通知记录
├── notification_subscription.py  # 【新增】通知订阅
├── webhook.py           # 【新增】Webhook 配置和投递记录
├── chat_room.py         # 【新增】聊天室、成员、消息
└── organization.py      # 【新增】组织（如需要）
```

### 7.2 数据库迁移

```bash
# 使用 Alembic 进行数据库迁移
# 1. 初始化 Alembic（如果还没有）
alembic init alembic

# 2. 创建迁移脚本
alembic revision --autogenerate -m "add api v2 models"

# 3. 执行迁移
alembic upgrade head
```

---

## 8. 目录结构规划

### 8.1 后端目录结构

```
LanGit/
├── api/
│   ├── api_v1.py              # API v1 路由（已存在）
│   ├── api_v2.py              # 【新增】API v2 路由
│   ├── dependencies.py        # 依赖注入（已存在）
│   ├── error.py               # 错误处理（已存在）
│   └── websocket/
│       ├── __init__.py
│       ├── auth.py            # 认证（已存在）
│       ├── manager.py         # 连接管理（已存在）
│       ├── router.py          # 路由（已存在，需扩展）
│       ├── heartbeat.py       # 【新增】心跳管理
│       └── handlers/
│           ├── __init__.py
│           ├── notification.py
│           ├── progress.py
│           ├── sync.py
│           ├── chat.py        # 【新增】聊天处理器
│           └── presence.py    # 【新增】在线状态处理器
│
├── controller/
│   ├── ...                    # 现有控制器
│   ├── notification_controller.py    # 【新增】
│   ├── webhook_controller.py         # 【新增】
│   └── chat_controller.py            # 【新增】
│
├── services/
│   ├── ...                    # 现有服务
│   ├── event_publisher.py     # 【新增】事件发布
│   ├── webhook_service.py     # 【新增】Webhook 执行
│   ├── offline_message_service.py  # 【新增】离线消息
│   └── chat_service.py        # 【新增】聊天服务
│
├── models/
│   ├── ...                    # 现有模型
│   ├── notification.py        # 【新增】
│   ├── notification_subscription.py  # 【新增】
│   ├── webhook.py             # 【新增】
│   └── chat_room.py           # 【新增】
│
├── utils/
│   ├── ...                    # 现有工具
│   ├── redis_client.py        # 【新增】Redis 客户端
│   └── webhook_signature.py   # 【新增】Webhook 签名
│
└── middleware/
    ├── ...                    # 现有中间件
    └── websocket_permission.py # 【新增】WebSocket 权限
```

### 8.2 前端目录结构

```
frontend/src/
├── stores/
│   ├── ...                    # 现有 store
│   ├── notifications.ts       # 【新增】通知 store
│   └── chat.ts                # 【新增】聊天 store
│
├── utils/
│   ├── ...                    # 现有工具
│   ├── websocket.ts           # 已存在，需扩展
│   ├── notification_api.ts    # 【新增】通知 API
│   ├── webhook_api.ts         # 【新增】Webhook API
│   └── chat_api.ts            # 【新增】聊天 API
│
└── views/
    ├── ...                    # 现有视图
    ├── notifications/         # 【新增】通知中心页面
    └── chat/                  # 【新增】聊天室页面
```

---

## 9. 测试策略

### 9.1 单元测试

```python
# tests/test_notification_service.py
class TestNotificationService:
    """测试通知服务"""
    
    async def test_publish_event(self):
        """测试事件发布"""
        pass
    
    async def test_offline_message_storage(self):
        """测试离线消息存储"""
        pass


# tests/test_webhook_service.py
class TestWebhookService:
    """测试 Webhook 服务"""
    
    async def test_webhook_delivery(self):
        """测试 Webhook 投递"""
        pass
    
    def test_signature_generation(self):
        """测试签名生成"""
        pass
    
    def test_signature_verification(self):
        """测试签名验证"""
        pass


# tests/test_chat_service.py
class TestChatService:
    """测试聊天服务"""
    
    async def test_send_message(self):
        """测试发送消息"""
        pass
    
    async def test_message_history(self):
        """测试消息历史"""
        pass
```

### 9.2 集成测试

```python
# tests/test_websocket_chat.py
class TestWebSocketChat:
    """测试 WebSocket 聊天功能"""
    
    async def test_join_room(self):
        """测试加入聊天室"""
        pass
    
    async def test_send_receive_message(self):
        """测试收发消息"""
        pass
    
    async def test_typing_indicator(self):
        """测试输入状态"""
        pass


# tests/test_webhook_integration.py
class TestWebhookIntegration:
    """测试 Webhook 集成"""
    
    async def test_push_event_webhook(self):
        """测试 Push 事件触发 Webhook"""
        pass
```

### 9.3 E2E 测试

```python
# tests/test_websocket_e2e.py 扩展
class TestWebSocketE2E:
    """WebSocket E2E 测试"""
    
    async def test_notification_flow(self):
        """
        测试完整通知流程：
        1. 用户 A 订阅仓库事件
        2. 用户 B 推送代码
        3. 用户 A 收到实时通知
        """
        pass
    
    async def test_chat_flow(self):
        """
        测试完整聊天流程：
        1. 用户 A 创建聊天室
        2. 用户 B 加入聊天室
        3. 用户 A 发送消息
        4. 用户 B 实时收到消息
        """
        pass
```

---

## 10. 配置更新

### 10.1 pyproject.toml 依赖

```toml
[tool.poetry.dependencies]
# 现有依赖...
redis = "^5.0.0"           # 【新增】Redis 客户端
alembic = "^1.12.0"        # 【新增】数据库迁移（如需要）
```

### 10.2 config.py 配置

```python
# config.py 新增
class RedisSettings(BaseSettings):
    """Redis 配置类"""
    host: str = Field(default="localhost", description="Redis 主机")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis 端口")
    db: int = Field(default=0, ge=0, description="Redis 数据库编号")
    password: Optional[str] = Field(default=None, description="Redis 密码")


class Config(BaseSettings):
    """配置主类"""
    # 现有配置...
    redis: RedisSettings = RedisSettings()  # 【新增】
```

---

## 11. 开发顺序建议

### 11.1 推荐开发顺序

1. **Phase 1 基础**（1-2 周）
   - Redis 集成
   - 离线消息服务
   - 心跳增强

2. **Phase 2 通知**（2-3 周）
   - 通知订阅模型和 API
   - 事件发布系统
   - 通知中心前端

3. **Phase 3 Webhook**（2 周）
   - Webhook 模型和 API
   - Webhook 执行服务
   - 签名验证

4. **Phase 4 聊天**（2-3 周）
   - 聊天室模型和 API
   - WebSocket 聊天处理器
   - 聊天前端界面

### 11.2 依赖关系

```
Phase 1 (基础)
    │
    ├──> Phase 2 (通知) ──> 需要 Redis、离线消息
    │
    ├──> Phase 3 (Webhook) ──> 相对独立
    │
    └──> Phase 4 (聊天) ──> 需要 WebSocket 基础
```

---

**文档结束**

本文档提供了 API v2 各阶段功能的详细技术实现方案，开发时可按此文档进行具体实现。
