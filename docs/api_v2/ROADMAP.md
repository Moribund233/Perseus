# LanGit 第二阶段开发规划路线图（API v2）

> 本文档记录 LanGit 项目第二阶段开发规划（代号 API v2），重点扩展 WebSocket 实时服务功能
> 
> 最后更新：2026-02-10

---

## 🎯 关于 "API v2" 的说明

**重要提示**：本文档中的 "API v2" 是开发规划的代号，用于区分不同阶段的开发目标，**不代表实际的路由版本**。

### 实际路由情况
- 应用使用统一的 `api_v1_router` 注册所有路由
- REST API 统一使用 `/api` 前缀
- WebSocket 统一使用 `/ws` 前缀
- 不严格区分 v1/v2 版本路径

### 本文档的用途
- 规划和记录第二阶段的功能开发（实时消息、聊天室、Webhook）
- 作为开发工作的路线图和参考文档
- 与 [API v1 开发规划](../api_v1/ROADMAP.md) 形成完整的项目开发历程记录

---

## 🎯 第二阶段开发目标

在第一阶段（API v1）基础上，通过 WebSocket 扩展实时通信功能，提供更丰富的协作体验。

### 核心方向

1. **实时消息通知服务** - 仓库事件实时推送
2. **简易组内聊天室** - 团队即时通讯
3. **Webhook 系统** - 与外部 CI/CD 工具集成
4. **在线协作功能** - 实时编辑、在线状态（可选）

---

## 📋 功能规划

### Phase 1: WebSocket 基础设施完善

**状态**: 🟡 规划中

| 功能 | 说明 | 预估工作量 |
|-----|------|-----------|
| 连接管理优化 | 心跳检测、断线重连、多设备同步 | 2-3 天 |
| 身份验证增强 | Token 刷新、权限校验、会话管理 | 2-3 天 |
| 消息队列 | 离线消息存储、消息可靠性保证 | 3-5 天 |

### Phase 2: 实时消息通知服务

**状态**: 🟡 规划中

| 功能 | 说明 | 预估工作量 |
|-----|------|-----------|
| 事件订阅系统 | 用户可订阅特定仓库/事件类型 | 3-5 天 |
| 推送通知 | Push 事件、PR 更新、Issue 变更实时推送 | 5-7 天 |
| 通知中心 | 历史通知查询、已读/未读管理 | 3-5 天 |
| 邮件/桌面通知 | 离线时通过其他渠道通知 | 5-7 天 |

**事件类型规划**:
- `push` - 代码推送
- `pull_request.opened/merged/closed` - PR 状态变更
- `issue.opened/closed/commented` - Issue 状态变更
- `repository.forked/starred` - 仓库社交事件
- `mention` - 用户被提及

### Phase 3: Webhook 系统

**状态**: 🟡 规划中

| 功能 | 说明 | 预估工作量 |
|-----|------|-----------|
| Webhook 配置 | 支持配置多个 Webhook URL | 2-3 天 |
| 事件推送 | Push、PR、Issue 等事件 HTTP 推送 | 3-5 天 |
| 签名验证 | HMAC-SHA256 签名验证 | 2-3 天 |
| 重试机制 | 失败重试、日志记录 | 2-3 天 |
| 事件过滤 | 按事件类型、仓库过滤 | 2-3 天 |

**支持的事件类型**:
- `push` - 代码推送
- `pull_request.opened/merged/closed` - PR 状态变更
- `issue.opened/closed/commented` - Issue 状态变更
- `repository.forked/starred` - 仓库社交事件
- `release.published` - 版本发布

**适用场景**:
- 与 Jenkins、GitLab CI 等 CI/CD 工具集成
- 自动化部署流水线
- 自定义工作流触发

### Phase 4: 简易组内聊天室

**状态**: 🟡 规划中

