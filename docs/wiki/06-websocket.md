# 06 · WebSocket 子系统

> 实时消息核心。管理所有 WS 连接、心跳、用户/仓库/房间三级路由、多 worker 广播。

---

## 目录

```
api/websocket/
├── __init__.py          # router —— 3 个 WS 端点
├── router.py            # /ws /ws/logs /ws/notifications
├── auth.py              # 从 URL query /ws?token=... 取 access_token 校验
├── manager.py           # Connection + ConnectionManager（核心）
└── handlers/
    ├── __init__.py
    ├── chat.py          # 聊天消息 handler
    ├── room.py          # 房间 handler（join/leave/mute）
    ├── notification.py  # 通知 handler
    ├── sync.py          # 状态同步 handler
    ├── progress.py      # 进度推送 handler
    └── log_handler.py   # 日志推送 handler
```

---

## 1. 三个 WS 端点

| 端点 | 用途 | 认证 |
|------|------|------|
| `/ws` | 主连接（用户绑定 + 仓库/房间订阅 + 多类型消息） | `?token=<access_token>` |
| `/ws/logs` | 管理员日志流（实时 audit.log 广播） | admin 用户 |
| `/ws/notifications` | 仅通知推送专用 | `?token=<access_token>` |

统一路由通过 `api/websocket/__init__.py` 的 `router` 导出，由 `routes_config` 注册。

---

## 2. 认证 `api/websocket/auth.py`

```python
async def authenticate_ws(websocket: WebSocket) -> User:
    # 从 URL query / headers 取 access_token
    # 调用 services.token_service.verify_token_active
    # 返回 User 或抛 401（关闭 code=1008）
```

---

## 3. Connection（单个连接包装）

```python
class Connection:
    websocket: WebSocket
    connection_id: str          # UUID
    user_id: Optional[UUID]     # 绑定的用户
    username: Optional[str]
    repository_ids: Set[UUID]   # 已订阅仓库
    rooms: Set[UUID]            # 已加入房间
    connected_at: datetime
    last_ping: datetime
    is_alive: bool
    metadata: Dict[str, Any]    # 扩展

    async def send(self, message: dict) -> bool
    def bind_user(self, user_id, username)
    def subscribe_repository(self, repo_id)
    def unsubscribe_repository(self, repo_id)
    def update_ping(self)
    def is_timeout(self, timeout_seconds=120) -> bool
    def to_dict(self) -> dict
```

所有 `send()` 内部统一 `json.dumps(message, default=str)` 兜底处理 UUID 等不可序列化类型。

---

## 4. ConnectionManager（连接管理器）

### 4.1 核心数据结构

```python
class ConnectionManager:
    _lock: asyncio.Lock           # 所有数据结构访问保护
    _connections: dict[str, Connection]      # connection_id → Connection
    _user_index: dict[UUID, set[str]]        # user_id → connection_id set
    _repo_index: dict[UUID, set[str]]        # repo_id → connection_id set
    _room_index: dict[UUID, set[str]]        # room_id → connection_id set
```

### 4.2 核心方法

| 方法 | 说明 |
|------|------|
| `async register(ws) -> Connection` | 接受连接，分配 connection_id |
| `async disconnect(conn)` | 注销连接，清理所有索引 |
| `async bind_user(conn, user_id, username)` | 绑定用户 |
| `async subscribe_repo(conn, repo_id)` | 订阅仓库 |
| `async subscribe_room(conn, room_id)` | 订阅房间 |
| `async send_to_user(user_id, message)` | 发给某个用户的所有连接 |
| `async send_to_repo(repo_id, message)` | 发给订阅某仓库的所有连接 |
| `async send_to_room(room_id, message)` | 发给某房间的所有连接 |
| `async broadcast(message)` | 全体广播 |
| `async heartbeat_checker()` | **后台协程**，每 30s 扫描超时连接（默认 120s 无心跳） |
| `async get_stats() -> dict` | 管理面板统计（连接数 / 用户数 / 仓库订阅数） |

