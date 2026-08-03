# Perseus Desktop 应用设计（Spec）

> 日期：2026-08-03
> 状态：草案（待评审）
> 范围：`client/desktop` — 基于 Wails v2 的桌面端，定位为"远程 Perseus 客户端 + 本地工作区"的 IDE 优先协作工具

---

## 1. 背景与目标

Perseus 是一个基于 Git 的本地化协作开发平台（FastAPI + pygit2 后端，React + Ant Design + CodeMirror 的 web 前端）。web 端与后端同源部署，通过浏览器直接访问服务器 API。

**desktop 端**（`client/desktop`，Wails v2.12 + React 模板脚手架）需要解决 web 端无法覆盖的场景：

- **本地文件系统交互**：读写本地工作区、文件监听、原生文件对话框
- **本地 IDE 能力**：LSP 集成（诊断、跳转、补全）、git 本地操作
- **跨源服务器访问**：实际使用中服务器与客户端可能不同源，浏览器 CORS 会拦截直接 API 调用
- **离线优先**：断网时本地工作区照常可用
- **多服务器管理**：一个 desktop 可同时连接多个 Perseus 服务器，并具备服务发现能力

### 1.1 目标

1. UI 设计与基本功能继承 web 端（仓库、PR、Issue、聊天、设置），但重新组织为 IDE 优先的布局
2. 以本地代码编辑 + Git 操作为核心体验，协作功能（PR/Issue/聊天/通知）为辅
3. Go 侧提供本地网关，统一转发对 Perseus 服务器的请求，规避 CORS，token 在 Go 侧注入
4. 多服务器动态注册 + 服务发现，配置不写死
5. 离线模式为第一等公民：连接与否只影响"可用性"，不影响本地功能

### 1.2 非目标（本版本不做）

- 不内嵌 Perseus 服务器（不做本地单机服务端）
- 不做 CI/CD 编排、构建运行
- 不做跨平台打包分发（本期仅 Windows；架构上为后续 macOS/Linux 预留）
- 不实现完整的 VS Code 扩展生态，LSP 语言先覆盖 Python 与 TypeScript/JavaScript

---

## 2. 关键技术决策（已确认）

| 维度 | 决策 | 理由 |
|------|------|------|
| 与服务器的关系 | 远程客户端 + 本地工作区 | clone 到本地编辑，push 回服务器 |
| 定位 | IDE 优先，协作为辅 | 突出桌面端差异化能力 |
| 前端代码复用 | 拷贝移植，各自独立 | 起步快，desktop 可自由改造 |
| 编辑器内核 | Monaco Editor | VS Code 同款，IDE 生态成熟（monaco-languageclient） |
| LSP 范围 | 先 Python（pyright）+ TS/JS（tsserver），可插拔注册表 | 验证全链路后扩展 |
| Git 引擎 | 系统 git CLI（porcelain 解析） | 功能全、与服务器 git 生态一致 |
| 通信模型 | Go 侧本地网关（HTTP + WebSocket）+ Wails 绑定（仅原生能力） | 规避 CORS、离线优先、多服务器代理 |
| 服务器连接 | 多服务器注册表 + 系统密钥库 + SSH 支持 | 服务发现、离线缓存 |
| 凭证存储 | Windows Credential Manager（`go-keyring`） | token 与私钥不落明文 |

---

## 3. 总体架构

