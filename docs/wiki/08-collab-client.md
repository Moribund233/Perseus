# 08 · 协同网关与客户端（collab-gateway + client）

> 本项目不只一个 Python 后端。还有 Node.js 协同编辑网关、Go 桌面端、React 前端。

---

## 一、collab-gateway —— 协同编辑网关（Node.js）

### 1.1 定位

一个独立运行的 **Yjs 协议网关**，负责：
- 客户端 ←→ Yjs CRDT 同步
- Redis 持久化 session 状态
- 编辑者感知（awareness）广播
- 通过 HTTP 回调（`/api/v1/collab-internal/*`）向 Python 后端鉴权、踢人、查询权限

### 1.2 技术栈

- Node.js
- Yjs（官方） + lib0（工具库）
- Redis（session 持久化 + 版本计数 + 分布式锁）
- HMAC-SHA256 内部回调签名

### 1.3 文件结构

```
collab-gateway/
├── server.mjs                # 核心服务器（buildGateway + startGateway）
├── sessionTtl.mjs            # 会话 TTL 管理
├── versionCounter.mjs        # 版本计数（防丢失更新）
├── redisPersistence.mjs      # Redis 持久化读写
├── package.json
└── tests/
    ├── gateway.test.mjs
    ├── gatewayFollow.test.mjs
    ├── gatewayHardening.test.mjs
    ├── redisIntegration.test.mjs
    ├── redisPersistence.test.mjs
    ├── versionCounter.test.mjs
    └── support.mjs
```

### 1.4 关键导出

```javascript
// server.mjs
export const APP_URL           // Python 后端地址（默认 http://app:8000）
export const INTERNAL_SECRET   // HMAC 签名密钥，与 Python 后端共享
export const SESSION_TTL_MS    // 会话空闲 TTL（默认 1h）
export const MAX_CONNECTIONS_PER_DOC
export const MAX_AWARENESS_BYTES
export const callApp(path, { method, body })  // HTTP 回调 Python 后端
export function parseConnectionToken(raw)      // 解析客户端连接 token
export function buildGateway({ ... })         // 构建网关（注入依赖）
export async function startGateway({ ... })   // 启动网关
```

### 1.5 与 Python 后端的协作链路

```
桌面端/浏览器 (Monaco + lib0/client)
        │  WebSocket (Yjs protocol, token=...)
        ▼
collab-gateway server.mjs
        │
        ├─► 解析连接 token（session_id + owner + 签名）
        ├─► callApp("/api/v1/collab-internal/verify") 鉴权
        │
        ├─► Redis: 持久化 session state
        ├─► Redis: versionCounter（版本号递增）
        ├─► Redis: sessionTtl（空闲续期）
        │
        ├─► callApp("/api/v1/collab-internal/presence") 更新在线状态
        │
        ├─► callApp("/api/v1/collab-internal/kick") （可选，Python 主动踢人）
        │
        └─► 广播 Yjs 更新 / awareness 到所有连接客户端
```

### 1.6 防滥用策略

| 策略 | 说明 |
|------|------|
| 单文档最大连接数 | `MAX_CONNECTIONS_PER_DOC`（默认 50） |
| awareness 大小限制 | `MAX_AWARENESS_BYTES`（防止恶意扩张状态） |
| Viewport sanitize | 清理无效视口信息 |
| Follow sanitize | 清理无效跟随关系 |
| Unsaved sanitize | 未保存标记清理 |
| 连接 token 必须签名 | Python 后端签发，gateway 独立验签 |

---

## 二、桌面端（client/desktop）—— Go + Wails

### 2.1 定位

一个基于 Wails 的 Windows/macOS/Linux 桌面应用，内嵌 WebView 渲染前端，Go 层提供本地能力（文件系统 / Git / LSP / 终端 / 缓存）。

### 2.2 技术栈

- **后端（Go）**：Wails v2 + pure-Go Git 封装（go-git 或调用外部 git）
- **前端**：React 19 + TypeScript（与 Web 端共享大量组件）
- **本地存储**：SQLite + 钥匙串（keychain）存凭据

### 2.3 Go 内部包

```
client/desktop/internal/
├── fs/                 # 文件系统（io.go / scan.go）
├── gateway/            # 本地网关（路由 + LSP + WS + Cache + 终端）
│   ├── gateway.go      # 核心网关
│   ├── router.go       # HTTP 路由
│   ├── handlers_collab.go
│   ├── handlers_config.go
│   ├── handlers_fs.go
│   ├── handlers_lsp.go
│   ├── handlers_search.go
│   ├── handlers_servers.go
│   ├── handlers_terminal.go
│   ├── handlers_workspace.go
│   ├── middleware.go
│   ├── proxy.go        # 远程仓库 HTTP 代理
│   ├── ws.go           # WS 处理
│   ├── lib0.go         # 本地 Yjs 协作桥接
│   ├── json.go
│   └── term_factory_windows.go
├── git/                # Go Git 封装
│   ├── cli.go / clone.go / diff.go / operations.go / remote.go / status.go
├── lsp/                # Language Server Protocol
│   ├── framing.go / manager.go / registry.go / session.go
├── server/             # 远程服务管理
│   ├── client.go / registry.go
├── store/              # 本地 SQLite 存储
│   ├── db.go / keychain.go / servers.go
└── term/               # 终端集成
    └── term.go
```

