# Desktop 前端移植同步清单（web → desktop）

> **背景**: 2026-09-07 决策 D2（见 [`specs/2026-09-07-desktop-decisions.md`](specs/2026-09-07-desktop-decisions.md)）——维持"拷贝移植"策略，以本清单跟踪两端功能差异，替代共享包改造。
> **用法**: web 端新功能合入时在此登记（状态 ⬜）；移植 desktop 时更新状态与移植批次列；两端结构性分叉时在"备注"记录原因。

**状态**: ✅ 已移植 / 🟡 部分 / ⬜ 未移植 / ➖ 不适用（桌面模型替代或职责外）

## 1. 功能差异总表（2026-09-07 盘点）

| 功能域 | web 端现状 | desktop 现状 | 移植批次 | 备注 |
|--------|-----------|--------------|----------|------|
| 认证/会话刷新 | ✅ 登录页 + 401 自动刷新 | ➖ 服务器注册表替代（登录换 token 进密钥库） | — | 模型不同, 不移植 |
| 仓库浏览 | ✅ 列表/详情/树/blob | ✅ 移植（2A, proxy 化） | 2A | 文件内容 `<pre>` 只读, web 为编辑器 |
| Issues | ✅ 列表/详情/创建/评论/关闭 | ✅ 移植（2B） | 2B | |
| Pull Requests | ✅ 列表/详情/merge/close/review | 🟡 列表/详情/评论/merge/close；**创建 PR 仅按钮无 Modal** | 2B+ | 补创建 Modal |
| 聊天 | ✅ 会话/频道/附件/reactions/presence | ✅ 移植（T4：门户三栏全屏页 + IDE 活动栏面板；后端补 `GET /api/v1/rooms`） | T4 | 频道=仓库房间语义与 web 一致；DM 私聊两端均未实现 |
| 通知 | ✅ 面板/未读/跳转 | ✅ 移植（T5：铃铛 Popover 面板 + 未读/已读/删除 + target_type 深链） | T5 | 偏好设置页未移植（desktop Settings 暂无对应 Tab） |
| **协作编辑（F-204）** | ✅ **Yjs 底座**（Hocuspocus 网关 + y-codemirror.next，2026-09-08 迁移） | ⬜ | **y-monaco 接入**（D1） | CRDT 底座已就绪, desktop 仅需 y-monaco 绑定 + provider 接线, 无协议适配 |
| 全局搜索 | ✅ 代码/issue 聚合搜索 | ✅ 门户聚合搜索（仓库/Issue/PR，T3；后端 `GET /api/v1/search/global` 两端可共用） | T3 | web 端 `GlobalSearch.tsx` 仍为纯代码搜索，可后续复用该端点增强 |
| Dashboard（贡献图/活动流） | ✅ | ⬜ | 待排期 | |
| Builds / Releases / Webhooks / 仓库设置 | ✅ | ⬜（仓库 settings tab 空占位） | 待排期 | |
| 用户中心（SSH Keys/OAuth /me） | ✅ | ⬜ | 待排期 | desktop identity 仅只读徽标 |
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
| 2026-09-07 | F-204 协作编辑合入（含断线 rejoin/权限缓存等修复） | ~~协作能力整体~~ → 已被 Yjs 迁移取代（2026-09-08 web 迁 Yjs 底座, desktop 走 y-monaco 接入） |
| 2026-09-07 | Editor 状态栏协作 presence/双态徽标 | 同上（Yjs 底座迁移后一并评估） |
