# Desktop UI 补全 + y-monaco 协作接入计划

> **状态（2026-09-08 建）**：桌面 UI 重构（Phase 1 门户 + Phase 2 IDE 工作区）已完成骨架，但对照原型 `client/prototype/desktop-ui/` 仍有多处**结构性缺口**（聊天整页、通知面板、门户全局搜索、PR 创建 Modal、仓库设置 Tab、IDE 协作辅助栏）。逻辑层（Go 网关 + TS API + Zustand stores + WS socket）经盘点几乎全部就绪，缺口集中在 **UI 层（tsx）接线与渲染**。
>
> 另：协作编辑（F-204）已在服务端通过 **Hocuspocus collab-gateway 独立容器**落地（commit `d9f3981`），web 端已迁移 y-codemirror.next；desktop 的 Monaco **并行尝试 y-monaco 接入**（D1 决策延续）。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐 desktop 对照原型缺失的 UI（依赖排序：PR 创建 → 仓库设置 → 门户搜索 → 聊天全屏页 → 通知面板），并行推进 y-monaco 协作接入（走本地网关代理 collab）。优先接线**已就绪的逻辑层**，仅在确需处新增逻辑层代码。

**Architecture:**
- 逻辑层盘点结论（已核对代码）：`api/chat.ts`+`chatSocket.ts`+`stores/chat.ts`、`api/notifications.ts`+`stores/notifications.ts`、`api/search.ts`（IDE 本地工作区）+`stores/search.ts`、`api/pullRequests.ts`(`create`) 、`stores/myWork.ts`、Go `handlers_search.go`/`handlers_terminal.go`/`handlers_lsp.go` **均已实现** → 本计划以 **tsx UI 接线为主**，最少逻辑层增量。
- 例外（需新增逻辑层）：
  1. **仓库设置 Webhooks/协作者** API 层（desktop 尚无对应 `api/*.ts` 与 Go 代理端点）。
  2. **collab 网关代理**：Hocuspocus 的 token 在加密 message payload 内，现有 `wsEndpoint` 的 `?token=` 透传**不适用** → 需 Go 侧新增 collab-aware proxy（截获 HocuspocusProvider 首帧重建 token）。
- 聊天形态：独立全屏页（对齐 `chat.html`）+ IDE 活动栏入口两处；collab 直连路径复用现有 `/api/local/proxy/{serverId}` 本地网关。

**Tech Stack:** React + AntD + Zustand + i18next + Vite/Wails（desktop）；Monaco（IDE）+ @monaco-editor/react；yjs + y-monaco + @hocuspocus/provider（协作）；后端 FastAPI + Hocuspocus collab-gateway（不动）。

## Decision Log（2026-09-08 已确认）

| 决策 | 结论 | 备注 |
|------|------|------|
| 下一步重心 | 接缺失 UI（按依赖排序） | 逻辑层已就绪，缺口在 tsx |
| 聊天形态 | 独立全屏页 + IDE 活动栏入口 | 遵循原型 `chat.html` |
| 门户搜索 | 聚合搜索（仓库/Issue/PR） | 与 IDE 本地搜索区分 |
| 仓库设置 | 本批补 Webhooks + 协作者 | 新增 API 层（少数逻辑增量） |
| y-monaco | 并行尝试接入（非后置） | collab-gateway 服务端已就绪 |
| collab 接入 | 走**本地网关代理** | 见 Task 9 约束 |

## Global Constraints

- 深色风格常量沿用现有视图（`textPrimary:#e6edf3`、`bluePrimary:#1f6feb`、`blueLight:#58a6ff`、`borderColor:#21262d`），不引入新色板。
- 不做跨端共享包：`relativeTime`/`getInitials`/`getAvatarColor` 等在 desktop 各自局部实现。
- 聊天离线语义：消息本地入队、重连自动补发（`chatSocket` 已实现指数退避重连；UI 复用 socket 状态）。
- i18n key 同步维护 `zh.json` 与 `en.json`。
- 本地工作区仍为 desktop 独有能力：IDE 搜索走本地 `workspaceSearchApi`（不经服务器），门户聚合搜索才走服务器 proxy —— 两者并存不混。
- collab 端 awareness 用户字段与 web 端一致（`name`/`color`/`user_id`），`getText('content')` 共享文本名保持一致。
- 每个 Task 结束必须过 `npm run build`（`client/desktop/frontend`）并 commit。