```
┌──────────────────────────────────────────────────────────┐
│                Desktop App (Wails v2)                     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │         React 19 前端（Monaco，拷贝移植 web）        │  │
│  │  api/client.ts 只改 BASE_URL → 指向本地网关          │  │
│  │  fetch 风格 API 客户端几乎原样复用（含离线降级）      │  │
│  └───────────────────┬────────────────────────────────┘  │
│          HTTP/WS ────┘  │  Wails 绑定（仅原生能力）        │
│  ┌─────────────────────▼──────────────────────────────┐  │
│  │              Go 后端：本地网关 :0 动态端口           │  │
│  │                                                    │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │  路由表（动态，不写死）                         │  │  │
│  │  │  /api/local/servers/...       服务器注册管理    │  │  │
│  │  │  /api/local/proxy/{serverId}/* 反向代理→Perseus  │  │  │
│  │  │  /api/local/workspaces/...    工作区 CRUD+clone │  │  │
│  │  │  /api/local/git/...           本地 git 操作      │  │  │
│  │  │  /api/local/fs/...            本地文件读取/扫描   │  │  │
│  │  │  /ws/events                  事件流（推送）       │  │  │
│  │  │  /ws/lsp/...                 LSP WebSocket 桥    │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  │                                                    │  │
│  │  服务: server(多服务器+发现) · git · lsp · fs-watch │  │
│  │        · perseus proxy · store(工作区/设置/密钥)    │  │
│  └──────────────┬─────────────────────────────────────┘  │
│   Wails 绑定: 文件对话框·密钥库·窗口·单实例·系统托盘·版本  │
└─────────────────┼────────────────────────────────────────┘
                  │ HTTPS / git(S)SH
       ┌──────────▼───────────┐
       │  Perseus Server(s)  │  ← 多个、动态注册、离线可降级
       └──────────────────────┘
```

### 3.1 数据面：本地网关（核心）

本地网关是 Go 后端内置的一个 HTTP 服务器（启动时绑定 `127.0.0.1:0` 动态端口，避免端口冲突）。**前端永远只与本地网关通信**，跨源请求由 Go 代理到目标 Perseus 服务器，token 在 Go 侧注入，前端不接触密钥。

- 网关端口写入本地 store，供前端读取（`wailsjs` 绑定返回 `{baseURL}`）
- 生产模式下同样适用（打包后前端资源内嵌，仍通过网关访问服务器 API）
- 网关自身无 CORS 限制（Go 侧代理天然绕过浏览器同源策略）

### 3.2 原生能力：Wails 绑定（收窄）

Wails 绑定不再承载数据面，仅暴露 OS 级能力：

- `OpenFolderDialog` / `OpenFileDialog` / `SaveFileDialog`
- `KeychainGet` / `KeychainSet` / `KeychainDelete`
- 窗口控制、单实例锁、系统托盘、app 版本与更新检查

---

## 4. Go 后端模块

采用**分层模块化**，每个模块单一职责、可独立测试；App 层只做绑定转发，网关路由层调用各服务。

```
client/desktop/
├── main.go                 # Wails 入口
├── app.go                  # App 结构体（原生绑定方法）
├── go.mod
├── build/                  # 打包资源
├── frontend/               # React + Monaco 前端（拷贝移植 web）
└── internal/
    ├── gateway/            # 本地网关（HTTP/WS 路由表、代理转发）
    │   ├── server.go       # 网关启动/关闭、动态端口
    │   ├── router.go       # 路由注册
    │   ├── proxy.go        # /api/local/proxy/{serverId}/* 反代
    │   └── ws.go           # /ws/events、/ws/lsp 升级处理
    ├── server/             # 多服务器注册表 + 服务发现
    │   ├── registry.go     # 服务器 CRUD、状态缓存（在线/离线）
    │   ├── discovery.go    # mDNS/导入/探测
    │   └── client.go       # 向目标服务器发请求（token 注入）
    ├── git/                # 系统 git CLI 封装
    │   ├── cli.go          # exec git、porcelain 解析
    │   ├── status.go       # status --porcelain=v2 解析
    │   ├── diff.go         # diff/unified 解析
    │   ├── branch.go       # 分支/提交/日志
    │   └── ssh.go          # GIT_SSH_COMMAND 注入
    ├── lsp/                # 语言服务器管理
    │   ├── registry.go     # 语言→server 注册表（可插拔）
    │   ├── manager.go      # 进程生命周期、按工作区实例化
    │   ├── bridge.go       # JSON-RPC stdin/stdout 桥接
    │   └── servers/        # pyright / tsserver 具体适配
    ├── fs/                 # 文件系统服务
    │   ├── watcher.go      # fsnotify 监听 + 防抖
    │   ├── scan.go         # 目录树扫描（忽略 .git、node_modules）
    │   └── io.go           # 读写文件、二进制识别
    ├── perseus/            # 服务器 API 客户端（对齐 web api/*）
    │   ├── auth.go / repositories.go / pull_requests.go
    │   ├── issues.go / notifications.go / chat.go
    │   └── websocket.go    # 服务器实时推送（通知/聊天）
    ├── store/              # 本地持久化
    │   ├── db.go           # SQLite（工作区索引、设置、服务器注册表）
    │   ├── keychain.go     # 系统密钥库封装（token/SSH 私钥）
    │   └── config.go       # 应用设置
    └── events/             # 事件总线（gateway WS 与 Wails Events 桥）
```