| 功能 | 说明 | 预估工作量 |
|-----|------|-----------|
| 基础聊天室 | 仓库/组织级别的聊天频道 | 5-7 天 |
| 消息功能 | 文本、表情、图片、代码片段 | 5-7 天 |
| 成员管理 | 在线状态、@提及、私聊 | 3-5 天 |
| 消息历史 | 聊天记录存储、搜索、导出 | 5-7 天 |

### Phase 5: 在线协作功能（可选）

**状态**: ⚪ 待定

| 功能 | 说明 | 预估工作量 |
|-----|------|-----------|
| 在线状态 | 显示谁在线、正在查看什么 | 3-5 天 |
| 实时协作 | 多人同时查看代码、光标同步 | 10-15 天 |
| 语音/视频 | 代码审查时的实时沟通 | 15-20 天 |

---

## 🔌 WebSocket 接口规划

### 版本说明

**重要**：本文档中的 "API v2" 是功能开发规划的代号，用于区分不同阶段的开发目标。实际应用路由不严格区分 v1/v2 版本：
- REST API 统一使用 `/api` 前缀
- WebSocket 统一使用 `/ws` 前缀
- 所有功能模块通过统一的 `api_v1_router` 注册

### 连接端点（规划）

```
WS /ws/connect                    # 建立连接
WS /ws/notifications              # 通知频道
WS /ws/chat/{room_id}             # 聊天室频道
WS /ws/collab/{repo_id}           # 协作频道
```

### 消息协议

```typescript
// 基础消息格式
interface WebSocketMessage {
  type: string;           // 消息类型
  timestamp: number;      // 时间戳
  sender: {
    id: string;
    username: string;
    avatar?: string;
  };
  payload: any;           // 消息内容
}

// 通知消息
interface NotificationMessage extends WebSocketMessage {
  type: 'notification';
  payload: {
    event: string;        // 事件类型
    repository: string;   // 仓库信息
    data: any;            // 事件数据
    link: string;         // 跳转链接
  };
}

// 聊天消息
interface ChatMessage extends WebSocketMessage {
  type: 'chat';
  payload: {
    roomId: string;
    content: string;
    contentType: 'text' | 'image' | 'code';
    replyTo?: string;     // 回复的消息ID
  };
}
```

---

## 🔗 Webhook API 规划

### REST API 端点（规划）

```
# Webhook 管理
GET    /api/repositories/{repo_id}/webhooks              # 获取 Webhook 列表
POST   /api/repositories/{repo_id}/webhooks              # 创建 Webhook
GET    /api/repositories/{repo_id}/webhooks/{hook_id}    # 获取 Webhook 详情
PATCH  /api/repositories/{repo_id}/webhooks/{hook_id}    # 更新 Webhook
DELETE /api/repositories/{repo_id}/webhooks/{hook_id}    # 删除 Webhook
POST   /api/repositories/{repo_id}/webhooks/{hook_id}/test  # 测试 Webhook

# Webhook 投递记录
GET    /api/repositories/{repo_id}/webhooks/{hook_id}/deliveries  # 获取投递记录
GET    /api/repositories/{repo_id}/webhooks/{hook_id}/deliveries/{delivery_id}  # 获取投递详情
POST   /api/repositories/{repo_id}/webhooks/{hook_id}/deliveries/{delivery_id}/redeliver  # 重新投递
```

### Webhook 数据模型

```typescript
interface Webhook {
  id: string;
  repository_id: string;
  url: string;                    // 推送目标 URL
  secret: string;                 // 签名密钥
  events: string[];               // 订阅的事件类型
  active: boolean;                // 是否启用
  created_at: string;
  updated_at: string;
}

interface WebhookDelivery {
  id: string;
  webhook_id: string;
  event: string;                  // 事件类型
  payload: object;                // 事件数据
  status: 'pending' | 'success' | 'failed';  // 投递状态
  response_status: number;        // HTTP 响应码
  response_body: string;          // HTTP 响应体
  delivered_at: string;           // 投递时间
  duration_ms: number;            // 耗时
  error_message?: string;         // 错误信息
}
```

