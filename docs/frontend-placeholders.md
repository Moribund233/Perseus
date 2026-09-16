# 前端占位实现清单与开发规划

> **更新日期**: 2026-09-16
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
| 全局搜索框 | ✅ 已接线：受控输入 + 350ms 防抖 → 下拉结果（按仓库分组、可点击进 Editor 对应文件/行）+ Enter 进入 `/search` 结果页 | 复用了后端跨仓库代码搜索 `/api/v1/search/code`（已存在聚合端点）。仓库/Issue/PR 聚合搜索后端端点已于 2026-09-10 新增（`GET /api/v1/search/global`，desktop T3 先行接入），web 端可复用增强为三类分组 | P2 |
| 通知点击跳转 | ✅ 已按 `target_type` 映射路由（PR→pulls / Issue→issues / 其余→仓库），解析 repository_id→path | — | P1 |
| 侧边栏未读徽标 | 已移除假数字（本批） | 若要恢复，需后端提供未读聚合端点 | P3 |

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
| 顶栏 Eye/Search/More 三按钮 | 无 onClick | 无对应后端能力；Search 可接消息搜索（需后端消息检索端点） | P3 |
| 消息删除 | ✅ 已加本人 hover 删除按钮 + 确认，调用 `chatApi.deleteMessage` | — | P1 |
| DM 私聊列表 | 成员伪装成 DM，点击无效 | 后端无私聊模型（仅 repo room），需私信会话设计 | P3 |
| 成员在线状态 | ✅ 已接 WS presence：进入房间 `presence_list` + join/leave 实时增删（批次 D） | — | P1 |
| 频道未读数 | ✅ 已接后端 `GET /rooms/unread`（按 repository_id 映射频道）+ 进频道 `POST /rooms/{id}/read`（批次 D） | — | P1 |
| 表情回应 reactions | UI 死代码（渲染逻辑存在，数据恒空） | ✅ 已接线（2026-09-16 确认前端早已实现）：emoji picker + WS `send_reaction` 增减 + REST `chatApi.addReaction` 兜底；后端 `chat_controller.py:62-83`、`chat_service.py:228` add_reaction 已就绪 | ✅ P1 完成 |
| 消息按日期分组 | 所有消息归入 "Today" | ✅ 按 created_at 分组渲染：Today/Yesterday（新增 i18n）/本地化日期头，静态 Today 块移除（批次 E） | ✅ P2 完成 |
| 侧边栏搜索框 | 无 value/onChange | 同顶栏搜索，依赖消息检索 | P3 |

### 3.4 Editor（editor/index.tsx）

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| 协同编辑 | ✅ 已实现并迁移 **Yjs 底座**（2026-09-08，D1）：`components/editor/collabController.ts` 接入 `collab-gateway`（Hocuspocus）+ `y-codemirror.next`；远端光标/选区（awareness 标签）+ 协作保存（stateless → 网关 → Git commit 全员广播）+ **断线本地编辑保留**（CRDT 重连收敛，3.6 方案 B 天然解决）；**邀请链接（2026-09-16，M2）**：工具栏「分享协作」生成会话级临时权限链接（仅成员），`?invite=` 经 JSON token 透传网关 | 会话 TTL/空闲卸载未做（Y.Doc 驻留内存至网关重启）；"会话已同步/Git 已提交"双态徽标待接 `hasUnsyncedChanges`/`collab-saved`（原 3.3 项）；不支持离线合并（页面关闭即丢，与旧版一致） | P2 |
| Discussions 面板 | 空状态占位（mock 已移除） | 行内评论需后端锚定文件+行号存储，可复用 PR 评论模型扩展 | P3 |
| 协作者 "viewing" 状态 | ✅ 已接 WS presence：在线协作者列表即 Editors tab 内容（批次 D）；本文件会话参与者经 `collab_init`/peer 事件展示（F-204） | — | P3 |
| "Online" 绿点 | ✅ 已接房间 presence（在线人数 > 0 亮绿）（批次 D） | — | P2 |
| 面包屑点击 | cursor:pointer 无跳转 | ✅ 已接线（批次 E）：目录段点击加载该目录并钉出浮动面板（对齐文件树点位），根段点击回根文件树（清选中与面板链） | ✅ P2 完成 |
| 文件删除入口 | ✅ 已加文件树 hover 删除按钮 + 确认弹窗，调用 `deleteFileContent`，删除后刷新树并关闭对应标签 | — | P1 |
| 文件重命名/移动 | 无 | ✅ 后端 move 端点已就绪（2026-09-16，`POST /{repo_id}/contents/move` 单次提交 copy+delete）；前端重命名/移动 UI 待接 | P3 |

### 3.5 Pull Requests

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| Filter 按钮 | 无 onClick | ✅ 已移除装饰按钮（批次 E），筛选由状态按钮组完成，unused i18n key 一并清理 | ✅ P4 完成 |
| 审阅者头像堆叠 | 恒只显示作者 | PR 详情已加 Review 提交区（Approve/Request changes/Comment） | P2 |
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
| "Docs" 导航链接 | `<a>` 无 href | 需文档站或移除 | P4 |
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
| 待排期 | DM 私聊、行内评论、亮色主题 | 涉及新后端能力 |

---

## 五、约定与注意事项

1. **防回归**：本批已修复 `build_pr_response` 系列懒加载 500。新增/修改 PR 相关查询时，
   凡是 `build_pr_response` 的调用方，必须 `selectinload(author/merger/pr_labels)`，
   否则在有真实数据的仓库会触发 `MissingGreenlet` 500（空库测试不会暴露）。
2. **活动流埋点**：新业务动作（release/fork/star 等）如需上 Dashboard 活动流，
   调用 `services/activity_service.try_record_activity`（吞异常，不影响主流程）。
3. **i18n**：所有新文案同时补 `client/web/src/i18n/locales/{zh,en}.json`；
   禁止硬编码兜底假数据（数字用 `--`，名字用真实值或空）。
4. **移除 > 伪装**：对无后端能力的按钮，优先移除或隐藏，而不是保留装饰品误导用户。
