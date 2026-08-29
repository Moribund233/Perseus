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

### 2.1 Releases（发行版）— P1

- **后端**: `release_controller.py` 已实现 list/get/getByTag/create/update/delete
- **前端**: `api/releases.ts` 已完整封装，**零引用**
- **建议**: 在仓库页新增 Releases tab，列表 + 创建/编辑弹窗；打 tag 关联 commit SHA
- **工作量**: 前端 1~2 天

### 2.2 Webhooks（Web 钩子）— P1

- **后端**: `webhook_controller.py` 已实现 8 个路由（CRUD/test/listDeliveries/getDelivery）
- **前端**: `api/webhooks.ts` 已完整封装，**零引用**
- **建议**: 仓库 Settings 子页（若仓库设置页先行，合并开发）；展示投递记录方便调试
- **工作量**: 前端 1~2 天

### 2.3 Builds / CI（构建）— P1

- **后端**: `build_controller.py` 已实现 list/get/create/getLogs；PR 合并后自动创建 Build（F-046）
- **前端**: `api/builds.ts` 已完整封装，**零引用**
- **建议**: 仓库页 Actions tab（当前点击无反应）改为 Builds 列表 + 日志查看；PR 详情页可挂 Build 状态徽标
- **工作量**: 前端 1~2 天

### 2.4 用户中心类 API — P1

`api/settings.ts` 中已封装但 UI 无入口：

| 方法 | 后端 | 建议 |
|---|---|---|
| `listSSHKeys / addSSHKey / deleteSSHKey` | `key_controller.py` | Settings 新增 SSH Keys tab（表单 + 列表 + 删除） |
| `listOAuthAccounts / unlinkOAuth` | `oauth_controller.py` | Settings 新增 OAuth 账号管理卡片 |
| `getUserPullRequests / getUserIssues` | `user_controller.py /me/*` | Dashboard 或用户页聚合展示 |

---

## 三、按页面的剩余占位点

### 3.1 顶栏 / 全局（AppLayout）

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| 全局搜索框 | 无 value/onChange/onPressEnter | 后端 `search_controller.py` 已有仓库内与跨仓库搜索；需补全局搜索聚合端点 + 结果下拉页 | P2 |
| 通知点击跳转 | ✅ 已按 `target_type` 映射路由（PR→pulls / Issue→issues / 其余→仓库），解析 repository_id→path | — | P1 |
| 侧边栏未读徽标 | 已移除假数字（本批） | 若要恢复，需后端提供未读聚合端点 | P3 |

### 3.2 仓库页（repositories/index.tsx）

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| Watch 按钮 | 无 onClick | 后端无 watch API（只有 star/fork）。需新表/字段 + 端点，或先移除该按钮 | P3 |
| Actions tab | 点击仅高亮，无内容 | 接 Builds（见 2.3） | P1 |
| Settings tab | 点击仅高亮，无内容 | 仓库设置子路由：改描述/可见性（`repositoriesApi.update` 已封装）、默认分支切换（`branch_controller` 已有）、Webhooks、协作者管理入口 | P1~P2 |
| 文件列表"最近提交/时间"两列 | 写死 `-` 和空白 | 需后端按目录聚合每文件最近提交（`get_commits` 逐文件请求开销大），建议后端新增 tree+last-commit 聚合端点 | P3 |

### 3.3 团队聊天（chat/index.tsx）

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| 顶栏 Eye/Search/More 三按钮 | 无 onClick | 无对应后端能力；Search 可接消息搜索（需后端消息检索端点） | P3 |
| 消息删除 | ✅ 已加本人 hover 删除按钮 + 确认，调用 `chatApi.deleteMessage` | — | P1 |
| DM 私聊列表 | 成员伪装成 DM，点击无效 | 后端无私聊模型（仅 repo room），需私信会话设计 | P3 |
| 成员在线状态 | 硬编码 `online` | 后端 ConnectionManager 有连接状态，需 presence 广播/查询端点 | P3 |
| 频道未读数 | 硬编码 0 | 需未读计数（按房间记录 last_read 水位） | P3 |
| 表情回应 reactions | UI 死代码（渲染逻辑存在，数据恒空） | 后端消息 reactions 存储 + WS 广播 | P3 |
| 消息按日期分组 | 所有消息归入 "Today" | 纯前端按 created_at 分组渲染 | P2 |
| 侧边栏搜索框 | 无 value/onChange | 同顶栏搜索，依赖消息检索 | P3 |

### 3.4 Editor（editor/index.tsx）

| 占位点 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| Discussions 面板 | 空状态占位（mock 已移除） | 行内评论需后端锚定文件+行号存储，可复用 PR 评论模型扩展 | P3 |
| 协作者 "viewing" 状态 | 硬编码 | 需 presence/编辑会话广播（WS 已有基础设施） | P3 |
| "Online" 绿点 | 硬编码 | 接 WS 连接状态即可（`chatSocket` 已有状态机可参考） | P2 |
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
| **批次 B（仓库能力页）** | Releases tab（2.1）+ Actions/Builds tab（2.3）+ 仓库 Settings tab（含 Webhooks 2.2、协作者、默认分支） | 前端 3~5 天 |
| **批次 C（用户中心）** | SSH Keys、OAuth 账号管理、`/me/*` 聚合展示（2.4）；全局搜索（3.1） | 前端 2~3 天（搜索含少量后端） |
| **批次 D（实时增强）** | Editor 在线状态（3.4）、聊天 presence/未读数（3.3）—— 共用 presence 基础设施，需后端 WS 扩展 | 前后端 4~6 天 |
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
