# Perseus Desktop

桌面端（Wails v2 + React 19），定位为"远程 Perseus 客户端 + 本地工作区"的 IDE 优先协作工具。

## 架构一页

```
┌──────────────────────────────────────────────┐
│         Desktop App (Wails v2)                │
│  ┌────────────────────────────────────────┐  │
│  │ React 19 前端（Monaco 编辑器）           │  │
│  │ api/client.ts BASE_URL → 本地网关        │  │
│  │ fetch 走 X-Gateway-Token 会话校验        │  │
│  └──────────────┬─────────────────────────┘  │
│      HTTP/WS    │    Wails 绑定（原生能力）   │
│  ┌──────────────▼─────────────────────────┐  │
│  │ Go 本地网关（127.0.0.1:0 动态端口）      │  │
│  │  /api/local/workspaces... 工作区 CRUD   │  │
│  │  /api/local/workspaces/{id}/git/{op}   │  │
│  │  /api/local/workspaces/{id}/tree|file  │  │
│  │  /api/local/servers...   服务器注册表    │  │
│  │  /api/local/proxy/{id}/* 通用反向代理    │  │
│  │  /api/local/proxy/{id}/ws/*  WS 透传    │  │
│  │  /api/local/proxy/{id}/collab 协作代理   │  │
│  │  （Hocuspocus 首帧 token 注入）          │  │
│  │  CORS 白名单 + 会话 token 防护           │  │
│  └──────────────┬─────────────────────────┘  │
│                 │ 系统密钥库(Windows CM)      │
│                 ▼                            │
│        SQLite（工作区/服务器/设置元数据）      │
└──────────────────────────────────────────────┘
```

- **Go 网关**：前端唯一通信入口，动态端口避免冲突；Origin 白名单（`http://localhost:34115`、`wails://localhost`）+ `X-Gateway-Token` 会话校验，仅绑定 loopback。
- **SQLite**（modernc.org/sqlite，纯 Go）：工作区/服务器/设置元数据。
- **系统密钥库**（go-keyring → Windows Credential Manager）：token/私钥不入库。
- **git**：系统 git CLI 封装（porcelain v2 解析、diff、clone/push/pull、凭据注入）。

## 开发命令

```bash
# 开发模式（前端热重载，自动起网关）
wails dev

# 打包（NSIS 安装包 / 可执行文件）
wails build

# 后端单测（含 store/server/gateway/ws/proxy/offline 语义）
go test ./...

# 前端类型检查 + 构建
cd frontend && npm run build
```

仓库根目录 `internal/gateway/smoke_test.go` 为 live-backend 冒烟测试：先 `docker compose up -d` 起后端（:8080），再 `go test ./internal/gateway -run TestSmokeLiveBackend -v` 验证注册表 + 代理 + 离线语义。

依赖要求：Go 1.25+、Wails v2.12、Node 20+。

## Phase 1 功能范围

- 工作区：添加本地目录 / clone 单仓库（手填 URL + 一次性凭据）
- Explorer 文件树（忽略 `.git`/`node_modules`/`__pycache__`/`dist`/`venv`）、文件读写（>2MB 只读提示、二进制识别）
- Monaco 编辑器：标签页、保存、只读
- git：status/diff/add/commit/push/pull/log/branch
- IDE 布局（活动栏/侧栏/编辑器/状态栏）+ Welcome + Settings

## Phase 2A 功能范围

- 多服务器注册表：账密登录（Go 侧换 token）或粘贴 token；CRUD、health 探测与状态缓存
- 通用反向代理：`/api/local/proxy/{serverId}/*` 全量转发服务器 API，token 仅存于系统密钥库，前端不接触
- 离线语义：目标不可达 → `503 {offline:true}`；GET 只读接口带 LRU 缓存（200 条 / 10MB / TTL 24h），离线命中透出 `cached`
- WS 透传：`/api/local/proxy/{serverId}/ws/{path}`，gorilla/websocket 双向帧转发 + 断线指数退避重连
- 前端 ServerShell 双壳：顶栏服务器选择 + health 徽标；仓库页忠实移植 web（代码/设置可用，issues/PR 留 2B），支持 "Clone to workspace"（Git CLI 克隆 + 自动切入 IdeShell）

## UI 补全范围（2026-09-10 批次，对齐 web 端能力）

- **门户聚合搜索**（T3）：标题栏搜索 Modal，仓库/Issue/PR 三分组 + 深链直达；后端新增 `GET /api/v1/search/global`（两端可共用）
- **PR 创建 Modal**（T1）：PullRequestsView 新建弹窗接线
- **仓库设置 Tab**（T2）：Webhooks（CRUD/测试/投递记录）+ 协作者（增删/角色）
- **团队聊天**（T4）：门户三栏全屏页（频道 = 仓库房间；Markdown/reactions/附件/typing/presence）+ IDE 活动栏精简面板，socket 常驻；后端补 `GET /api/v1/rooms`
- **通知面板**（T5）：铃铛 Popover（未读计数/全部已读/删除，点击按 target_type 深链）
- **我的工作**（T6）：跨仓库「我发起的 PR / 我的 Issue」聚合视图
- **协作辅助栏**（T7）：IDE 右侧 aux（待处理 PR / 相关 Issue / 成员在线 presence）
- **协作编辑（T9）**：接入 Yjs 统一底座 —— Go 网关 collab 代理（lib0 varint 编解码 + 首帧 AuthenticationMessage token 注入）+ `CollabSession`（HocuspocusProvider）+ `MonacoBinding`，与 web 共享 collab-gateway 与保存语义（stateless collab-save → Git commit 全员广播）

## 已知边界

- 网关会话 token 仅存内存，随进程退出失效
- 数据目录持久化在 `%APPDATA%\perseus\app.db`
- Releases/Builds tab、Dashboard 贡献图/活动流、用户中心（SSH Keys/OAuth）尚未移植，两端差异以 [`docs/plans/desktop-port-sync.md`](../docs/plans/desktop-port-sync.md) 清单跟踪
- Clone to workspace 走 Git CLI；SSH 推送、mDNS、托盘/单实例/NSIS 属 Phase 4（见 `docs/archive/specs/2026-08-03-desktop-app-design.md`）