---

### Task 1: PR 创建 Modal（最小体量收尾）

**Files:**
- Modify: `client/desktop/frontend/src/views/repositories/PullRequestsView.tsx`、`api/pullRequests.ts`（已含 `create`）
- Modify: `i18n/locales/zh.json`、`en.json`

**Interfaces:**
- Consumes: `usePullRequestsStore.createPullRequest(repoId, {title, description, source_branch, target_branch})`（store 已就绪，见 `stores/pullRequests.ts`）。
- Produces: PullRequestsView 顶部「New Pull Request」按钮（`PullRequestsView.tsx:103`）由死按钮改为打开 Modal 表单；提交后刷新列表。

- [x] **Step 1: 接线 Modal**

`PullRequestsView.tsx:103` 的 `<Button onClick>` 补 `setCreateOpen(true)`；新增 state `createOpen` + 表单字段（title 必填、description、source_branch、target_branch）。提交调 `createPullRequest(currentRepo.id, values)` → `message.success` → 关闭并刷新。

- [x] **Step 2: i18n key**

`desktop.pullRequests.newPRModal`（title/titleLabel/titleRequired/source/target/submit/cancel）双语。

- [x] **Step 3: build 验证 + Commit**

`npm run build`（`client/desktop/frontend`）通过后提交 commit `be24390`。

---

### Task 2: 仓库详情 settings Tab —— Webhooks + 协作者（逻辑层增量）

**Files:**
- Create: `client/desktop/frontend/src/api/repositorySettings.ts`、`views/repositories/RepositorySettings.tsx`
- Modify: `views/repositories/RepositoriesView.tsx`（`activeTab === 'settings'` 渲染）、`i18n`

**Interfaces:**
- Consumes: `useRepositoriesStore.currentRepo`、`useServersStore`.
- Produces: 新增 desktop API 层：`webhooks`（list/create/delete）/`collaborators`（list/add/remove），经 `proxyRequest`；`RepositorySettings` 视图含两个分区（Webhooks CRUD + 协作者增删）。

- [x] **Step 1: 新增 API 层**

`api/repositorySettings.ts`，参考后端既有端点（web 端 `api/settings.ts` 语义），全部 `proxyRequest` 化（serverId 前置）。
> **前置核对**：确认后端已暴露 webhooks/collaborators 端点；若缺，需先在后端补（该增量留待确认后单列）。
> 前置核对结论：`controller/webhook_controller.py`（`/api/v1/repositories` 前缀：GET/POST/PATCH/DELETE webhooks + POST `/test` + GET `/deliveries`）、`controller/repository_member_controller.py`（GET/POST/PUT/DELETE members + PUT `/role` + activate/deactivate）均已存在，无需后端新增。`listWebhooks` 兼容分页 `{items}` 与裸数组两种响应；协作者添加使用 `GET /api/v1/users` 列表做用户下拉。

- [x] **Step 2: 写 RepositorySettings 视图**

`RepositorySettings.tsx`：Tabs「Webhooks / 协作者」；Webhooks 列表 + 新建（url/secret/events）+ 删除；协作者列表 + 添加（username/role）+ 移除。破坏性操作二次确认。
> 事件全集取自 `models/webhook.py::WEBHOOK_EVENTS`（18 个事件）；角色集合 `owner/admin/developer/readonly`；新增 root 事件徽标或 Tag 样式沿用现有设计语言。

- [x] **Step 3: 接线 RepositoriesView**

`RepositoriesView.tsx` 的 `tabItems` 已含 `settings`（line 454），在 `Content` 内 `activeTab === 'settings'` 渲染 `<RepositorySettings repoId={currentRepo.id} />`。

- [x] **Step 4: build 验证 + Commit**

`npm run build` 通过后提交 commit `de0bf39`。

---

### Task 3: 门户全局聚合搜索（仓库/Issue/PR）

