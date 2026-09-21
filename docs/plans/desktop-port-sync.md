# Desktop 前端移植同步清单（web → desktop）

> **背景**: 2026-09-07 决策 D2（见 [`archive/specs/2026-09-07-desktop-decisions.md`](../archive/specs/2026-09-07-desktop-decisions.md)）——维持"拷贝移植"策略，以本清单跟踪两端功能差异，替代共享包改造。
> **用法**: web 端新功能合入时在此登记（状态 ⬜）；移植 desktop 时更新状态与移植批次列；两端结构性分叉时在"备注"记录原因。
> **2026-09-10**: UI 补全批次（T1-T7、T9）完成，主表全面回填；剩余欠项集中在 Builds/Releases、Dashboard 贡献图/活动流、用户中心。
> **2026-09-10（原型还原度）**: 逐屏对照 `client/prototype/desktop-ui/` 审计并按 F0-F3 批次修复：Monaco 主题/etab 色块/crumbs hint（F0）、Issue 新建按钮/readme Markdown/last-commit 列/branch pill/复刻按钮/Tab 计数（F1）、Issue 详情侧栏与列表行标签（F2）、仓库树 `.fc` 芯片/StatusBar Ln/Col（F3）；**后端新增 `languages` 聚合**（`services/language_service.py`，卡片主语言，web 可复用，见 §4）。
> **2026-09-14（同步批次收官）**: 存量欠项全部移植完毕，主表除结构性 ➖ 外全 ✅——Builds/Releases（T8）、Dashboard 贡献图/活动流（并入我的工作）、用户中心（SSH Keys/OAuth）、通知偏好设置页；**移植债务清零**：双态徽标（会话已同步/Git 已提交）两端落地 + M1 未保存离开提示（`beforeunload` × `hasPendingChanges`）两端补齐。web 搜索页接入 `/search/global` 聚合对齐 desktop T3。Release 附件上传/下载/删除（F1）、分支保护面板（F2）、顶栏全局搜索聚合（F3）、通知偏好 8 项（F4）两端同步落地；F-047 构建状态展示完结；F-205 实时通知推送完成。验证：web `tsc+vite` ✅ / desktop `tsc+vite` ✅ / pytest 867 passed / 契约脚本 0 不一致（后端 187 ops vs 前端 109 调用）。

**状态**: ✅ 已移植 / 🟡 部分 / ⬜ 未移植 / ➖ 不适用（桌面模型替代或职责外）

## 1. 功能差异总表（2026-09-07 盘点）

