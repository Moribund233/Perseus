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

### 通知示例（未来实现）

```json
{
  "type": "notification",
  "id": "notif_001",
  "kind": "issue_mentioned",
  "title": "你在 Issue #42 中被提到了",
  "body": "admin 在 Bug: login fails 中提到了你",
  "link": "/repositories/1/issues/42",
  "read": false,
  "created_at": "2026-06-10T10:30:00Z"
}
```

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

## 7. 协作编辑 `/ws/collab`（F-204）

> **认证**: 必需（URL query `token`）
> **消息上限**: 2MB（容纳批量粘贴产生的变更集）
> **实现**: `services/realtime/collab_service.py` + `api/websocket/handlers/collab.py`
> **前端集成**: `client/web/src/components/editor/collabController.ts`（CodeMirror 6 `@codemirror/collab`）

文档会话标识 `docKey = {repository_id}:{branch}:{path}`。
服务端为每个会话维护权威文本 + 版本号 + 变更日志（乐观并发控制）：
客户端 push 必须基于服务端当前版本，过期则拒绝并返回缺失变更，
客户端（collab 扩展）rebase 本地未确认变更后重发。

变更集（`changes`）为 CM6 `ChangeSet.toJSON()` 数组，一次 push 可携带多个顺序变更集。

### 权限模型

- `collab_join` 时一次性校验读权限（owner/admin/developer/viewer）与写权限
  （owner/admin/developer），写权限缓存在会话参与者上（`can_write`）
- `collab_push` / `collab_save` 直接使用缓存权限，不逐次查库；
  仓库角色变更在重新 join 后生效
- 消息上限 2MB（按 UTF-8 字节数，容纳批量粘贴产生的变更集）

### 断线与重连

- 连接断开时服务端将该连接移出所有会话（会话无人时销毁）
- 客户端重连成功后必须重新 `collab_join`（前端已实现：状态重置 + 自动重新加入）

### 消息协议

| 消息 | 方向 | 说明 |
|------|------|------|
| `collab_join` | C→S | 加入会话 `{repository_id, branch, path, clientID}`（join 需读权限） |
| `collab_init` | S→C | 会话快照 `{docKey, doc, version, participants}`（含权威文本） |
| `collab_push` | C→S | 推送变更 `{docKey, version, changes[], clientID}`（需写权限） |
| `collab_update` | S→C | 变更广播 `{docKey, changes[], clientID, version}`（全员，含发送者：自身更新由 clientID 识别并确认） |
| `collab_reject` | S→C | 版本过期 `{docKey, version, changes[], resync}`（changes 为缺失变更） |
| `collab_pull` | C→S | 增量拉取 `{docKey, version}` |
| `collab_resync` | S→C | 版本超出日志窗口，需重新 join |
| `collab_cursor` | C→S / S→C | 光标/选区 `{anchor, head}`（C→S 附带本地同步版本号） |
| `collab_save` | C→S | 协作保存 `{docKey, message}`（以服务端权威文本提交 Git commit，需写权限） |
| `collab_saved` / `collab_save_ack` | S→C | 保存结果广播 / 提交者回执 `{commit_id, saved_by, path, branch, message}` |
| `collab_leave` / `collab_peer_left` | C→S / S→C | 离开会话 / 成员离开广播 |

### 会话生命周期

- 首个协作者 `collab_join` 时从 Git 分支文件内容创建会话
- 最后一个协作者离开（或连接断开）时销毁会话（内存态，不持久化）
- 二进制文件不支持协作编辑

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
