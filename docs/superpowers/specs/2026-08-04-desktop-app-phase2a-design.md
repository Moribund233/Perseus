# Perseus Desktop Phase 2A 设计（Spec）

> 日期：2026-08-04
> 状态：待评审
> 前置：Phase 1 已交付（store/keychain/fs/git/网关骨架/IdeShell/仓库工作区）
> 范围：`client/desktop` — 服务器接入 + 协作能力的第一阶段（Phase 2 拆分为 2A/2B 两份 plan，本 spec 覆盖 2A）

---

## 1. 背景与目标

Phase 1 已完成本地优先骨架：SQLite store、密钥库、本地 fs、git CLI、本地网关（动态端口 + CORS 白名单 + 会话 token）、Wails 绑定、IdeShell 布局与 Monaco 编辑器。

Phase 2 目标是把 desktop 变为"远程 Perseus 客户端"：连接一个或多个 Perseus 服务器，浏览/克隆仓库，并把 web 端协作页面（仓库/PR/Issue/聊天）接入。为控制单份 plan 规模，**Phase 2 拆为两份**：

- **2A（本 spec）**：服务器注册表 + 登录 + token 密钥库 + health 探测 + 通用 proxy 全量路由 + 离线语义 + 仓库页面移植
- **2B（后续 spec）**：PR/Issue 页面移植 + 通知/聊天（WS 透传）

### 1.1 目标（2A）

1. 多服务器注册表：手动添加（账密登录 或 粘贴 token）、CRUD、health 探测与状态缓存
2. 通用反向代理：`/api/local/proxy/{serverId}/*` 全量转发服务器 API，token 仅存于 Go 侧（密钥库），前端不接触
3. 离线语义：目标不可达时返回 `503 {offline:true, cached}`，GET 只读接口带 LRU 缓存
4. 前端 ServerShell 双壳：浏览服务器时进入服务器视图，本地编辑时进入 IdeShell
5. 仓库页面从 web 忠实移植，走 proxy，并新增"Clone to workspace"桌面集成

### 1.2 非目标（本 spec 不做）

- PR/Issue/聊天页面移植（2B）
- OAuth 浏览器流（仅账密 + token 粘贴）
- mDNS 服务发现、离线缓存落盘、SSH 推送（Phase 4）
- Go 侧类型化 perseus API 客户端（用通用代理，见 §3 取舍）

---

## 2. 架构决策（已确认）

| 维度 | 决策 | 理由 |
|------|------|------|
| 代理形态 | **通用反向代理**（非类型化客户端） | Go 侧无需复刻服务器 API 结构体，前端 web 类型原样复用；代理天然覆盖全部接口 |
| 认证 | 账密登录（Go 侧换 token）或粘贴 token | 桌面端不引入 OAuth 浏览器流，最简单可靠 |
| token 存放 | Windows Credential Manager，key=`server:<id>:token` | 复用 Phase 1 keychain，不落盘明文 |
| health | `GET {baseURL}/api/v1/users/me` 探测 + 注册表持久化 + 内存 TTL 缓存 | 复用登录探针，接口稳定 |
| 布局 | ServerShell / IdeShell 双壳，state 切换 | 符合 spec §6.1；desktop 无 router，沿用现有模式 |
| 仓库页 | web 忠实移植（去 AppLayout 外壳）+ Clone 集成 | "继承自 web，微调布局" |

---

## 3. Go 后端

### 3.1 store：`servers` 表

新增 `internal/store/servers.go`（表在 `db.go` 的迁移中一并创建），仅存非敏感元数据：

```go
type Server struct {
    ID          string    `json:"id"`
    Name        string    `json:"name"`
    BaseURL     string    `json:"base_url"`
    AuthMethod  string    `json:"auth_method"`   // "password" | "token"
    Username    string    `json:"username,omitempty"`
    Health      string    `json:"health"`        // "online" | "offline" | "unknown"
    LastChecked string    `json:"last_checked,omitempty"` // RFC3339
    LastSuccess string    `json:"last_success,omitempty"`
    CreatedAt   time.Time `json:"created_at"`
}
```

方法：`CreateServer` / `ListServers` / `GetServer` / `UpdateServer` / `DeleteServer` / `SetServerHealth`。

### 3.2 server 服务模块：`internal/server/`

- `registry.go`：注册表 CRUD，包装 store；删除时清理密钥库 token
- `client.go`：
  - `Login(baseURL, username, password) (token string, err error)`：POST `{baseURL}/api/v1/auth/login`，解析 `{token, ...}`
  - `Probe(baseURL, token) error`：GET `{baseURL}/api/v1/users/me`（带 Bearer）
  - `Token(serverID) (string, error)`：从密钥库取 token
  - `SetToken/DeleteToken`：写/删密钥库（key=`server:<id>:token`）