**Files:**
- Create: `client/desktop/frontend/src/views/GlobalSearchView.tsx`（或 Modal）
- Modify: `layouts/PortalShell.tsx`（`PortalShell.tsx:190` 死按钮接线）、`i18n`

**Interfaces:**
- Consumes: 现有 `repositoriesApi`/`issues`/`pullRequests` 的 proxyRequest（聚合语义对齐 web 端 `/search` 聚合；若 desktop 无聚合端点则前端并发三接口本地合并）。
- Produces: PortalShell 标题栏搜索框触发聚合搜索 UI（Modal/下拉），展示仓库/Issue/PR 三类分组结果，点击跳转对应详情（仓库→`openRepo`、Issue/PR→仓库详情对应 Tab）。

- [x] **Step 1: 写聚合视图**

`GlobalSearchView.tsx`：输入触发防抖查询；三分类分组合并；点击导航。
> **前置核对**：后端是否已有聚合搜索 API；若无，前端并发 `repositoriesApi.list` + issues/PR 列表本地筛选合并。
> 前置核对结论（2026-09-10）：后端**无**仓库/Issue/PR 聚合端点（`/api/v1/search/code` 仅代码搜索；Issue `search` 仅 per-repo filter；PR 列表无关键词参数），前端本地合并受 N+1 请求与分页截断限制 → **采用后端增量**：新增 `GET /api/v1/search/global`（`search_controller.py`，DB 层 ilike 三表查询 + `get_accessible_repository_ids` 权限过滤，`per_type` 限流），web 端后续可复用。7 例后端测试（`TestGlobalSearchAPI`）于 WSL docker 测试容器通过。

- [x] **Step 2: 接线 PortalShell**

`PortalShell.tsx` 搜索死按钮改为打开 `GlobalSearchView` Modal；结果点击经 `useRepositoriesStore.pendingOpen` 深链（`RepositoriesView` 消费：按 path 拉取仓库 → 定位 `issues`/`pullRequests` Tab → 打开对应 Issue/PR 详情）。

- [x] **Step 3: build 验证 + Commit**

`npm run build` 通过后提交。

---

### Task 4: 团队聊天 —— 独立全屏页 + IDE 活动栏入口

**Files:**
- Create: `client/desktop/frontend/src/views/chat/ChatView.tsx`（三栏：频道/私信 · 会话 · 成员）
- Modify: `stores/chat.ts`（补房间获取聚合，如 `fetchChatRooms`）、`layouts/PortalShell.tsx`（注册 `chat` 视图 + CRUMB）、`stores/navigation.ts`（`PortalView` 增 `'chat'`）、`layouts/IdeShell.tsx:225-230`（chat 活动栏面板真接线）、`api/chat.ts`（按需补 `listRooms`）
- Add deps: `@monaco` 无关；聊天 Markdown 渲染若需可引 `react-markdown`（按需评估）

**Interfaces:**
- Consumes: `chatApi`（`getRoomMessages`/`getRoomMembers`/`getRepositoryRoom`/`getUnreadCounts`/`markRead`/`addReaction`/`uploadAttachment`）+ `chatSocket`（消息/ack/presence/typing/reaction）+ `useChatStore`.
- Produces:
  - 全屏聊天视图（对齐 `chat.html`）：频道/私信侧栏、消息流（Markdown + 代码片段 + reactions + typing 指示）、成员面板、composer（附件/表情/发送）。
  - IDE 活动栏「聊天」入口打开真实聊天面板（替换 `IdeShell.tsx:225-230` 的 `phase2` 占位）。

- [x] **Step 1: ChatView 组件骨架**

仿 `chat.html` 三栏布局（频道 240 / 会话 / 成员 220）+ `useChatStore` 渲染房间/消息/成员；频道列表对齐 web 端语义 = 用户仓库列表，点击 `openChannel(repoId)`（服务端按仓库访问权限 auto-join）。共享件拆分：`ChatMessages.tsx`（Markdown + reactions + typing + 日期分组 + 本人删除）、`ChatComposer.tsx`（附件/表情/Markdown 工具条/Enter 发送，断连禁用）。

- [x] **Step 2: store 补房间聚合**

