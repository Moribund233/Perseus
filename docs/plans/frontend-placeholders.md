# 前端占位实现清单与开发规划

> **更新日期**: 2026-09-18（回填 F-602 Discussions、F-604 文件移动/重命名、Landing「Docs」链接失效；批次 H 接线：参与者未保存徽标、PR 审阅者头像堆叠、聊天单会话检索范围切换；仅剩亮色主题）
> **背景**: 前端多处 UI 为占位/装饰实现（无 onClick 的按钮、硬编码 mock 数据、假状态）。
> 本文档梳理**尚未真实化**的占位点，作为后续迭代规划依据。
>
> **已完成批次**（参见 git log）:
> - 2026-08-29 第一批：Chat Markdown 渲染、附件上传/表情/格式化按钮、Editor 保存链路/新建文件/Markdown 预览、
>   Dashboard 活动流/贡献图/统计卡真实化、Settings 通知偏好/头像上传、顶栏 New 建仓库、
>   PR 列表新建弹窗、PR 标签序列化 + 懒加载 500 修复、假 badge/假统计兜底清理
> - 2026-08-29 批次 A（接线冲刺）：通知点击跳转（按 target_type 导航到仓库 PR/Issue）、
>   Chat 消息删除（本人 hover 删除）、Editor 文件删除（hover 删除 + 确认弹窗）、
>   PR 详情标签管理（拉取/添加/移除）、PR 编辑（标题/描述）、PR Review 提交（Approve/Request changes/Comment）
> - 2026-08-29 批次 B（仓库能力页）：Releases tab（列表/创建/编辑/删除/草稿）、Actions tab 接 Builds（列表/状态筛选/日志）、
>   仓库 Settings tab（描述/可见性/默认分支 + 协作者管理 + Webhooks CRUD/测试/投递记录）
> - 2026-08-31 批次 C（用户中心）：Settings「安全」tab（SSH Keys 增删 + OAuth 账号解绑）、
>   Dashboard「我的 PR / Issues」跨仓库聚合、顶栏全局搜索（防抖下拉 + /search 结果页 + Editor 行号跳转）
> - 2026-08-31 批次 D（实时增强）：聊天/Editor 在线状态接 WS presence（list/join/leave）、
>   聊天频道未读数徽标（后端 `GET /rooms/unread` + `POST /rooms/{id}/read`，RoomMember.last_read_at 水位）
> - 2026-09-16 批次 E（体验完善）：消息 reactions UI 接线确认（前端已实现：emoji picker + WS 即时增减 + REST 兜底）、
>   聊天消息按日期分组（Today/Yesterday/日期头）、编辑器面包屑点击跳转（目录段钉出浮动面板 + 根段回根文件树）、
>   文件树 last-commit 列全层级接线（任意层级请求 `last_commit=true`）、PR Filter 装饰按钮移除 + unused i18n key 清理

---

## 一、优先级说明

| 级别 | 含义 |
|---|---|
| P1 | 后端 API 已就绪，仅缺前端接线（低成本高收益） |
| P2 | 前后端都需少量开发 |
| P3 | 需要新后端能力（存储/推送/聚合），工作量较大 |
| P4 | 暂无规划价值，建议保持现状或移除 |

---

## 二、整模块未接线（后端 API 全部就绪，仅缺 UI）

> 这三块是"接线即用"，优先级最高。

### 2.1 Releases（发行版）— ✅ 已完成（批次 B）

- **后端**: `release_controller.py` 已实现 list/get/getByTag/create/update/delete
- **前端**: 仓库页 Releases tab（`components/repo/ReleasesTab.tsx`）：列表 + 创建/编辑/删除 + 草稿/预发布

### 2.2 Webhooks（Web 钩子）— ✅ 已完成（批次 B）

- **后端**: `webhook_controller.py` 已实现 8 个路由（CRUD/test/listDeliveries/getDelivery）
- **前端**: 仓库 Settings tab 内 Webhook 区块（`components/repo/RepoSettingsTab.tsx`）：CRUD + 测试 + 投递记录

### 2.3 Builds / CI（构建）— ✅ 已完成（批次 B）

- **后端**: `build_controller.py` 已实现 list/get/create/getLogs；PR 合并后自动创建 Build（F-046）
- **前端**: 仓库页 Actions tab（`components/repo/BuildsTab.tsx`）：构建列表 + 状态筛选 + 日志查看

### 2.4 用户中心类 API — ✅ 已完成（批次 C）

`api/settings.ts` 中的封装全部接入 UI：

