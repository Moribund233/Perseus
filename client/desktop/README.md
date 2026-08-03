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
│  │  CORS 白名单 + 会话 token 防护           │  │
│  └──────────────┬─────────────────────────┘  │
│                 │ 系统密钥库(Windows CM)      │
│                 ▼                            │
│        SQLite（工作区/设置元数据）            │
└──────────────────────────────────────────────┘
```

- **Go 网关**：前端唯一通信入口，动态端口避免冲突；Origin 白名单（`http://localhost:34115`、`wails://localhost`）+ `X-Gateway-Token` 会话校验，仅绑定 loopback。
- **SQLite**（modernc.org/sqlite，纯 Go）：工作区/设置元数据。
- **系统密钥库**（go-keyring → Windows Credential Manager）：token/私钥不入库。
- **git**：系统 git CLI 封装（porcelain v2 解析、diff、clone/push/pull、凭据注入）。

## 开发命令

```bash
# 开发模式（前端热重载，自动起网关）
wails dev

# 打包（NSIS 安装包 / 可执行文件）
wails build
```

依赖要求：Go 1.25+、Wails v2.12、Node 20+。

## Phase 1 功能范围

- 工作区：添加本地目录 / clone 单仓库（手填 URL + 一次性凭据）
- Explorer 文件树（忽略 `.git`/`node_modules`/`__pycache__`/`dist`/`venv`）、文件读写（>2MB 只读提示、二进制识别）
- Monaco 编辑器：标签页、保存、只读
- git：status/diff/add/commit/push/pull/log/branch
- IDE 布局（活动栏/侧栏/编辑器/状态栏）+ Welcome + Settings

## 已知边界（Phase 1）

- 网关会话 token 仅存内存，随进程退出失效
- 数据目录持久化在 `%APPDATA%\perseus\app.db`；设置项尚为占位
- 多服务器注册表、Perseus 代理、离线缓存、LSP、SSH 推送等属 Phase 2+（见 `docs/superpowers/specs/2026-08-03-desktop-app-design.md`）