### 4.3 消息格式

```jsonc
{
  "type": "chat",
  "event": "message",
  "data": { "room_id": "...", "content": "...", "author": {...} },
  "timestamp": "2026-09-21T...Z"
}
```

---

## 5. 消息路由（handlers）

### 5.1 分发逻辑

```
客户端 WebSocket 消息
        │
        ▼
api/websocket/router.py  receive loop
        │  按 message["type"] 分发
        ▼
handlers/<type>.py  handle(conn, message)
        │
        ├─ 更新索引（subscribe / unsubscribe）
        ├─ 调用 service（如保存聊天消息）
        └─ 触发广播
```

### 5.2 六个 handler

| 模块 | 监听 type | 主要 event | 说明 |
|------|----------|-----------|------|
| `chat.py` | `chat` | `message` / `typing` | 保存聊天消息 → 房间广播 |
| `room.py` | `room` | `join` / `leave` / `mute` | 更新 room_index |
| `notification.py` | `notification` | `subscribe` / `read` | 通知订阅 |
| `sync.py` | `sync` | `state` | 客户端状态同步请求 |
| `progress.py` | `progress` | `build` / `ci` | 构建进度推送 |
| `log_handler.py` | `log` | `subscribe` | 管理员日志流订阅 |

---

## 6. 实时广播总线（跨 worker）

### 6.1 `utils/realtime_bus.py`

```python
class RealtimeBus:
    # 绑定 ConnectionManager 并在 Redis PUBSUB 上转发
    async def bind(manager: ConnectionManager) -> None
    async def start() -> bool          # 启动，Redis 不可用返回 False（退化为进程内）
    async def stop() -> None
    async def publish(channel: str, message: dict) -> None
```

### 6.2 Redis PUBSUB 设计

```
worker-1 publish ─► Redis PUBSUB ─► worker-2 subscriber → ConnectionManager.send_to_user/repo/...
                                         │
                                         └─► worker-3 subscriber ...
```

- 通道前缀 = `{config.redis.namespace}:ws`（默认 `perseus:ws`）
- Redis 不可用时退化为进程内广播（单 worker 场景无影响）
- 连接失败有 `reconnect_cooldown`（默认 5s）避免每次重连

### 6.3 广播调用入口

Service 层触发广播时统一走：

```python
from utils.realtime_bus import bus

async def notify_pr_opened(pr):
    # ... 写通知 ...
    await bus.publish(f"repo:{pr.repository_id}", {
        "type": "event",
        "event": "pr_opened",
        "data": {...}
    })
```

`realtime_bus.start()` 在 lifespan startup 时调用，成功后所有 worker 的 manager 都会转发。

---

## 7. 在线状态 presence

```python
# services/realtime/presence_service.py
presence = PresenceService()  # 单例

presence.online_users: dict[UUID, set[worker_id]]
presence.online_in_repo: dict[UUID, set[user_id]]
```

- Redis 可用 → 多 worker 共享
- Redis 不可用 → 进程内
- lifespan startup 时绑定到 ConnectionManager（`manager.set_presence(presence)`）

---

## 8. Worker 注册表（Redis）

```python
# services/worker_registry.py
class WorkerRegistry:
    async def heartbeat(manager, bus) -> None   # 20s 周期写 Redis
    async def list_workers() -> list[dict]       # Admin 查看活跃 workers
```

Admin 控制台用它展示在线 worker 数、各 worker 连接数、版本等。

---

## 9. 安全要点

- WS 连接必须认证（`api.websocket.auth`），未认证 3s 内关闭
- `/ws/logs` / Admin 路由额外要求 `is_admin=True`
- 每个客户端独立锁 `_lock` 保护所有索引操作
- 心跳超时 120s 自动清理（`is_alive=False` + `disconnect`）
- 消息 JSON 统一 `default=str` 避免序列化异常

---

## 下一章

👉 [07 · 中间件与工具库（middleware + utils）](07-middleware-utils.md)