| 方法 | 后端 | 落地 |
|---|---|---|
| `listSSHKeys / addSSHKey / deleteSSHKey` | `key_controller.py` | Settings「安全」tab（`components/settings/SecuritySettings.tsx`）：添加表单 + 列表（fingerprint）+ 删除（确认弹窗） |
| `listOAuthAccounts / unlinkOAuth` | `oauth_controller.py` | 同上「安全」tab 内 OAuth 账号卡片：列表 + 解除绑定 |
| `getUserPullRequests / getUserIssues` | `user_controller.py /me/*` | Dashboard「我的 PR / Issues」卡片（`components/dashboard/MyWork.tsx`）：跨仓库聚合 + PR/Issues 切换 + 点击跳转详情 |

---

## 三、按页面的剩余占位点

### 3.1 顶栏 / 全局（AppLayout）

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| 全局搜索框 ✅ | ✅ 已接线（2026-09-14 对齐 desktop T3）：受控输入 + 350ms 防抖 → **并行 `searchCode` + `searchGlobal` 聚合**（`/api/v1/search/global`，仓库/Issue/PR 三类分组）——下拉与 `/search` 结果页均为聚合视图；Enter 进 `/search` 结果页 | — | ✅ P2 完成 |
| 通知点击跳转 | ✅ 已按 `target_type` 映射路由（PR→pulls / Issue→issues / 其余→仓库），解析 repository_id→path | — | P1 |
| 侧边栏未读徽标 ✅ | 已移除假数字（本批） | **已恢复（2026-09-18）**：复用既有无读聚合端点 `GET /api/v1/rooms/unread`（频道）+ `GET /api/v1/dm`（私聊 unread_count）求和，`AppLayout` 每 60s 轮询 + 路由变化刷新，「团队聊天」nav 项显示聚合徽标；静音会话由后端排除，不参与聚合 | ✅ P3 完成 |

### 3.2 仓库页（repositories/index.tsx）

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| Watch 按钮 | ✅ 已接线（2026-09-16）：`handleWatchToggle` + `getWatchStatus`，后端 `POST/DELETE/GET /{repo_id}/watch` + `watch_count` | — | ✅ P3 完成 |
| Actions tab | ✅ 已接 Builds 列表 + 日志（批次 B） | — | P1 |
| Settings tab | ✅ 已实现仓库设置子内容：描述/可见性/默认分支、协作者管理、Webhooks（批次 B） | — | P1~P2 |
| 文件列表"最近提交/时间"两列 | 写死 `-` 和空白 | ✅ 已接线：任意层级文件树请求 `last_commit=true`，root 顶层曾只对根目录附加（批次 E） | ✅ P1 完成 |

### 3.3 团队聊天（chat/index.tsx）

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| 顶栏 Eye/Search/More 三按钮 ✅ | — | **全部接线完成（2026-09-18）**：Eye＝右侧成员面板显隐切换（复用 WS presence 在线成员）；Search＝聚焦侧栏消息检索框；More＝下拉菜单（频道信息与成员 → Drawer：房间类型/成员数/未读/静音开关，成员列表含在线点与静音标记；静音会话 → 后端新增 `POST /api/v1/rooms/{room_id}/members/me`，`set_member_muted` 落库，静音后 `GET /rooms/unread` 与 DM 未读均排除）；i18n 已补 zh/en | — | ✅ P3 完成 |
| 消息删除 | ✅ 已加本人 hover 删除按钮 + 确认，调用 `chatApi.deleteMessage` | — | P1 |
| DM 私聊列表 | ✅ 已接（2026-09-18）：侧栏 DM 列表 `GET /api/v1/dm` 真数据（peer/未读/在线），点击打开会话；右侧成员点击发起私聊（`POST /api/v1/dm` 幂等创建）；消息收发复用 `GET/POST /rooms/{room_id}/messages` + WS 房间广播 | — | P1 ✅ |
| 成员在线状态 | ✅ 已接 WS presence：进入房间 `presence_list` + join/leave 实时增删（批次 D） | — | P1 |
| 频道未读数 | ✅ 已接后端 `GET /rooms/unread`（按 repository_id 映射频道）+ 进频道 `POST /rooms/{id}/read`（批次 D） | — | P1 |
| 表情回应 reactions | UI 死代码（渲染逻辑存在，数据恒空） | ✅ 已接线（2026-09-16 确认前端早已实现）：emoji picker + WS `send_reaction` 增减 + REST `chatApi.addReaction` 兜底；后端 `chat_controller.py:62-83`、`chat_service.py:228` add_reaction 已就绪 | ✅ P1 完成 |
| 消息按日期分组 | 所有消息归入 "Today" | ✅ 按 created_at 分组渲染：Today/Yesterday（新增 i18n）/本地化日期头，静态 Today 块移除（批次 E） | ✅ P2 完成 |
| 侧边栏搜索框 | ✅ 已接（2026-09-18）：`GET /api/v1/messages/search?q=` 300ms 防抖 + 结果下拉（发件人/会话名/时间/内容摘要），点击跳转对应频道或私聊；**「全部会话 / 本会话」范围切换**（本会话走 `GET /rooms/{id}/messages?q=`） | — | P2 ✅ |