`stores/chat.ts`：`fetchChatRooms()` = 后端 `GET /api/v1/rooms`（`RoomService.list_rooms` 既有服务端实现补暴露 REST，2 例测试通过）+ `fetchUnread` 按 `repository_id` 映射 `unreadByRepo`；另补 `typingByRoom`/`onlineUsers`（presence 全套）、`toggleReaction`/`pickReaction`/`deleteMessage`、`reset()`（切服务器清态）；修复 `fetchMessages` 倒序返回未反转问题。

- [x] **Step 3: 注册为 Portal 独立视图**

`navigation.ts` `PortalView` 增 `'chat'`；`PortalShell.tsx` switch 增 case（无服务器时空态）+ CRUMB_KEYS；入口：Welcome 新增「团队聊天」动作卡；切服务器时 `resetChat`。

- [x] **Step 4: IDE 活动栏 chat 面板真接线**

`IdeShell.tsx` 占位改为 `ActivityChatPanel`（房间下拉 + 精简消息流 + composer），clone 工作区按 `remote_url` 尾段自动匹配来源仓库房间；socket 常驻不随切 Tab 销毁（对齐终端语义）。

- [x] **Step 5: build 验证 + Commit**

`npm run build` 通过（新增 `react-markdown`+`remark-gfm`，pnpm）后提交 commit `842315b`。

---

### Task 5: 通知面板

**Files:**
- Create: `client/desktop/frontend/src/views/notifications/NotificationsPanel.tsx`（下拉/抽屉）
- Modify: `layouts/PortalShell.tsx`（`PortalShell.tsx:199` 死按钮接线）

**Interfaces:**
- Consumes: `notificationsApi`（`list`/`markAsRead`/`markAllAsRead`/`delete`/`preferences`）+ `stores/notifications.ts`.
- Produces: 标题栏通知铃铛点击打开面板（列表/未读状态/全部已读/跳转到对应仓库或 issue/PR）。

- [x] **Step 1: 写面板组件**

`NotificationsPanel.tsx`：标题栏铃铛 Popover 下拉面板；未读徽标计数、全部已读、单条删除（hover）、点击跳转（语义对齐 web `AppLayout.handleNotificationClick`：target_type 含 pr/pull → PR Tab、issue → Issues Tab、其余 → 仓库，经 `repositoriesApi.get` 解析 path 后复用 `pendingOpen` 深链）。

- [x] **Step 2: 接线 PortalShell**

`PortalShell.tsx` 铃铛 `onClick={phase2}` 占位移除 → `Popover(trigger=click)` 包裹；`phase2` 死占位在 PortalShell 中全部清零。

- [x] **Step 3: build + Commit**

`npm run build` 通过后提交 commit `a4d00e6`。

---

### Task 6: 我的工作 — ✅ 已完成（2026-09-10，commit `21d1716`）

**Files:**
- Create: `client/desktop/frontend/src/views/MyWorkView.tsx`
- Modify: `navigation.ts`、`PortalShell.tsx`、`Welcome.tsx`（入口动作卡）、`i18n`

**Interfaces:**
- Consumes: `stores/myWork.ts`（`fetchMyPullRequests`/`fetchMyIssues` 已就绪）.
- Produces: 聚合「我发起的 PR / 分配的 Issue」视图，跳转到仓库详情对应 Tab。

> 落地：PR/Issue 双 Tab + 状态筛选（open/closed/all，all 不传参）；行点击经 `repositories` store 映射 `repository_id→path` 后复用 `pendingOpen` 深链直达对应 Issue/PR 详情。Welcome 新增「我的工作」入口。

---

### Task 7: IDE 协作辅助栏（aux/collab）— ✅ 已完成（2026-09-10，commit `19587ee`）

**Files:**
- Create: `views/workspace/CollabAuxPanel.tsx`、`hooks/useWorkspaceChatRoom.ts`
- Modify: `layouts/IdeShell.tsx`（标题栏切换按钮 + 右侧 aux）、`views/chat/ActivityChatPanel.tsx`（复用 hook）、`i18n`
- Consumes: `useChatStore`（成员/presence）+ 后续 Task 9 collab awareness.