### 2.4 Go ↔ 前端 通信

Wails 通过：
- **Bindings**：Go 函数暴露为前端可调用（`wailsjs/go/main/App.js`）
- **Events**：Go 向前端推送事件（如构建进度 / LSP 更新）
- **本地 HTTP 代理**：前端请求本地 `http://127.0.0.1:<port>`（gateway 路由），Go 层再代理到远程 Perseus 后端或本地 Git

### 2.5 关键本地能力

| 能力 | Go 实现 | 说明 |
|------|---------|------|
| 文件浏览 | `internal/fs/io.go` + `scan.go` | 本地工作区文件系统 |
| Git 操作 | `internal/git/` | pure-Go clone/diff/status/remote |
| 终端 | `internal/term/term.go` | 嵌入终端模拟器 |
| LSP | `internal/lsp/` | Language Server 管理（Python/TS/Go 等） |
| 远程代理 | `gateway/proxy.go` | 把本地 HTTP 请求代理到远程 Perseus |
| 缓存 | `gateway/cache.go` | 本地仓库缓存 |
| 协作桥接 | `gateway/lib0.go` | 本地与 collab-gateway 间的 Yjs 桥 |

---

## 三、Web 客户端（client/web）—— React + Vite

### 3.1 技术栈

- React 19 + TypeScript 6
- Vite 8（手动代码分割）
- Zustand 5（轻量响应式状态）
- React Router v7（Layout Routes + Protected Routes）
- Ant Design 6（企业级 UI，GitHub 暗色主题）
- i18next（中英文双语）
- React Hook Form + Zod（表单验证）
- CodeMirror 6（代码编辑器）

### 3.2 目录结构

```
client/web/src/
├── api/                 # API 客户端（fetch 封装 + WS URL 工具）
│   ├── client.ts        # Axios-like fetch 封装
│   ├── chatSocket.ts    # 聊天 WS
│   ├── logSocket.ts     # 日志 WS
│   ├── notificationSocket.ts
│   ├── admin.ts / auth.ts / builds.ts / ...   # 按领域拆分
├── components/          # 通用 UI
│   ├── admin/           # 管理员专属组件
│   ├── chat/            # 聊天
│   ├── dashboard/       # 仪表盘
│   ├── editor/          # 代码编辑器（collabController）
│   ├── explorer/        # 文件树
│   ├── layout/          # 布局（AppLayout / LandingLayout / GlobalSearch）
│   ├── repo/            # 仓库级 Tab（Builds / Releases / Settings）
│   ├── settings/        # 设置页
│   ├── skeleton/       # 骨架屏
│   └── ...
├── routes/              # 按页面路由组织
│   ├── admin/
│   ├── chat/ · dashboard/ · editor/ · issues/
│   ├── landing/         # 登录 / 注册入口
│   ├── pull-requests/
│   ├── repositories/
│   ├── search/ · settings/
│   └── App.tsx          # 路由总入口
├── stores/              # Zustand 状态（每个领域一个）
│   ├── auth.ts / editorState.ts / issues.ts
│   ├── notifications.ts / pullRequests.ts
│   └── repositories.ts
├── i18n/locales/        # 中英语言包
├── styles/              # theme.ts + index.css
└── main.tsx             # React root
```

### 3.3 主要页面

| 路由 | 组件 | 说明 |
|------|------|------|
| `/` | Landing | 登录 / 注册 |
| `/dashboard` | MyWork | 我创建的 PR / Issue / 仓库活跃度 |
| `/repositories` | RepositoriesView | 仓库列表 + 搜索 |
| `/repositories/{owner}/{repo}` | Repository detail | 仓库主页（README） |
| `/repositories/{owner}/{repo}/tree/{path}` | Explorer | 文件树浏览 |
| `/repositories/{owner}/{repo}/pulls` | PullRequestsView | PR 列表 |
| `/repositories/{owner}/{repo}/pulls/{num}` | PullRequestDetail | PR 详情 + diff |
| `/repositories/{owner}/{repo}/issues` | IssuesView | Issue 列表 |
| `/repositories/{owner}/{repo}/issues/{num}` | IssueDetail | Issue 详情 |
| `/repositories/{owner}/{repo}/settings` | RepositorySettings | 仓库设置 |
| `/chat` | ChatView | 实时聊天 |
| `/editor` | Monaco 编辑器 | 协作编辑 |
| `/search` | GlobalSearchView | 跨仓库代码搜索 |
| `/settings` | Settings | 个人设置 |
| `/admin/*` | Admin 各 Section | 管理员控制台（Overview / Config / Logs / Metrics / Debug / Redis / Stream Log） |

### 3.4 API 客户端封装模式

```typescript
// api/client.ts —— 统一 fetch 封装
// 自动注入 Authorization header
// 401 自动尝试 refresh_token
// 统一错误处理

// api/repositories.ts —— 领域函数
export async function listRepositories(params): Promise<Repo[]>
export async function getRepository(owner, repo): Promise<Repo>
export async function createRepository(data): Promise<Repo>
...
```

---

## 四、原型 UI（client/prototype/desktop-ui）

纯 HTML/CSS/JS 原型，早期验证用（不再是主线），保留在仓库里供快速参考。

---

## 下一章

👉 [09 · 部署与运行](09-deployment.md)