### 3.4 Editor（editor/index.tsx）

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| 协同编辑 | ✅ 已实现并迁移 **Yjs 底座**（2026-09-08，D1）：`components/editor/collabController.ts` 接入 `collab-gateway`（Hocuspocus）+ `y-codemirror.next`；远端光标/选区（awareness 标签）+ 协作保存（stateless → 网关 → Git commit 全员广播）+ **断线本地编辑保留**（CRDT 重连收敛，3.6 方案 B 天然解决）；**邀请链接（2026-09-16，M2）**：工具栏「分享协作」生成会话级临时权限链接（仅成员），`?invite=` 经 JSON token 透传网关；**会话 TTL 延迟销毁（2026-09-17）**：最后一人离开后保留内存 Y.Doc 至多 10 分钟（`PERSEUS_COLLAB_SESSION_TTL_MS`），TTL 到期卸载，下次 join 重新播种；**双态徽标（2026-09-14 web / 09-18）**：状态栏「会话已同步/同步中」轮询 `hasUnsyncedChanges` + 「Git 已提交 {short-SHA}」由 `onSaved` 收 `collab-saved` 的 `commit_id` 填充；**「版本 N」✅ 2026-09-18**：「会话已同步 · v{N}」由广播 `version` 驱动（网关 `collab-gateway/versionCounter.mjs`，Redis INCR 持久计数 / 无 Redis 回退内存） | 不支持离线合并（页面关闭即丢，与旧版一致） | P2 |
| Discussions 面板 | ✅ 已接线（2026-09-18，F-602）：web `discussions.ts` + 标签文件/回复/解决/重开/删除/跳转行/未读数徽标；desktop `DiscussionsPanel.tsx` 右侧面板（文件级线程/回复/解决/删除/跳行） | 后端已就绪（2026-09-17）：`FileComment`（文件+行号/分支/提交锚定）+ `/api/v1/repositories/{repo_id}/discussions`（创建/列表/回复/解决/删除） | ✅ P3 完成 |
| 协作者 "viewing" 状态 | ✅ 已接 WS presence：在线协作者列表即 Editors tab 内容（批次 D）；本文件会话参与者经 `collab_init`/peer 事件展示（F-204） | — | P3 |
| "Online" 绿点 | ✅ 已接房间 presence（在线人数 > 0 亮绿）（批次 D） | — | P2 |
| 面包屑点击 | cursor:pointer 无跳转 | ✅ 已接线（批次 E）：目录段点击加载该目录并钉出浮动面板（对齐文件树点位），根段点击回根文件树（清选中与面板链） | ✅ P2 完成 |
| 文件删除入口 | ✅ 已加文件树 hover 删除按钮 + 确认弹窗，调用 `deleteFileContent`，删除后刷新树并关闭对应标签 | — | P1 |
| 文件重命名/移动 | ✅ 已接线（2026-09-18，F-604）：web 文件树 hover 移动/重命名（主树+浮动面板）→ `POST /contents/move`；desktop 本地工作区 `POST /api/local/workspaces/{id}/rename` + ExplorerPanel Modal | ✅ 后端 move 端点已就绪（2026-09-16，`POST /{repo_id}/contents/move` 单次提交 copy+delete） | ✅ P3 完成 |

### 3.5 Pull Requests

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| Filter 按钮 | 无 onClick | ✅ 已移除装饰按钮（批次 E），筛选由状态按钮组完成，unused i18n key 一并清理 | ✅ P4 完成 |
| 审阅者头像堆叠 | ✅ 已接线（2026-09-18）：后端列表响应新增 `reviewers`（`build_pr_response(include_reviewers=True)`，预加载 reviews.reviewer）；web/desktop PR 列表头像堆叠显示 作者+审阅者（去重、最多 4） | PR 详情 Review 提交区（Approve/Request changes/Comment） | ✅ P2 完成 |
| PR 编辑 | ✅ 已加标题/描述编辑入口 | — | P2 |
| PR 标签 UI | ✅ 已加标签管理下拉（拉取/添加/移除） | — | P1 |