### 4.1 模块职责

**store**
- SQLite 持久化：工作区索引（本地路径 ↔ Perseus 仓库 owner/repo/serverId）、服务器注册表（仅非敏感元数据）、应用设置
- 敏感数据（token、SSH 私钥）一律进系统密钥库（Windows Credential Manager），store 只存引用

**server（多服务器注册表 + 服务发现）**
- 服务器实体：`id`、名称、`baseURL`、认证方式（token/SSH）、健康状态（在线/离线/未知）、上次成功时间、缓存信息（用户信息、可见仓库列表）
- 发现来源：
  1. 手动添加（URL + 账号密码/token，走登录换取 access token）
  2. 导入 `config.toml` / 粘贴服务器列表
  3. 局域网 mDNS 探测（Perseus 服务器发布 `_perseus._tcp` 服务，desktop 主动发现并列出待连接项）
- 离线：注册表保留服务器元数据与缓存状态，断网时前端仍可显示"离线"信息与本地工作区

**perseus client**
- Go 版服务器 API 客户端，方法与响应结构对齐 web 的 `api/auth.ts`、`api/repositories.ts` 等模块，前端"拷贝移植"时响应类型可直接复用
- 所有请求经 `server/client.go` 带 `Authorization: Bearer <token>`，token 来自密钥库

**git**
- 系统 git CLI，操作集：
  - 工作区：`init`、`clone`（HTTP/SSH）
  - 状态：`status --porcelain=v2`、`diff`（工作区/暂存/分支间）
  - 提交：`add`、`restore`、`commit`、`stash`、`rebase`
  - 分支：`branch`、`checkout`、`merge`、冲突检测
  - 远程：`remote`、`fetch`、`pull`、`push`
  - 历史：`log --format=...`
- SSH：`GIT_SSH_COMMAND="ssh -i <key>"` 按服务器注入对应私钥；密码短语私钥用 `ssh-agent` 交互式提示
- git 凭证：HTTP 推送 token 通过 `credential.helper` 写入临时凭证文件（用完即删）或 `-c http.extraHeader`

**lsp**
- 语言服务器注册表（可插拔）：语言 → 启动命令/参数/初始化选项
- 本期：Python → `pyright-langserver --stdio`；TypeScript/JavaScript → `tsserver --stdio`（后续可加 Go、Rust 等）
- 管理器：按工作区惰性启动、进程健康检查、崩溃自动重启（限次）、关闭时优雅停止
- 桥接：JSON-RPC over stdin/stdout；与前端的所有请求/响应/推送统一走网关 WS（`/ws/lsp/{workspaceId}`，双向 JSON-RPC 帧），不另开 HTTP 通道

