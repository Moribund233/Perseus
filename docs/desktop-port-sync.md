# Desktop 前端移植同步清单（web → desktop）

> **背景**: 2026-09-07 决策 D2（见 [`specs/2026-09-07-desktop-decisions.md`](specs/2026-09-07-desktop-decisions.md)）——维持"拷贝移植"策略，以本清单跟踪两端功能差异，替代共享包改造。
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
| 聊天 | ✅ 会话/频道/附件/reactions/presence | ✅ 移植（T4：门户三栏全屏页 + IDE 活动栏面板；后端补 `GET /api/v1/rooms`） | T4 | 频道=仓库房间语义与 web 一致；DM 私聊两端均未实现 |
| 通知 | ✅ 面板/未读/跳转 | ✅ 移植（T5：铃铛 Popover 面板 + 未读/已读/删除 + target_type 深链）；偏好设置页已补（2026-09-14，Settings 通知分区，四项开关与 web 对齐，按当前连接服务器存取） | T5 | |
| **协作编辑（F-204）** | ✅ **Yjs 底座**（Hocuspocus 网关 + y-codemirror.next，2026-09-08 迁移） | ✅ **T9 接入**（Monaco + y-monaco；Go 网关首帧 token 注入代理；awareness/保存语义与 web 对齐） | T9 ✅ | 两端同底座；desktop 经本地网关 collab 代理（web 直连同源网关） |
| 全局搜索 | ✅ 代码/issue 聚合搜索 | ✅ 门户聚合搜索（仓库/Issue/PR，T3；后端 `GET /api/v1/search/global` 两端可共用） | T3 | web 端 `GlobalSearch.tsx` 仍为纯代码搜索，可后续复用该端点增强 |
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
| 2026-09-07 | Editor 状态栏协作 presence/双态徽标 | ~~双态徽标~~ → ✅ 2026-09-14 两端落地（desktop `stores/editorStatus.ts` + StatusBar；web editor 状态栏；会话已同步=connected 且无未同步变更，Git 已提交=最近协作保存 short-SHA，内容再编辑即失效） |

> **2026-09-14 起移植债务清零。** 后续 web 合入影响两端的功能时按登记规则在此追加。

## 4. 后端共享增强（web/desktop 均可复用）

- **仓库语言聚合**（2026-09-10，F3 决策落地）：`Repository.languages`（`{语言标识: 文件数}` 降序）由新 `services/language_service.py` 提供——网格卡片主语言色块直接取 Top1。web 仓库列表/详情可复用该字段补齐 GitHub 式语言条。旧版仅单文件 `detect_file_language`，无聚合数据。
- **代码搜索保鲜闭环**（2026-09-16，搜索保鲜批次）：`services/search_service.py` 新增 `diff_changed_files`/`update_files`/`cleanup_index` 静态方法——push 重建异步化（`asyncio.to_thread`）、collab save 与 PR merge 走增量索引（非全量 rebuild）、仓库删除/改名清理索引残留。索引仍存于仓库内 `.perseus_search_index/`（bare 仓库下 FTS5 自然为空，搜索回退 ripgrep，未改变该设计）。