### 3.6 Settings

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| 主题切换 | 已移除假 Radio（应用固定 dark） | 若支持亮色主题，需全站 CSS 变量化，工程量大；建议暂不恢复 | P3 |
| 语言持久化 | `i18n.changeLanguage` 即时生效 | localStorage 已由 i18next-browser-languagedetector 处理，无需额外工作 | — |

### 3.7 Landing（未登录页）

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| 统计兜底假数字 | 已改为 `--`（本批） | — | 完成 |
| "Docs" 导航链接 | ✅ 已不存在：landing 导航项改为 功能/协作/进入控制台（锚点或路由），无空 `<a>` | — | ✅ 失效 |
| 页脚 About/Privacy/Terms/GitHub | 均无 href | 补静态页或外链 | P4 |
| "协作"区可视化 | 纯装饰（假窗口/假代码条/假头像） | 营销视觉，可保留 | P4 |

---

## 四、建议迭代批次

| 批次 | 内容 | 预估 |
|---|---|---|
| **批次 A（接线冲刺）** ✅ | 通知点击跳转、消息删除、文件删除、PR 标签 UI、PR 编辑、PR review 提交 — **已完成** | — |
| **批次 B（仓库能力页）** ✅ | Releases tab（2.1）+ Actions/Builds tab（2.3）+ 仓库 Settings tab（含 Webhooks 2.2、协作者、默认分支）— **已完成** | — |
| **批次 C（用户中心）** ✅ | SSH Keys、OAuth 账号管理、`/me/*` 聚合展示（2.4）；全局搜索（3.1）— **已完成** | — |
| **批次 D（实时增强）** ✅ | Editor 在线状态（3.4）、聊天 presence/未读数（3.3）— **已完成**（presence 复用原 WS 基础设施，未读数新增 REST 端点） | — |
| **批次 E（体验完善）** ✅ | 消息 reactions UI（确认已实现，仅回填）、文件树 last-commit 列全层级接线、聊天按日期分组、编辑器面包屑点击跳转、PR Filter 装饰按钮移除 — **已完成（2026-09-16）** | 后端早已就绪，纯前端 + 文档 |
| 待排期 | ~~DM 私聊、行内评论、消息搜索 — desktop 待跟进~~ → **web/desktop 均已接线（2026-09-18）**；亮色主题 | 亮色主题工程 |

---

## 五、批次 F：后端就绪待接线清单（2026-09-17 规划）

> 依据 2026-09-17 后端复核（`1191 passed / 3 skipped`，含 API 契约测试）与前端代码库现状盘点。
> 下列能力后端 API 已就绪，前端（web 优先，desktop 跟进）仅需接线。

### 5.1 接线项总表