**fs**
- `fsnotify` 监听打开的工作区，防抖（~300ms）后聚合变更，推送 `/ws/events`
- 目录树扫描排除 `.git`、`node_modules`、`__pycache__`、`dist` 等；二进制文件识别（读取首字节 + 扩展名）
- 读写文件为 UTF-8；大文件（>2MB）提示转为只读或懒加载

**events（事件总线）**
- 统一事件名空间，跨 `gateway/ws` 与 Wails `EventsEmit` 桥接
- 事件类型：`fs:changed`、`git:status`、`git:operation-result`、`lsp:diagnostics`、`lsp:server-status`、`perseus:notification`、`perseus:chat`、`server:health`、`store:changed`

---

## 5. 网关路由契约

前端 `api/client.ts`（拷贝自 web）仅修改 `BASE_URL` 指向网关，并支持按 `serverId` 作用域。路由前缀：

| 路由 | 说明 |
|------|------|
| `GET /api/local/config` | 返回 `{ baseURL, defaultServerId }` |
| `GET/POST/PUT/DELETE /api/local/servers` | 服务器注册表 CRUD |
| `GET /api/local/servers/{id}/health` | 连通性探测（在线时实时测，离线返回缓存） |
| `GET /api/local/servers/{id}/discover` | 触发服务发现（mDNS/导入） |
| `/api/local/proxy/{serverId}/*` | 反向代理到 `server.baseURL/*`（`*` 为服务器完整路径，如 `api/v1/repositories`），Go 注入 token；服务器不可达时返回 `503 { offline: true, cached: {...} }` |
| `GET/POST /api/local/workspaces` | 工作区列表 / 创建（clone 或添加本地目录） |
| `GET /api/local/workspaces/{id}` | 工作区详情 |
| `DELETE /api/local/workspaces/{id}` | 移除工作区（可选删本地目录） |
| `POST /api/local/workspaces/{id}/clone` | 从服务器 clone |
| `POST /api/local/workspaces/{id}/git/:op` | git 操作（status/diff/commit/push/...） |
| `GET /api/local/workspaces/{id}/tree` | 文件树（走本地 fs，替代 web 的服务器端 tree） |
| `GET /api/local/workspaces/{id}/file?path=` | 读取文件内容（本地） |
| `PUT /api/local/workspaces/{id}/file` | 写文件（本地，返回行数/大小） |
| `WS /ws/events` | 前端订阅事件流 |
| `WS /ws/lsp/{workspaceId}` | LSP 双向 JSON-RPC 桥 |
| `WS /api/local/proxy/{serverId}/ws/{path}` | 服务器 WebSocket 透传：`{path}` 追加到 `baseURL/ws/{path}`（如 `notifications`、`logs`、聊天主连接） |

### 5.1 错误与离线语义

- 统一错误响应：`{ error: { code, message, offline?: boolean, cached?: any } }`，前端 `apiRequest` 的 `ApiError` 增加 `offline` 与 `cached` 字段
- 离线定义：目标服务器不可达（连接失败/DNS 失败/超时），与"未登录/无权限"（401/403）区分
- 前端降级策略（见 §7）

---

## 6. 前端架构

### 6.1 工程结构（拷贝移植 web 后改造）