**Interfaces:**
- Produces: 对齐 `ide.html` 右侧「协作：待处理 PR / 相关 Issue / 成员在线」辅助栏（`aux`），接线现有 PR/Issue 快速列表 + chat presence。

> 落地：标题栏 TeamOutlined 切换按钮；`useWorkspaceChatRoom` hook 抽取工作区→房间关联（ActivityChatPanel 同步复用，消除重复）；PR/Issue 经 `useWorkspaceRepo` 限定当前仓库，presence 来自活跃房间 `onlineUsers`。

---

### Task 8: （预留）仓库详情 Releases/Builds

> 依赖后端既有端点；因而 port-sync 仍计为待排期项，不在本批强制范围。若仓库设置 Tab 复用结构可直接扩展。

---

### Task 9: y-monaco 协作接入（Go 代理 + Monaco 绑定）

**Files:**
- Create:
  - Go: `client/desktop/internal/gateway/handlers_collab.go`（collab-aware WS 代理）
  - TS: `client/desktop/frontend/src/api/collabSocket.ts`（HocuspocusProvider 封装，参照 web `collabController.ts`）
  - TS: `client/desktop/frontend/src/components/editor/CollabMonaco.tsx`（y-monaco 绑定）
- Modify: `client/desktop/frontend/src/package.json`（+`yjs`、`y-monaco`、`@hocuspocus/provider`）、`views/workspace/EditorTabs.tsx`（可协作文件挂 CollabMonaco）
- Add tests: Go `handlers_collab_test.go` + TS 冒烟

**Critical constraint（collab 代理 token 注入）：**
- 现有 `wsEndpoint`（`internal/gateway/ws.go:150`）用 `?token=` 透传，**仅适用于 chat 类 WS**。
- Hocuspocus 鉴权走 `onAuthenticate` 回调 + **连接 message 内加密 token**，本地网关无法像 `?token=` 那样注入。
- → 需 Go 侧新增 `handlers_collab.go`：截获 `HocuspocusProvider` 首帧（connection message）→ 以密钥库 app access token 重建 message → 转发到 collab-gateway `/ws/collab`（经服务器地址的 nginx 分流）。
- **开工前必做**：核对 `@hocuspocus/provider` 连接消息格式（`ClientMessageSyncStep1`/鉴权字段），确认可改写 payload。此为全计划**技术风险最高**项，宜作为独立小里程碑先行 spike 验证。

**Interfaces:**
- Consumes: HocuspocusProvider（url=本地网关 collab 代理、name=docKey `{repoId}:{branch}:{path}`、token=网关鉴权）；`collab-gateway` 内部回调（/auth、/doc、/save）由服务端处理，desktop 不感知。
- Produces: Monaco 内 yMonaco(ydoc.getText('content'), awareness)；本地编辑通过 awareness 光标渲染远端参与者；显式保存 `sendStateless({type:'collab-save'})`；只读用户由网关强制。