### Webhook 推送格式

```json
{
  "event": "push",
  "repository": {
    "id": "repo-123",
    "name": "my-project",
    "full_name": "username/my-project",
    "url": "http://lansgit.local/username/my-project"
  },
  "sender": {
    "id": "user-456",
    "username": "john",
    "avatar_url": "http://lansgit.local/avatars/john.png"
  },
  "timestamp": "2026-02-10T12:00:00Z",
  "payload": {
    "ref": "refs/heads/main",
    "before": "abc123...",
    "after": "def456...",
    "commits": [
      {
        "id": "commit-789",
        "message": "Fix bug",
        "author": "john",
        "timestamp": "2026-02-10T11:59:00Z"
      }
    ]
  }
}
```

### 签名验证

Webhook 请求头包含签名信息：
```
X-LanGit-Event: push
X-LanGit-Delivery: delivery-id
X-LanGit-Signature: sha256=<hmac_sha256_signature>
```

验证方式：
```python
import hmac
import hashlib

def verify_signature(payload: bytes, secret: str, signature: str) -> bool:
    expected = 'sha256=' + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## 🏗️ 技术架构

### 后端架构

```
┌─────────────────────────────────────────────────────┐
│                   API v2 Gateway                    │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐  │
│  │ REST API│ │WebSocket│ │ 消息队列  │ │Webhook  │  │
│  │  Layer  │ │  Layer  │ │ (Redis)  │ │ 服务    │  │
│  └────┬────┘ └────┬────┘ └────┬─────┘ └────┬────┘  │
│       └───────────┴───────────┴────────────┘        │
│                       │                             │
│       ┌───────────────┼───────────────┐             │
│       ▼               ▼               ▼             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐         │
│  │通知服务  │    │聊天服务  │    │Webhook  │         │
│  │(Events) │    │(Rooms)  │    │ 服务    │         │
│  └─────────┘    └─────────┘    └─────────┘         │
└─────────────────────────────────────────────────────┘
```

### 数据存储

| 数据类型 | 存储方案 | 说明 |
|---------|---------|------|
| 在线状态 | Redis | 过期时间机制 |
| 消息历史 | PostgreSQL | 持久化存储 |
| 离线消息 | Redis + PostgreSQL | 双写保证可靠性 |
| 会话信息 | Redis | 分布式会话管理 |

---

## 📊 开发计划

### 第一阶段（2-3周）
- [ ] WebSocket 基础设施完善
- [ ] 实时消息通知服务基础版
- [ ] API v2 文档编写

### 第二阶段（3-4周）
- [ ] 通知中心完整功能
- [ ] 推送通知集成
- [ ] 前端 SDK 更新

### 第三阶段（2-3周）
- [ ] Webhook 系统开发
- [ ] 事件推送实现
- [ ] CI/CD 集成测试

### 第四阶段（3-4周）
- [ ] 简易聊天室功能
- [ ] 消息历史管理
- [ ] 性能优化

**总计预估**: 10-14 周

---

## 🔄 API 版本兼容性

| 版本 | 状态 | 说明 |
|-----|------|------|
| API v1 | ✅ 稳定维护 | 现有功能，长期支持 |
| API v2 | 🟡 开发中 | 新增 WebSocket 实时功能 |

- API v1 和 v2 将并行维护
- 客户端可选择性升级
- 数据层完全兼容

---

## 📚 相关文档

- [API v1 开发规划](../api_v1/ROADMAP.md) - 基础功能规划
- [WebSocket 基础测试](../../tests/test_websocket.py) - 现有 WebSocket 测试
- [前端 WebSocket 集成](../../frontend/src/utils/websocket.ts) - 客户端实现

---

**备注**: 本文档为规划文档，具体实现细节可能在开发过程中调整。