```
client/desktop/frontend/src/
├── main.tsx / App.tsx            # Wails runtime 初始化、网关配置读取
├── api/                          # 拷贝自 web，client.ts 改 BASE_URL + serverId 作用域
├── stores/                       # Zustand：auth/workpace/git/lsp/servers/notifications
├── i18n/                         # 拷贝自 web（zh/en）
├── styles/                       # 拷贝自 web（GitHub 暗色主题）
├── components/                   # 通用组件（拷贝 web 常用组件）
├── layouts/
│   ├── Ideshell.tsx             # 核心：ActivityBar/侧栏/标签页/状态栏/底层面板
│   └── ServerShell.tsx          # 服务器未连接时的欢迎/管理视图
└── views/
    ├── workspace/                # 工作区主视图（explorer + editor + git + diff）
    │   ├── ExplorerPanel.tsx
    │   ├── EditorTabs.tsx        # Monaco 标签页
    │   ├── GitPanel.tsx          # 变更/暂存/提交
    │   ├── DiffView.tsx          # Monaco diff
    │   ├── ProblemsPanel.tsx     # LSP 诊断列表
    │   └── OutputPanel.tsx       # git/lsp 输出日志
    ├── repositories/             # 仓库浏览（web 移植，改走 proxy）
    ├── pull-requests/            # PR（web 移植）
    ├── issues/                   # Issue（web 移植）
    ├── chat/                     # 聊天（web 移植 + WS 透传）
    ├── settings/                 # 设置（web 移植 + 本地设置）
    ├── servers/                  # 多服务器管理 + 服务发现（新）
    └── welcome/                  # 欢迎页（打开工作区/连接服务器）
```

### 6.2 IDE 布局（`IdeShell`）

借鉴 VS Code 四段式布局，沿用 web 的 GitHub 暗色主题配色：

```
┌────┬────────────────────────────────────────────────────────────┐
│ 活 │  顶栏：面包屑 / 分支切换 / 服务器状态 / 搜索 / 通知 / 用户     │
│ 动 │                                                            │
│ 栏 │  ┌──────────┬──────────────────────────────┬────────────┐  │
│  • │  │  侧栏     │  编辑器（Monaco 标签页）       │  辅助面板   │  │
│ Explorer│  Explorer │  - 文件标签 + 面包屑 + diff   │  PR/Issue │  │
│  Search │  Git       │  - 行号/断点/minimap         │  聊天/成员 │  │
│  Git    │  搜索       │  - 错误/警告内联              │           │  │
│  PR     │            │                              │           │  │
│  Issue  │            ├──────────────────────────────┤           │  │
│  Chat   │            │  底层面板：Problems/Output/  │           │  │
│  设置   │            │  git 输出/LSP 服务器状态       │           │  │
│ 服务器  │            └──────────────────────────────┘           │  │
│        │  状态栏：分支 / 服务器在线状态 / 光标位置 / 语言 / UTF-8   │  │
└────┴────────────────────────────────────────────────────────────┘
```

- **活动栏**：Explorer（工作区）、Search（本地内容搜索，优先调用系统 ripgrep，缺失时回退到目录内容扫描）、Source Control（git 变更）、PR、Issues、Chat、Settings、Servers
- **状态栏**：分支名、服务器连接状态（在线/离线）、光标行列、文件语言、编码
- **辅助面板**：默认容纳 PR/Issue 快速视图、聊天；可收起
- 布局尺寸可拖拽调节，状态持久化到 store

### 6.3 Monaco 集成

- 使用 `@monaco-editor/react`（加载器封装）
- 语言服务：内置基本高亮 + 语法；**LSP 能力**（补全/跳转/诊断/格式化/重命名）走 `monaco-languageclient` 或自研轻量协议桥（见 §8）
- 文件与磁盘双向同步：`fs:changed` 事件 → 若文件未修改（无脏标记）则刷新内容；编辑器保存 → `PUT /api/local/workspaces/{id}/file`
- 只读模式：打开后无编辑权限或文件过大时只读；diff 视图用 Monaco diff editor
- Markdown 预览走 web 移植组件

---

## 7. 核心 UX 流程

### 7.1 首次启动 / 服务器接入

1. Welcome 页：列出"已注册服务器"与"最近工作区"，空态引导添加服务器或打开本地目录
2. 添加服务器：输入 `baseURL` → 连通性检测 → 登录（账号密码 或 token）→ 存入注册表（元数据进 SQLite，token 进密钥库）
3. 可选：启动 mDNS 发现，列出局域网可用 Perseus 服务器一键连接

### 7.2 克隆 → 工作区 → 编辑