| 功能域 | web 端现状 | desktop 现状 | 移植批次 | 备注 |
|--------|-----------|--------------|----------|------|
| 认证/会话刷新 | ✅ 登录页 + 401 自动刷新 | ➖ 服务器注册表替代（登录换 token 进密钥库） | — | 模型不同, 不移植 |
| 仓库浏览 | ✅ 列表/详情/树/blob | ✅ 移植（2A, proxy 化）+ 原型还原度补全（F1：文件表 last-commit 列、README Markdown、branch pill、Tab 计数/复刻按钮；F3：卡片主语言色点取自 §4 聚合） | 2A | 文件内容 `<pre>` 只读, web 为编辑器 |
| Issues | ✅ 列表/详情/创建/评论/关闭 | ✅ 移植（2B） | 2B | |
| Pull Requests | ✅ 列表/详情/merge/close/review | ✅ 移植（T1 补创建 Modal） | T1 ✅ | |
| 聊天 | ✅ 会话/频道/附件/reactions/presence | ✅ 移植（T4：门户三栏全屏页 + IDE 活动栏面板；后端补 `GET /api/v1/rooms`）+ DM 私聊/消息检索（2026-09-18）+ 静音会话/未读徽标（批次 G，2026-09-18） | T4 / 2026-09-18 | 频道=仓库房间语义与 web 一致 |
| 通知 | ✅ 面板/未读/跳转 | ✅ 移植（T5：铃铛 Popover 面板 + 未读/已读/删除 + target_type 深链）；偏好设置页已补（2026-09-14，Settings 通知分区，四项开关与 web 对齐，按当前连接服务器存取） | T5 | |
| **协作编辑（F-204）** | ✅ **Yjs 底座**（Hocuspocus 网关 + y-codemirror.next，2026-09-08 迁移） | ✅ **T9 接入**（Monaco + y-monaco；Go 网关首帧 token 注入代理；awareness/保存语义与 web 对齐） | T9 ✅ | 两端同底座；desktop 经本地网关 collab 代理（web 直连同源网关） |
| 全局搜索 | ✅ 代码搜索 + 仓库/Issue/PR 聚合（2026-09-14 接入 `GET /api/v1/search/global`：下拉 + `/search` 结果页三类分组，两端一致） | ✅ 门户聚合搜索（仓库/Issue/PR，T3；后端 `GET /api/v1/search/global` 两端可共用） | T3 | |
| Dashboard（贡献图/活动流） | ✅ | ✅ 我的工作（T6：跨仓库 PR/Issue 聚合 + 深链跳转）；贡献图/活动流已补（2026-09-14：`GET /users/me/dashboard` 聚合，近 30 天贡献柱状图 + 统计 chips + 动态 i18n 活动流，并入 MyWorkView，与 web ContribGraph 同款） | T6 ✅ | |
| Builds / Releases / Webhooks / 仓库设置 | ✅ | ✅ 仓库设置 tab（T2：Webhooks + 协作者）；Builds/Releases 已移植（2026-09-14，T8 落地：Builds 列表+日志 Modal、Releases 列表/创建/编辑/删除，仓库详情新增 构建/发布 两 Tab，与 web 同键组 `app.repositories.builds/releases.*`） | T2 ✅ / T8 ✅ | |
| 用户中心（SSH Keys/OAuth /me） | ✅ | ✅ 已移植（2026-09-14，Settings 账户分区：SSH Keys 增删 + OAuth 关联解绑，按当前连接服务器经网关代理操作；web `settingsApi` 同路径） | 2026-09-14 | desktop identity 徽标保留只读展示 |
| Editor 文件保存/删除 API | ✅（服务端 blob 提交） | ➖ 本地工作区直接读写文件系统 | — | 职责由本地 fs/git 替代 |
| 404/错误页、骨架屏 | ✅ | ✅ skeleton 已随 2A/2B 移植 | — | |

## 2. desktop 独有能力（web 无对应, 不回移植）

- 服务器注册表 + 密钥库 token + health 探测 + 离线 LRU 缓存（gateway 反向代理）
- 本地工作区（clone/文件树/Monaco 编辑/git status/add/commit）
- Wails 原生绑定（对话框/密钥库）

## 3. 已登记的移植债务（web 迭代产生的落后项）

登记规则：web 合入影响两端的功能后，desktop 未跟进的，在此追加一行。

