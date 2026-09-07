# 前端占位实现清单与开发规划

> **更新日期**: 2026-08-29
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
| 全局搜索框 | ✅ 已接线：受控输入 + 350ms 防抖 → 下拉结果（按仓库分组、可点击进 Editor 对应文件/行）+ Enter 进入 `/search` 结果页 | 复用了后端跨仓库代码搜索 `/api/v1/search/code`（已存在聚合端点） | P2 |
| 通知点击跳转 | ✅ 已按 `target_type` 映射路由（PR→pulls / Issue→issues / 其余→仓库），解析 repository_id→path | — | P1 |
| 侧边栏未读徽标 | 已移除假数字（本批） | 若要恢复，需后端提供未读聚合端点 | P3 |

### 3.2 仓库页（repositories/index.tsx）

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| Watch 按钮 | 无 onClick | 后端无 watch API（只有 star/fork）。需新表/字段 + 端点，或先移除该按钮 | P3 |
| Actions tab | ✅ 已接 Builds 列表 + 日志（批次 B） | — | P1 |
| Settings tab | ✅ 已实现仓库设置子内容：描述/可见性/默认分支、协作者管理、Webhooks（批次 B） | — | P1~P2 |
| 文件列表"最近提交/时间"两列 | 写死 `-` 和空白 | 需后端按目录聚合每文件最近提交（`get_commits` 逐文件请求开销大），建议后端新增 tree+last-commit 聚合端点 | P3 |

### 3.3 团队聊天（chat/index.tsx）

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| 顶栏 Eye/Search/More 三按钮 | 无 onClick | 无对应后端能力；Search 可接消息搜索（需后端消息检索端点） | P3 |
| 消息删除 | ✅ 已加本人 hover 删除按钮 + 确认，调用 `chatApi.deleteMessage` | — | P1 |
| DM 私聊列表 | 成员伪装成 DM，点击无效 | 后端无私聊模型（仅 repo room），需私信会话设计 | P3 |
| 成员在线状态 | ✅ 已接 WS presence：进入房间 `presence_list` + join/leave 实时增删（批次 D） | — | P1 |
| 频道未读数 | ✅ 已接后端 `GET /rooms/unread`（按 repository_id 映射频道）+ 进频道 `POST /rooms/{id}/read`（批次 D） | — | P1 |
| 表情回应 reactions | UI 死代码（渲染逻辑存在，数据恒空） | 后端消息 reactions 存储 + WS 广播 | P3 |
| 消息按日期分组 | 所有消息归入 "Today" | 纯前端按 created_at 分组渲染 | P2 |
| 侧边栏搜索框 | 无 value/onChange | 同顶栏搜索，依赖消息检索 | P3 |

### 3.4 Editor（editor/index.tsx）

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| 协同编辑 | ✅ 已实现（F-204）：`components/editor/collabController.ts` 接入 `/ws/collab`，CodeMirror 6 collab OT 同步 + 远端光标/选区渲染（带用户名标签）+ 协作保存（以服务端权威文本提交 Git，回退 HTTP 直提）+ 断线重连自动 rejoin | 远端光标位置在本地有未确认变更时存在短暂偏移（自校正）；断线重连后本地未确认变更会被服务端快照覆盖（策略决策见 `docs/collab-f204-vs-cwm.md` 3.6）；不支持离线合并 | P2 |
| Discussions 面板 | 空状态占位（mock 已移除） | 行内评论需后端锚定文件+行号存储，可复用 PR 评论模型扩展 | P3 |
| 协作者 "viewing" 状态 | ✅ 已接 WS presence：在线协作者列表即 Editors tab 内容（批次 D）；本文件会话参与者经 `collab_init`/peer 事件展示（F-204） | — | P3 |
| "Online" 绿点 | ✅ 已接房间 presence（在线人数 > 0 亮绿）（批次 D） | — | P2 |
| 面包屑点击 | cursor:pointer 无跳转 | 点击目录段切回该目录/根文件树，纯前端 | P2 |
| 文件删除入口 | ✅ 已加文件树 hover 删除按钮 + 确认弹窗，调用 `deleteFileContent`，删除后刷新树并关闭对应标签 | — | P1 |
| 文件重命名/移动 | 无 | 后端需 move 端点（或 copy+delete 组合提交） | P3 |

### 3.5 Pull Requests

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| Filter 按钮 | 无 onClick | 筛选实际由状态按钮组完成；建议直接移除该装饰按钮 | P4 |
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
| **批次 E（体验完善）** | 消息 reactions、DM 私聊、文件树 last-commit 聚合、行内评论、亮色主题 | 按需评估，均涉及新后端能力 |

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