1. 在服务器仓库列表选择仓库 → "Clone to workspace"（或直接打开本地已有目录为工作区）
2. clone 完成后建立工作区记录（本地路径 ↔ owner/repo/serverId）
3. Explorer 加载本地文件树；打开文件 → Monaco 渲染 → 按语言惰性启动 LSP
4. 编辑保存 → `PUT file` + git status 变更事件 → Source Control 面板显示变更

### 7.3 Git 操作与推送

1. Source Control 面板：变更列表（增删改/未跟踪）、暂存/取消暂存、提交（填写 message）、stash
2. 提交后：`git push`（HTTP 走 token / SSH 走私钥）→ 可选"创建 PR"入口跳转 PR 视图
3. 冲突处理：merge/rebase 冲突 → 差异编辑器三方对比（或左右对比）逐条解决 → 标记 resolved

### 7.4 PR / Issue / 协作（web 移植）

- PR 列表/详情/评论/Review：复用 web 页面，API 走 `/api/local/proxy/{serverId}/api/v1/...`
- Issue 列表/详情/评论：同上
- 聊天与通知：`WS /api/local/proxy/{serverId}/ws/*` 透传服务器实时流
- 编辑器的"讨论/成员"辅助面板保留（数据来自服务器 PR 评论 + 仓库成员）

### 7.5 离线行为

- **本地功能全可用**：文件浏览、编辑、git 本地操作（status/diff/commit/stash）、LSP
- **服务器功能降级**：代理路由返回 `offline:true` → UI 显示"离线"徽标；PR/Issue 列表显示缓存（若 store 有缓存）或友好空态
- **重新联网**：`server:health` 事件自动恢复；前端自动重连 WS 并刷新
- **push/pull 在离线时**：允许本地 commit，push/pull 操作显式报"服务器离线，已暂存本地变更"，用户联网后手动重试

---

## 8. LSP 子系统设计

### 8.1 可插拔语言注册表

```go
type LanguageServer struct {
    Language   string   // "python" | "typescript" | ...
    DisplayName string
    Command    []string // 启动命令
    InitOptions map[string]any
    Roots      []string // 需要监视的根目录提示
    Extensions []string // 匹配文件扩展名
}
```

- 注册表以 Go 常量内置，未来支持从配置/插件扩展
- 按工作区首文件扩展名匹配语言 → 惰性启动服务器实例；同一语言同工作区共享实例

### 8.2 进程与协议

- 子进程：`exec.Command(server.Command...)`，`stdin/stdout` 走 `bufio` 按 `Content-Length` 帧解析
- 生命周期：启动 → `initialize` → `initialized` → 打开文档 `didOpen` → 编辑 `didChange` → 保存 `didSave` → 关闭 `didClose` → 工作区关闭时 `shutdown`/`exit`
- 崩溃处理：捕获退出 → 指数退避重启（最多 3 次）→ 仍失败则上报 `lsp:server-status` 错误态，前端提示"语言服务不可用"

### 8.3 前端协议桥

- 前端通过 `WS /ws/lsp/{workspaceId}` 与后端桥接
- 请求（前端→后端→LSP）：`hover`、`definition`、`references`、`completion`、`signatureHelp`、`rename`、`documentFormatting`
- 推送（LSP→后端→前端）：`publishDiagnostics` → `lsp:diagnostics` 事件 → Monaco markers + Problems 面板
- Monaco 集成：自定义 `CompletionItemProvider` / `DefinitionProvider` / `HoverProvider` / `SignatureHelpProvider` / `RenameProvider`，内部走 WS 桥，避免引入 `monaco-languageclient` 的重量依赖（若其集成成本可控则复用，最终以实现阶段实测为准）

### 8.4 能力矩阵（本期）