- [x] **Step 0（spike，2026-09-08 已验证通过）**: 核对 Hocuspocus 连接消息格式，验证 Go 代理改写 token 可行性。**结论：可行，token 位于确定的二进制偏移，Go 需实现 lib0 varint/varstring 编解码（约 100 行）。**
  - 已确认连接时序（`HocuspocusProvider.onOpen`）：先 `sendToken()` 发 **AuthenticationMessage**（首帧），再 `startSync()` 发 SyncStepOneMessage + AwarenessMessage。
  - AuthenticationMessage lib0 二进制帧格式（`AuthenticationMessage.ts` + `@hocuspocus/common/auth.ts`）：
    ```
    writeVarString(documentName)          // lib0 变长字符串（长度前缀 + UTF-8）
    writeVarUint(MessageType.Auth = 2)    // Hocuspocus 消息类型字节
    writeVarUint(AuthMessageType.Token = 0) // auth 子类型（token 请求）
    writeVarString(token)                 // ← JWT 明文，改写点
    writeVarString(version)               // 协议版本字符串（编译期注入，如 "4.6.0"）
    ```
  - token 为 ASCII JWT，无多字节游走问题；仅需实现 lib0 `read/write VarUint` + `VarString` 即定位改写。
  - 实测证实 Hocuspocus 对**格式不匹配的帧静默忽略**（无响应/无日志）：JSON `{type:"connect"}` 和 MessageType 误用 0 的二进制帧均被丢。安全性好（无信息泄漏），但要求代理**必须精确重建帧字节**（varint 重新编码长度，不能只改字节不重算前缀）。
  - 反向印证：向 collab-gateway 发送 JSON `{type:"connect",...}` 首帧被静默忽略（Hocuspocus 只认 lib0 二进制），证明 token 注入**只能**在二进制 Auth 帧内完成，`?token=` URL 透传必然无效（与计划 Critical constraint 一致）。
  - **全链路端到端实证**（app 容器经 `ws://collab:4444`）：发送精确 lib0 Auth 帧（`docName + varuint(2) + varuint(0) + token="" + version="4.6.0"`）→ collab 日志 `[onAuthenticate] 无效或过期的 token` → 服务器回写 `PermissionDenied` 帧（docName + varuint(2)/Auth + varuint(1)/PermissionDenied + utf8 "无效或过期的 token"）。整条 client→Hocuspocus→app `/api/v1/collab/auth`（X-Collab-Internal-Secret）→PermissionDenied 链路可用；注入密钥库真实 app token 即可得 `Authenticated`（Auth + varuint(2)/Authenticated + scope）并放行。
  - dev 编排（`docker-compose.dev.yml`，project `perseus-devt`，WSL 隔离）已拉起并验证：app(8000)+collab(4444/4445 Hocuspocus v4.6.0)+gateway(127.0.0.1:8080)+git-cgi；`PERSEUS_COLLAB_INTERNAL_SECRET` 内部回调密钥已生效。
  - 实现指引：`handlers_collab.go` 首个客户端帧解析→密钥库取 app access token→替换 `token` 字段→转发出站 ws 连接；其余帧透明双向转发。
- [ ] **Step 1**: Go `handlers_collab.go` 代理（首帧改写 + 双向转发 + 重连）。
- [ ] **Step 2**: TS `collabSocket.ts` 封装 provider。
- [ ] **Step 3**: `CollabMonaco.tsx` y-monaco 绑定 + 协作状态栏（participants/pending）。
- [ ] **Step 4**: 接线 `EditorTabs.tsx`（哪些文件可协作：本地工作区文件与远端仓库文件关联时；初始限定已 clone 到工作区且对应远端仓库存在的文件）。
- [ ] **Step 5**: build + go test + commit。

---

### Task 10: 全量验证 + README/同步清单回填

**Files:**
- Modify: `client/desktop/README.md`、`docs/desktop-port-sync.md`、`docs/superpowers/plans/2026-09-07-desktop-decisions.md`（如适用）

**Interfaces:**
- Consumes: Task 1-9 全部产物.

- [ ] **Step 1**: desktop `npm run build` + `go build ./...` + `go test ./...` 全绿。
- [ ] **Step 2**: README 新增「UI 补全范围」小节。
- [ ] **Step 3**: 回填 `desktop-port-sync.md` 状态（聊天/通知/全局搜索/PR创建/仓库设置 → ✅/状态）。

---

## Self-Review Notes

- **Spec 覆盖**：PR 创建（T1）、仓库设置（T2）、门户搜索（T3）、聊天全屏+IDE（T4）、通知（T5）、我的工作（T6）、IDE 辅助栏（T7）、y-monaco 协作（T9）、验证回填（T10）。Releases/Builds（T8）与 mDNS/托盘/NSIS（D4/Phase4）不在本批。
- **逻辑层先行的印证**：T1（`pullRequests.create` 已就绪）、T4（`chatSocket`/`chat store` 全就绪）、T5（`notifications store` 就绪）、T6（`myWork store` 就绪）均为**纯 UI 接线**；唯一逻辑层增量是 T2（仓库设置 API）与 T9（collab 代理）。
- **collab 风险**：T9 是全计划唯一高风险项，已前置 spike（Step 0）并标注「collab-aware proxy」与 chat `?token=` 的机制差异，避免误用现有透传。
- **无占位**：所有组件/方法在对应 Task 给出一等实现或明确降级路径（T6 可选、T8 预留）。