| 日期 | web 变更 | 欠缺的 desktop 跟进 |
|------|----------|---------------------|
| 2026-09-07 | F-204 协作编辑合入（含断线 rejoin/权限缓存等修复） | ~~协作能力整体~~ → ✅ 2026-09-10 T9 y-monaco 接入完成（Yjs 同底座） |
| 2026-09-07 | Editor 状态栏协作 presence/双态徽标 | ~~双态徽标~~ → ✅ 2026-09-14 两端落地（desktop `stores/editorStatus.ts` + StatusBar；web editor 状态栏；会话已同步=connected 且无未同步变更，Git 已提交=最近协作保存 short-SHA，内容再编辑即失效）；**「版本 N」✅ 2026-09-18 两端**：「会话已同步 · v{N}」由 `collab-saved` 广播的 `version` 驱动（网关 `collab-gateway/versionCounter.mjs`，Redis INCR 持久计数 / 无 Redis 回退内存） |
| 2026-09-16 | 协作邀请链接（M2）：web 编辑器「分享协作」生成会话级临时权限链接（`?invite=` 透传 `invite_token`，网关 JSON token 解析） | ~~协作会话邀请入口（y-monaco 会话）：编辑器工具栏分享按钮 + 以 `?invite=` 加入会话~~ → ✅ 2026-09-18（F-605）：编辑器 crumbs 分享按钮 → `repositoriesApi.createCollabInvite` → 复制 `<base>/editor/owner/repo?file=&invite=` 链接（格式与 web 一致） |
| 2026-09-17 | 跟随模式（Follow me）：web 接线参与者点选跟随/停止、工具栏「跟我来」（写权限）、跟随者计数、有跟随者时节流广播 `viewport` awareness | ✅ 2026-09-17 已补：desktop `CollabMonaco` 跟随菜单/跟我来/跟随指示 + `CollabSession` awareness `viewport`（字符偏移与 web 同单位）/`follow` + spotlight 信令 |
| 2026-09-18 | 批次 F1/F2（web）: DM 私聊/消息检索（聊天）+ 行内评论 Discussions/文件移动重命名 UI（编辑器） | ~~聊天 DM/搜索 + 编辑器 Discussions/移动 UI — desktop 待跟进~~ → ✅ 2026-09-18 desktop 落地：聊天页 DM 列表/私聊按钮 + 消息搜索框（`ChatView.tsx`）；IDE 行内评论面板（`DiscussionsPanel.tsx`，文件级线程/回复/解决/删除/跳行，`useWorkspaceRepo`+远端 proxy）；文件移动重命名（workspace rename 端点 `POST /api/local/workspaces/{id}/rename` 新增 + ExplorerPanel 重命名 Modal，TDD `TestWorkspaceRename`） |
| 2026-09-18 | 批次 F3: F-606 空闲自动落盘（web 计时 → 网关转发 `draft` → 落 `collab/draft-{branch}`）；F-605 desktop 分享邀请已补 | F-606 不适用 desktop（本地 fs 直接写盘即保存） |
| 2026-09-18 | 批次 G（web）: 聊天顶栏 Eye/More 接线（Eye=右侧成员面板显隐；More=频道信息 Drawer+静音开关）+ 静音会话排除未读（后端 `POST /api/v1/rooms/{room_id}/members/me` → `set_member_muted`，`GET /rooms/unread` 与 DM 未读均排除）+ 侧边栏未读徽标恢复（`AppLayout` 轮询聚合） | ~~desktop 待跟进~~ → ✅ 2026-09-18：ChatView 顶栏成员面板显隐已有（T4）；本批补静音开关（header Bell 按钮，`chatApi.setMemberMuted` proxy + store `setMemberMuted` 回写 is_muted + 刷新未读，未读排除被动受益）+ 成员行静音标记 + 活动栏聊天徽标/Welcome 聊天入口徽标（`useChatUnreadBadge`=频道未读+DM 未读聚合）；顺带移除活动栏重复 chat 按钮 |
| 2026-09-18 | 批次 H（web）: 参与者「未保存/已提交」徽标（awareness `unsaved`）、PR 列表审阅者头像堆叠（后端 `reviewers`）、聊天搜索「全部会话/本会话」范围切换（`GET /rooms/{id}/messages?q=`） | ✅ 2026-09-18 desktop：`collabSocket.ts` awareness `unsaved` + `CollabMonaco` 参与者徽标/tooltip；PR 列表头像堆叠（`PullRequestsView.tsx`，复用后端 `reviewers`）。聊天单会话搜索范围切换为 web 专属，未移植（desktop ChatView 保留跨会话搜索） |

> **2026-09-14 起移植债务清零。** 后续 web 合入影响两端的功能时按登记规则在此追加。
> **2026-09-16**: 邀请链接（M2）已登记 desktop 跟进项（见上表）。

## 4. 后端共享增强（web/desktop 均可复用）

- **仓库语言聚合**（2026-09-10，F3 决策落地）：`Repository.languages`（`{语言标识: 文件数}` 降序）由新 `services/language_service.py` 提供——网格卡片主语言色块直接取 Top1。web 仓库列表/详情可复用该字段补齐 GitHub 式语言条。旧版仅单文件 `detect_file_language`，无聚合数据。
- **代码搜索保鲜闭环**（2026-09-16，搜索保鲜批次）：`services/search_service.py` 新增 `diff_changed_files`/`update_files`/`cleanup_index`——push/collab save/PR merge 走增量索引（非全量 rebuild）、仓库删除清理索引。**后续（2026-09-20）搜索架构重构**：内容改为取自 Git 对象（pygit2）、索引持久化到主库（`repo_search_files`/`repo_search_state`，PostgreSQL `pg_trgm` GIN），不再使用仓库内 `.perseus_search_index/` 文件，ripgrep 退役。