| ID | 任务 | 后端端点（已就绪） | web 现状 | desktop 现状 | 级别 |
|----|------|-------------------|----------|--------------|------|
| F-601 | DM 私聊 | `POST/GET /api/v1/dm` | ✅ 2026-09-18：`chat.ts` 封装 `dmApi`；侧栏私聊列表接 `GET /api/v1/dm`（含未读徽标/在线点），点击打开会话（复用房间消息/WS）；成员点击发起私聊（无会话时 `POST /api/v1/dm` 幂等创建） | ✅ 2026-09-18：同 web（`api/chat.ts` dmApi + ChatView 侧栏 DM 列表/成员行发起私聊，ActivityChatPanel 并入 `@ peer` 选项） | P1 |
| F-602 | 行内评论 Discussions | `/api/v1/repositories/{repo_id}/discussions` CRUD | ✅ 2026-09-18：`discussions.ts` 封装（list/create/resolve/remove）+ 标签文件/回复/解决/重开/删除（作者或仓库 admin）/跳转行/未读数徽标 | ✅ 2026-09-18：IDE 右侧面板（EditorTabs 评论按钮开合）；`api/discussions.ts` 经网关 proxy；`DiscussionsPanel.tsx` 文件级线程/回复/解决/删除/跳行，新建评论锚定当前光标行 + 工作分支（`useWorkspaceRepo`） | P2 |
| F-603 | 消息检索 | `GET /api/v1/messages/search`、`GET /rooms/{id}/messages?q=` | ✅ 2026-09-18：侧栏搜索框接 `GET /api/v1/messages/search`（300ms 防抖 + 结果下拉，点击跳转对应房间/私聊）；顶栏 Search 按钮聚焦搜索框 | ✅ 2026-09-18：同 web（ChatView 顶部搜索框 + 结果下拉，命中跳转频道/DM） | P2 |
| F-604 | 文件重命名/移动 UI | `POST /api/v1/repositories/{repo_id}/contents/move` | ✅ 2026-09-18：文件树行 hover 移动/重命名按钮（主树 + 浮动树面板），弹窗填目标路径与提交信息，成功后刷新树并迁移已打开 tab | ✅ 2026-09-18：本地工作区走新增 `POST /api/local/workspaces/{id}/rename`（TDD `TestWorkspaceRename`；ExplorerPanel 重命名 Modal + 树行 hover 按钮，FloatingTreePanel `onRename` 透传） | P2 |
| F-605 | 协作邀请 desktop 跟进 | `POST .../collab/invites` | ✅ 已完成（编辑器分享按钮） | ✅ 2026-09-18：编辑器 crumbs 分享按钮生成邀请链接（`?invite=`，格式与 web 一致）并复制剪贴板（`desktop/frontend .../workspace/EditorTabs.tsx` + `repositoriesApi.createCollabInvite`） | P2 |
| F-606 | 会话空闲自动落盘前端计时 | `/collab/save` 草稿分支已就绪 | ✅ 2026-09-18：web 编辑器连续 5 分钟无编辑且存在未保存内容 → 经协作会话触发草稿保存（`draft=true`，落 `collab/draft-{branch}`，不触碰工作分支）；网关转发 `draft` 标志；无协作会话时不自动提交 | 无（本地 fs 替代） | P3 |
| F-607 | 跟随模式（Follow me） | Awareness `viewport`/`follow` + stateless `collab-spotlight`（✅ 后端 2026-09-17） | ✅ 2026-09-17：web — 参与者列表点选跟随/停止、工具栏"跟我来"（写权限）、状态栏跟随指示；desktop — CollabMonaco 跟随菜单/跟我来/跟随指示，`viewport` 以字符偏移与 web 同单位可互跟 | 无 | P2 ✅ |

### 5.2 接线顺序建议

1. **批次 F1（聊天增强）**：F-601 DM 私聊 + F-603 消息检索（同一 `chat.ts` 模块，UI 相邻）— **web ✅ 2026-09-18 / desktop ✅ 2026-09-18**
2. **批次 F2（编辑器增强）**：F-602 Discussions + F-604 文件移动 UI — **web ✅ 2026-09-18 / desktop ✅ 2026-09-18**（desktop 文件重命名走本地 `POST /api/local/workspaces/{id}/rename`）
3. **批次 F3（跨端对齐）**：F-605 desktop 邀请入口 + F-606 空闲落盘计时 — **✅ 2026-09-18**（F-605 desktop 落地；F-606 web + 网关 `draft` 转发，desktop 无此职责）
4. **批次 F4（编辑器协作增强）**：F-607 跟随模式（后端协议 ✅ 2026-09-17，前端接线）

### 5.3 关键契约备注

- **DM 会话列表**：`room_id`、`room_name`、`room_type`、`peer_user_id`、`peer_username`、`created_at`（+ `unread_count` 由控制器注入）
- **Discussions 响应**：`id`、`author_id`、`author_username`、`content`、`file_path`、`line_number`、`branch`、`commit_hash`、`parent_id`、`resolved`、`created_at`、`updated_at`
- **消息检索响应**：`{ messages: [{ id, room_id, room_name, room_type, repository_id, sender_id, sender_username, message_type, content, reply_to, created_at, reactions }] }`
- **移动文件**：请求体 `{ from_path, to_path, message?, branch? }`，响应 `{ commit_id, branch, from, to }`

---

## 六、约定与注意事项

1. **防回归**：本批已修复 `build_pr_response` 系列懒加载 500。新增/修改 PR 相关查询时，
   凡是 `build_pr_response` 的调用方，必须 `selectinload(author/merger/pr_labels)`，
   否则在有真实数据的仓库会触发 `MissingGreenlet` 500（空库测试不会暴露）。
2. **活动流埋点**：新业务动作（release/fork/star 等）如需上 Dashboard 活动流，
   调用 `services/activity_service.try_record_activity`（吞异常，不影响主流程）。
3. **i18n**：所有新文案同时补 `client/web/src/i18n/locales/{zh,en}.json`；
   禁止硬编码兜底假数据（数字用 `--`，名字用真实值或空）。
4. **移除 > 伪装**：对无后端能力的按钮，优先移除或隐藏，而不是保留装饰品误导用户。