- 添加服务器流程（`POST /api/local/servers`）：
  1. 请求体 `{name, baseURL, username?, password?, token?}`
  2. password → `Login` 换 token；token → 直接用
  3. `SetToken` 入密钥库 → `Probe` 定初始 health
  4. `CreateServer` 入库；失败则回滚（删 token）
- health：`probeServer(id)` 调 Probe，成功 → `online` 更新 LastSuccess，失败 → `offline`；结果写入 store + 内存缓存（TTL 60s，`GET /servers/{id}/health` 直接返回缓存，过期才实测）

### 3.3 网关路由

`internal/gateway/router.go` 新增：

```
GET    /api/local/servers              列表（元数据，无 token）
POST   /api/local/servers              添加（登录/探测）
PUT    /api/local/servers/{id}         更新元数据
DELETE /api/local/servers/{id}         删除 + 清密钥库
GET    /api/local/servers/{id}/health  按需探测（缓存 TTL）
POST   /api/local/servers/{id}/refresh 重新校验 token（改密码后刷新）
GET/POST/PUT/PATCH/DELETE /api/local/proxy/{serverId}/*   通用反代
WS     /api/local/proxy/{serverId}/ws/{path}              WS 透传
GET    /api/local/config               增加 defaultServerId 字段
```

新路由复用现有 `withSecurity` 中间件（CORS 白名单 + `X-Gateway-Token` 校验）。

### 3.4 通用反向代理：`internal/gateway/proxy.go`

**HTTP 反代**
- 解析 `{serverId}`，`GetServer` 校验存在；`Token(serverID)` 取 token，缺失 → `401 AUTH_TOKEN_MISSING`
- 上游 URL：`{baseURL}/{path}`，`path` 为 serverId 后的完整路径（含 query）
- 构造 `http.Client`（超时 30s），逐字节透传 body；注入 `Authorization: Bearer <token>`；去掉可能污染的头（`X-Gateway-Token` 不外发）
- 上游 4xx/5xx：原样透传状态码 + 上游 body
- **离线判定**：`*url.Error`（连接/DNS/超时）→ 503 语义

**GET LRU 缓存**
- 内存实现（`internal/gateway/cache.go`）：`container/list` + `map`，key=`serverId + path + query`
- 上限 200 条 / 10MB，TTL 24h；仅缓存 2xx GET 响应（存 body + Content-Type + 状态码）
- 离线且命中 → `503 {error:{code:"SERVER_OFFLINE", message, offline:true, cached:{...}}}`
- 离线未命中 → `503 {error:{..., offline:true, cached:null}}`
- 写操作（POST/PUT/PATCH/DELETE）不做缓存

**WS 透传**
- 独立注册 `/api/local/proxy/{serverId}/ws/{path}`，避免与 HTTP catch-all 冲突
- 上游：`ws(s)://{host}/ws/{path}?token=<serverToken>`（服务器 WS 认证用 query token）
- 用 `gorilla/websocket` 双向帧转发，带心跳 ping；断线指数退避重连（上限 5 次）
- 网关侧仍要求 `X-Gateway-Token`（本地安全边界不因透传放宽）

### 3.5 错误结构

统一：`{error: {code, message, offline?, cached?}}`
- `SERVER_OFFLINE`（503，offline:true）
- `AUTH_TOKEN_MISSING`（401）
- `SERVER_NOT_FOUND`（404）
- `LOGIN_FAILED`（401，账密错误原样透传服务器 message）
- 上游非 2xx：透传上游状态码与 body，不重包

---

## 4. 前端

### 4.1 api 层

- `api/client.ts`：新增 `proxyRequest<T>(serverId, path, opts)` → `fetch(\`${baseURL}/api/local/proxy/${serverId}${path}\`)` + `X-Gateway-Token`；`ApiError` 增加 `offline?: boolean`、`cached?: any`
- 新建 `api/servers.ts`：`register(data)` / `list()` / `remove(id)` / `refresh(id)` / `health(id)`
- 移植 `api/repositories.ts`：`repositoriesApi` 各方法改收 `serverId` 参数，内部走 `proxyRequest(serverId, '/api/v1/...')`，接口类型原样保留
- issues / pull-requests 的 api 与 store **留到 2B**，2A 不移植

### 4.2 stores

- 新建 `stores/servers.ts`（Zustand）：`servers: Server[]`、`currentServerId: string|null`、`setServers` / `setCurrent` / `upsert` / `remove`；加载时 `list()` + 恢复 `currentServerId`（存 localStorage）
- 移植 `stores/repositories.ts`（接口改 `proxyRequest`，其余逻辑保留）；issues store 留到 2B