| 能力 | Python (pyright) | TS/JS (tsserver) |
|------|------------------|------------------|
| 诊断 publishDiagnostics | ✅ | ✅ |
| 补全 completion | ✅ | ✅ |
| 跳转 definition | ✅ | ✅ |
| 引用 references | ✅ | ✅ |
| Hover | ✅ | ✅ |
| 签名帮助 | ✅ | ✅ |
| 重命名 | ✅ | ✅ |
| 格式化 documentFormatting | ✅ | ✅ |

---

## 9. 错误处理、事件与测试

### 9.1 错误处理

- 网关统一错误结构 `{ error: { code, message, offline?, cached? } }`，全链路透传
- 分层错误码：`AUTH_*`、`SERVER_*`、`GIT_*`、`LSP_*`、`FS_*`、`STORE_*`
- 前端 `ApiError` 扩展 `offline` / `cached` 字段，Zustand store 统一捕获并映射为用户可读消息（i18n）

### 9.2 事件

- 事件名见 §4.1 events 模块；所有事件同时支持网关 WS 订阅与 Wails `EventsEmit`（供原生层使用）
- 事件带上 `{ workspaceId?, serverId?, ts }` 元数据，前端按需过滤

### 9.3 测试

| 层 | 方式 |
|----|------|
| git 模块 | `go test`，用真实临时仓库（`git init` + fixture 文件）验证 status/diff/commit/branch 解析 |
| lsp 模块 | `go test` 集成测试：起 pyright/tsserver 假进程，验证 initialize/didOpen/publishDiagnostics 链路 |
| proxy/网关 | `go test` + `httptest` 假服务器，验证 token 注入、离线 503 语义 |
| store | 内存 SQLite（`file::memory:`）+ 假 keychain |
| 前端 | 沿用 web 的 ESLint/TS 检查；关键流（克隆→编辑→提交）手工验收清单 |
| 整体 | `wails build` + 手工冒烟（真服务器 + 真 git + 真 LSP） |

---

## 10. 实施阶段（Phase）

每个 Phase 对应一份独立 implementation plan。

**Phase 1 — 骨架打通（本地优先）**
- Go 骨架：store（SQLite + keychain）、gateway 动态端口、Wails 绑定（对话框/密钥库）
- 工作区：添加本地目录、clone 单仓库、Explorer 文件树、文件读写
- Monaco 编辑器：标签页、保存、只读、diff 基础
- git：status/diff/add/commit/push/pull 基础操作
- 前端：IdeShell 布局 + Welcome + Workspace 视图 + Settings

**Phase 2 — 服务器接入 + 协作**
- server 注册表 + 登录 + token 密钥库 + health 探测
- perseus proxy 全量路由 + 离线语义
- 仓库/PR/Issue 页面移植（走 proxy）
- 通知 + 聊天（WS 透传）

**Phase 3 — LSP**
- lsp 注册表 + 进程管理 + pyright/tsserver 适配
- WS 桥 + Monaco providers（诊断/补全/跳转/引用/hover/签名/重命名/格式化）
- Problems 面板 + LSP 状态指示

**Phase 4 — 增强与收尾**
- SSH 推送（私钥/ssh-agent）、git 凭证注入
- 多服务器 mDNS 发现 + 离线缓存展示
- 系统托盘、单实例、自动更新检查、Windows 打包（NSIS）

---

## 11. 风险与对策

| 风险 | 对策 |
|------|------|
| LSP 与 Monaco 桥接成本高 | Phase 3 前置最小验证（pyright 诊断链路）；若自研成本过高改用 monaco-languageclient |
| 大仓库 clone / 大文件性能 | 文件树懒加载、>2MB 文件只读提示、git 操作用 goroutine + 事件回报进度 |
| tsserver 初始化慢/内存高 | 惰性启动、空闲超时关闭、单工作区共享实例 |
| 多服务器 token 泄露 | 全量走系统密钥库，网关进程内不落盘明文；SSH 私钥同理 |
| Windows 打包分发 | 后续 NSIS + WebView2 引导；本期不阻塞核心开发 |
