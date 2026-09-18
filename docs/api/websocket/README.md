# Perseus WebSocket API

> **基础路径**: `/ws`
> **协议**: WebSocket (ws://)
> **数据格式**: JSON
> **认证**: 通过 URL query 参数 `token` 传递 JWT

---

## 目录

1. [连接方式](#1-连接方式)
2. [通用端点](#2-通用端点-ws)
3. [实时日志](#3-实时日志-wslogs)
4. [用户通知](#4-用户通知-wsnotifications)
5. [仓库实时事件](#5-仓库实时事件-wsrepositoryid)
6. [消息协议](#6-消息协议)
7. [协作编辑](#7-协作编辑-wscollab-f-204)

---

## 1. 连接方式

### 连接 URL 格式

```
ws://host:port/ws?token=your_jwt_token
ws://host:port/ws/logs?token=your_jwt_token
ws://host:port/ws/notifications?token=your_jwt_token
ws://host:port/ws/repository/42?token=your_jwt_token
```

### 认证模式

| 端点 | 认证要求 | 匿名支持 |
|------|----------|----------|
| `/ws/` | 可选 | ✅ 匿名连接（功能受限）|
| `/ws/logs` | 可选 | ✅ 匿名连接（只能接收公开日志）|
| `/ws/notifications` | 必需 | ❌ 必须提供有效 Token |
| `/ws/repository/{id}` | 可选 | ✅ 公开仓库可匿名 |

### 连接生命周期

```
客户端 → 服务端: WebSocket 握手 (含 token)
服务端 → 客户端: {"type": "connected", "connection_id": "...", "authenticated": true/false}
客户端 → 服务端: {"type": "ping"}
服务端 → 客户端: {"type": "pong"}
客户端 → 服务端: {"type": "subscribe", "channel": "..."}
服务端 → 客户端: {"type": "notification", ...}
...双向通信...
客户端 → 服务端: WebSocket 关闭帧
服务端: 清理连接资源
```

---

## 2. 通用端点 `/ws/`

通用 WebSocket 端点，支持消息订阅、同步、进度通知。

### 连接响应

认证成功：
```json
{
  "type": "connected",
  "connection_id": "a1b2c3d4",
  "authenticated": true,
  "user": {
    "id": 1,
    "username": "admin",
    "is_admin": true
  },
  "message": "连接成功，已认证"
}
```

匿名连接：
```json
{
  "type": "connected",
  "connection_id": "a1b2c3d4",
  "authenticated": false,
  "message": "连接成功，匿名模式（部分功能受限）"
}
```

### 支持的消息类型

| 类型 | 方向 | 说明 |
|------|------|------|
| `ping` / `pong` | 双向 | 心跳检测 |
| `subscribe` | C→S | 订阅频道 |
| `unsubscribe` | C→S | 取消订阅 |
| `sync_request` | C→S | 请求同步操作 |
| `sync_status` | S→C | 同步状态推送 |
| `progress_update` | C→S | 进度更新消息 |
| `broadcast` | C→S | 广播消息（管理员）|
| `notification` | S→C | 通知推送 |
| `error` | S→C | 错误消息 |

### 订阅/取消订阅

```json
// 订阅仓库
{
  "type": "subscribe",
  "channel": "repository",
  "repository_id": 42
}

// 取消订阅
{
  "type": "unsubscribe",
  "channel": "repository",
  "repository_id": 42
}
```

### 心跳

```json
// 客户端发送
{
  "type": "ping",
  "timestamp": "2026-06-10T12:00:00.000Z"
}

// 服务端响应
{
  "type": "pong",
  "timestamp": "2026-06-10T12:00:00.000Z",
  "server_time": "2026-06-10T12:00:00.500Z"
}
```

---

## 3. 实时日志 `/ws/logs`

实时日志推送端点，替代传统的 HTTP 轮询日志接口。

### 连接响应

```json
{
  "type": "connected",
  "connection_id": "a1b2c3d4",
  "authenticated": true,
  "channel": "logs",
  "message": "日志通道已连接"
}
```

### 客户端 → 服务端

#### 订阅日志

```json
{
  "type": "subscribe_logs",
  "filters": {
    "levels": ["INFO", "WARNING", "ERROR"],
    "loggers": ["app", "git"],
    "keywords": ["error", "timeout"]
  },
  "history_count": 50
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| filters.levels | string[] | ❌ | 日志级别筛选（默认全部）|
| filters.loggers | string[] | ❌ | 日志器名称筛选 |
| filters.keywords | string[] | ❌ | 关键词筛选 |
| history_count | int | ❌ | 发送历史日志条数（0=不发送）|

#### 取消订阅日志

```json
{
  "type": "unsubscribe_logs"
}
```

#### 获取日志统计

```json
{
  "type": "get_log_stats"
}
```

### 服务端 → 客户端

#### 日志条目

```json
{
  "type": "log",
  "timestamp": "2026-06-10 10:30:45",
  "level": "ERROR",
  "logger": "app.git",
  "message": "Git operation failed: remote rejected"
}
```

#### 日志统计

```json
{
  "type": "log_stats",
  "stats": {
    "total": 1024,
    "by_level": {
      "ERROR": 12,
      "WARNING": 45,
      "INFO": 967
    },
    "period_seconds": 300
  }
}
```

---

## 4. 用户通知 `/ws/notifications`

通知专用端点，**必须认证**。连接后自动订阅用户通知频道。

### 连接响应

```json
{
  "type": "connected",
  "connection_id": "a1b2c3d4",
  "channel": "user_notifications",
  "message": "通知通道已连接"
}
```

### 消息协议

此端点仅用于接收通知，客户端只需发送心跳：

```json
// 客户端心跳
{"type": "ping", "timestamp": "2026-06-10T12:00:00.000Z"}

// 服务端响应
{"type": "pong", "timestamp": "2026-06-10T12:00:00.000Z", "server_time": "..."}
```

### 通知推送（✅ F-205 已实现，2026-09-14 两端接入）

服务端在 `notification_service.create_notification` 落库后主动推送（`notify_user`，
经 `manager.send_to_user` 投递到该用户全部连接，离线用户自然跳过）：

```json
{
  "type": "user_notification",
  "notification_type": "mention",
  "data": {
    "id": "0193a1b2-...",
    "type": "mention",
    "title": "你在 Issue #42 中被提到了",
    "message": "admin 在 Bug: login fails 中提到了你",
    "repository_id": "0193a1b2-...",
    "target_type": "issue",
    "target_id": "0193a1b2-...",
    "is_read": false,
    "created_at": "2026-09-14T10:30:00Z",
    "read_at": null
  },
  "unread_count": 3,
  "timestamp": "2026-09-14T10:30:00.123456"
}
```

字段说明：
- `data`：完整通知对象（与 `GET /api/v1/notifications` 列表项同构，可直接插入前端列表）
- `unread_count`：推送时刻该用户的未读总数（随消息下发，客户端免回查）
- 客户端仅需心跳保活（建议 30s 间隔）；断线期间产生的通知由客户端重连后经 REST 对账

> **web 接入**: `client/web/src/api/notificationSocket.ts`（AppLayout 挂载，登录态常驻）
> **desktop 接入**: `client/desktop/frontend/src/api/notificationSocket.ts`（PortalShell 挂载，经本地网关 WS 透传，切服自动换通道）

---

## 5. 仓库实时事件 `/ws/repository/{id}`

仓库专用端点，连接后自动订阅指定仓库的消息。

### 连接响应

```json
{
  "type": "connected",
  "connection_id": "a1b2c3d4",
  "repository_id": 42,
  "authenticated": true,
  "message": "已连接到仓库 42"
}
```

### 仓库事件（未来实现）

```json
{
  "type": "repository_event",
  "repository_id": 42,
  "event": "push",
  "data": {
    "ref": "refs/heads/main",
    "commits": [
      {
        "hash": "abc123",
        "message": "Fix login bug",
        "author": "admin"
      }
    ]
  }
}
```

支持的事件类型：

| 事件 | 说明 |
|------|------|
| `push` | 代码推送 |
| `pull_request` | PR 变更 |
| `issues` | Issue 变更 |
| `release` | Release 发布 |
| `member` | 成员变更 |

---

## 6. 消息协议

### 客户端 → 服务端

```json
{
  "type": "<message_type>",
  "...": "其他字段（按消息类型定义）"
}
```

### 服务端 → 客户端

```json
{
  "type": "<message_type>",
  "...": "其他字段（按消息类型定义）"
}
```

### 错误

```json
{
  "type": "error",
  "error": "消息处理失败: Invalid message type"
}
```

### WebSocket 关闭码

| 关闭码 | 含义 |
|--------|------|
| 1000 | 正常关闭 |
| 1008 | 认证失败 / Token 无效 |

---

## 7. 协作编辑 `/ws/collab`（F-204，Yjs 底座）

> **架构**: Hocuspocus 哑管道网关（`collab-gateway/`，独立容器）+ app 内部回调端点
> **同步协议**: y-websocket（CRDT，`Y.Doc` 文档模型）；光标/在线状态走 Awareness
> **前端集成**: `client/web/src/components/editor/collabController.ts`（CM6 `y-codemirror.next`）
> **desktop 接入**: `y-monaco`（D1 决策，待排期）

文档会话标识 `docKey = {repository_id}:{branch}:{path}`（经 provider 协议消息传输，
不依赖 URL 路径）。`Y.Doc` 中唯一共享文本类型为 `getText("content")`，
客户端必须以同名 ytext 绑定编辑器扩展。

### 职责边界（git-cgi 同构的哑管道模式）

| 层 | 职责 | 实现 |
|----|------|------|
| collab-gateway 容器 | CRDT 同步、Awareness（光标/参与）、只读强制、stateless 转发 | `@hocuspocus/server`，零业务代码 |
| app（FastAPI） | 用户鉴权、仓库权限、Git 文档加载与提交 | `controller/collab_internal_controller.py` |

### app 内部回调端点（服务间调用，共享密钥门禁）

请求头 `X-Collab-Internal-Secret: $PERSEUS_COLLAB_INTERNAL_SECRET`（未配置时端点整体 503；
compose 由 `scripts/generate_env.py` 生成并注入 app 与 collab 两容器）：

| 端点 | 网关钩子 | 说明 |
|------|---------|------|
| `POST /api/v1/collab/auth` | `onAuthenticate` | `{token, docKey}` → 校验 JWT + 仓库读写角色 → `{user_id, username, can_write}`；401/403/404 原因经 `writePermissionDenied` 送达客户端 |
| `GET /api/v1/collab/doc` | `onLoadDocument` | Git 读取文件内容作为文档种子；二进制 415 / 不存在 404 |
| `POST /api/v1/collab/save` | `onStateless("collab-save")` | `{token, docKey, content, message}` → 实时校验写权限（不缓存）→ 以提交者身份 `commit_file` → `{commit_id, saved_by, ...}` |

### stateless 消息（显式保存语义，与旧 F-204 一致）

| 消息 | 方向 | 说明 |
|------|------|------|
| `collab-save` | C→S | `{message}` → 网关回调 app 提交 Git（需写权限） |
| `collab-saved` | S→C 广播 | `{docKey, commit_id, saved_by, message, branch, path}` 全员广播（含提交者），驱动"Git 已提交"徽标 |
| `collab-save-error` | S→C（点对点） | `{error}` 保存失败原因 |

- `onStoreDocument`（debounce/断开自动触发）：**Git 提交仅由显式 `collab-save` 触发**，防止高频自动 commit。
  配置 `REDIS_URL` 时，另将 Y.Doc 全量状态快照写入 Redis（会话持久化，非 Git commit）。
- 自动保存到 Git（草稿分支）仍是待办，见 `docs/collab-f204-vs-cwm.md` 3.2 长期方案。

### 跟随模式（Follow me，2026-09-17 后端就绪）

> 后端实现：`collab-gateway/server.mjs`（`beforeHandleAwareness` 策略 + `onStateless` spotlight）；
> 测试：`collab-gateway/tests/gatewayFollow.test.mjs`（7 例）。
> 前端：web ✅ 2026-09-17（`collabController.ts` + `routes/editor/index.tsx`）；desktop ✅ 2026-09-17（`collabSocket.ts` + `CollabMonaco.tsx`）。

跟随状态完全落在 **Awareness**（感知层）：跟随关系由客户端从感知状态派生，网关只做盖章/校验，
不保存业务状态（awareness 经 `extension-redis` 跨副本同步，多副本天然一致）。

**Awareness 扩展字段**

| 字段 | 写入方 | 说明 |
|------|--------|------|
| `user` | 客户端 → 网关盖章 | `{name, color, user_id}`；`user_id`/`name` 由网关以已认证身份覆盖（防冒名），`color` 等展示字段保留 |
| `cursor` | y-codemirror / y-monaco | 光标/选区（既有，binding 管理） |
| `viewport` | 客户端 | `{anchor: number}` 视口顶部位置（≥0 整数，非法被剔除） |
| `follow` | 客户端 | `{target: clientID \| null}` 被跟随者（非整数被剔除） |

- 网关 `beforeHandleAwareness` 对单条 awareness 强制 `PERSEUS_COLLAB_MAX_AWARENESS_BYTES`（默认 8192）：
  超限先剔除 `viewport`/`follow`，再剔除白名单（`user`/`cursor`）外字段；仍超限则收敛为最小身份。
- 只读连接不受影响：只读仅拒绝文档 update，awareness 照常广播（只读者可显示光标、可跟随）。
- 客户端建议仅在检测到有 peer 的 `follow.target === 自身 clientID` 时才广播 `viewport`（节流 ~120ms）。

**stateless 消息（"跟我来" / Spotlight）**

| 消息 | 方向 | 载荷 | 说明 |
|------|------|------|------|
| `collab-spotlight` | C→S | `{on: boolean}` | 仅写权限（`can_write`）者可发起 |
| `collab-spotlight` | S→C 广播 | `{docKey, from:{user_id, username}, on}` | 全员广播（含发起者）；接收端据 `from.user_id` 在 awareness 中定位发起者 clientID，并 `setLocalStateField("follow", {target})` |
| `collab-spotlight-error` | S→C（点对点） | `{error}` | 无写权限时返回 |
| `collab-spotlight` | S→C 广播 | `{on:false}` | 发起者断开时网关自动广播（`onDisconnect`），对端停止跟随 |

### 权限与只读

- 连接时校验读权限（owner/admin/developer/viewer）与写权限（owner/admin/developer）
- 只读连接由 Hocuspocus 服务端强制（`connectionConfig.readOnly`）：
  其 update 被拒绝并 nak，无需客户端配合；本地 awareness 光标仍正常广播
- 保存前在 app 侧实时复核写权限（token 随连接上下文携带）

### 断线与重连（CRDT 优势）

- 断线期间本地编辑保留在客户端内存文档中，重连后由 provider 自动同步收敛
  （解决旧 F-204 "重连整篇覆盖丢输入" 问题，即 3.6 方案 B）
- 服务端 `Y.Doc` 在最后一人离开后保留 `PERSEUS_COLLAB_SESSION_TTL_MS`（默认 10 分钟，`collab-gateway/sessionTtl.mjs`），
  TTL 到期卸载；窗口内重 join 复用内存现场（无需重新播种）
- 多副本：配置 `REDIS_URL` 后，`@hocuspocus/extension-redis` 经 Redis pub/sub 跨副本同步，
  `@hocuspocus/extension-database` 将快照持久化至 Redis，支撑副本重启/故障后恢复未提交编辑
  （`collab-gateway/redisPersistence.mjs`，多副本冷启动播种经 Redis 锁串行化）

### 部署与验证

- 容器: `docker/collab/Dockerfile`（node:22-alpine），prod/dev compose `collab` 服务，
  nginx `/ws/collab` 分流至网关（优先于 `/ws` 通配）
- 测试: `collab-gateway/tests/gateway.test.mjs`（vitest，双客户端真实同步）、
  `collab-gateway/tests/gatewayFollow.test.mjs`（跟随模式：盖章/字段校验/spotlight 权限）、
  `tests/test_collab_internal_api.py`（app 端点契约）、
  `scripts` 侧 E2E 冒烟（注册→建仓→双端同步→保存→Git 落盘回读）

---

## 附录：连接示例

### JavaScript

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=' + token);

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log('Received:', msg);
};

// 发送心跳
setInterval(() => {
  ws.send(JSON.stringify({type: 'ping'}));
}, 30000);
```

### Python (websockets)

```python
import asyncio
import websockets
import json

async def connect():
    async with websockets.connect(f"ws://localhost:8000/ws?token={token}") as ws:
        response = json.loads(await ws.recv())
        print(f"Connected: {response}")

        # 订阅日志
        await ws.send(json.dumps({
            "type": "subscribe_logs",
            "filters": {"levels": ["ERROR"]},
            "history_count": 10
        }))

        # 接收消息
        async for message in ws:
            data = json.loads(message)
            print(f"Received: {data}")

asyncio.run(connect())
```