### 4.3 ServerShell 双壳

- `App.tsx` 顶层状态：`mode: "workspace" | "server"`；工作区存在 → IdeShell；`currentServerId` 存在且非工作区模式 → ServerShell；否则 Welcome
- `layouts/ServerShell.tsx`：
  - 顶栏：返回工作区按钮、服务器选择器（Dropdown）、health 徽标、刷新
  - 主体：`view: "repositories" | "issues" | "pull-requests" | "chat"` 状态切换（沿用 state 模式）
  - 空态：未选服务器时提示去 ServerManager 添加
- `views/servers/ServerManager.tsx`：服务器列表（health Tag / 删除 / 刷新）+ 添加 Modal（baseURL + name；账密 或 token 单选）+ 登录失败错误提示
- `views/Welcome.tsx`：新增"连接服务器"卡片，列出已注册服务器快捷进入
- `views/settings/Settings.tsx`：在占位页补充服务器注册表只读摘要（可选）

### 4.4 仓库页移植：`views/repositories/`

- 移植 web `routes/repositories/index.tsx`：列表视图（筛选 tabs、搜索、骨架）+ 详情视图（信息头 + tabs：代码/issues/PR/设置），内部结构忠实保留，**删除 web AppLayout 外壳**（面包屑/搜索由 ServerShell 顶栏承担），路由参数（owner/repo）改为 store/state 传递
- 文件浏览走服务器端 tree/blob（proxy），与本地工作区 fs 无关
- 详情页 tabs：**代码/设置**在 2A 可用；**issues/PR** 在 2A 显示占位（"2B 实现"），不联数据
- **新增桌面集成**：详情页"Clone to workspace"按钮 → 调 Phase 1 `createWorkspace({serverId, url, clone:true})`，成功后 toast + 可切换进 IdeShell 打开
- 复用：`RepositoriesSkeleton`、`PageTransition`、i18n `app.repositories.*`

### 4.5 i18n

新增命名空间：`desktop.servers.*`（添加/登录/health/删除）、`desktop.serverShell.*`（返回/服务器选择/离线提示）。仓库页沿用已移植的 `app.repositories.*`。

---

## 5. 错误处理与事件

- 前端：`proxyRequest` 捕获 503 `offline:true` → store 标记服务器 offline；页面显示离线徽标 + cached 数据（若有）或友好空态
- 后端：错误码见 §3.5，全链路透传
- 事件（2A 暂不接 WS 事件流，health 变化由前端轮询/操作触发刷新；2B 再接 /ws/events）

---

## 6. 测试

| 层 | 方式 |
|----|------|
| store.servers | 内存 SQLite + 断言 CRUD/health 字段 |
| server registry | fake keychain + 内存 store；添加/删除/回滚逻辑 |
| proxy | `httptest` 假服务器：token 注入、4xx 透传、离线 503、LRU 缓存命中/未命中、写操作不缓存 |
| WS 透传 | `httptest.NewServer` + 假 WS 端点，验证帧往返 |
| health | 假服务器 200/超时两种探针 |
| 前端 | `npm run build`（tsc）+ 手工验收清单 |

手工验收：Docker 起后端（:8080）→ 添加服务器（账密/token）→ 浏览仓库列表/详情 → Clone to workspace → IdeShell 编辑。

---

## 7. Task 拆分（粗）

1. store servers 表 + CRUD + 测试
2. server 模块：registry/client/login/probe/token + 测试
3. 网关：servers 路由（CRUD/health/refresh）+ 测试
4. 网关：proxy HTTP 反代 + token 注入 + 离线语义 + 测试
5. 网关：GET LRU 缓存 + 测试
6. 网关：WS 透传 + 测试
7. 前端：api/servers + proxyRequest + ApiError 扩展
8. 前端：stores/servers + repositories store 移植
9. 前端：ServerShell + ServerManager + Welcome 接线
10. 前端：仓库页移植 + Clone 集成
11. i18n 补充 + 全量 build/vet/test
12. 手工冒烟验收 + README 更新

---

## 8. 风险与对策

| 风险 | 对策 |
|------|------|
| 服务器 API 路径/字段与 web 假设不一致 | 以真实后端手工验收为准；代理透传不解析 body，天然兼容 |
| WS 透传选型/重连成本 | gorilla/websocket 成熟稳定；2A 先实现透传+重连，聊天业务 2B 再接 |
| 离线缓存体积 | LRU 200 条/10MB + TTL 24h，超限逐出 |
| 账密登录失败时回滚不一致 | 添加服务器失败即删已写 token，保证注册表一致 |
