# Perseus Desktop Phase 2B 设计（Spec）

> 日期：2026-08-08
> 状态：待评审
> 前置：Phase 2A 已交付（服务器注册表/登录/反向代理/WS 透传/离线语义/Repo 列表+代码详情/Clone）
> 范围：`client/web` + `client/desktop` — issues/PR 页面补齐（web）+ 忠实移植（desktop）；聊天与通知不在本期

---

## 1. 背景与目标

Phase 2A 让 desktop 成为远程 Perseus 客户端：多服务器注册表、通用反向代理（`/api/local/proxy/{serverId}/*`）、离线 503 + LRU 缓存、WS 透传，以及仓库列表/代码浏览/Clone to workspace。仓库详情页的 issues/PR tabs 目前是 `comingIn2b` 占位。

Phase 2B 目标是补齐协作工作流的两大主体：**Issue** 与 **Pull Request**。

### 现状调研结论（决定实施方案）

- Web 端 `api/issues.ts`、`api/pullRequests.ts`、`stores/issues.ts`、`stores/pullRequests.ts` **API 与 store 层已完整实现**（list/filter/get/create/update/close/reopen/batch/merge/comments/reviews/labels）。
- 但 Web 端 **issues 没有任何页面组件**（只有 API+store）；`pull-requests` 路由只是**只读列表**（状态筛选、计数、作者/时间/标签展示，无详情、无创建、无操作）。
- 后端能力齐全：`issue_controller.py`（list/filter/batch/close/reopen/details/update/comments）、`pull_request_controller.py`（list/get/create/patch/close/merge/comments/reviews）、`pr_label_controller.py`（labels CRUD + PR 打标）。
- Desktop 端 `RepositoriesView.tsx` 已有 code/pullRequests/issues/settings 四个 tab，issues/PR 是占位；`proxyRequest` 与 `ApiError`（offline/cached）就绪；无 `users/me` 身份层。

**因此本 spec 采用"先补 web、再忠实移植"路线**（非从零自定 UI）：web 补齐的页面组件就是 desktop 移植的直接参照物，UI 逻辑只写一遍。

### 1.1 目标

1. **Web 端**：在仓库详情页补全 issues/PR 完整 UI——列表（筛选/计数/新建）、详情（作者/状态/时间/描述/评论/操作）、创建、关闭/重开（issue）、合并/关闭/Review（PR）。走现有 `apiRequest`。
2. **Desktop 端**：新增 identity（`GET /api/v1/users/me` 经 proxy），把 web 新补的 issues/PR 组件移植进 `RepositoriesView` 现有 tabs，替换占位；API 改用 `proxyRequest`，store 逻辑照搬。
3. 全量验证：web build、desktop build 全绿。

### 1.2 非目标（本 spec 不做）

- 通知/未读徽标、（基础聊天也）留 Phase 2C
- WS 事件流接入（`/ws/events`）留后续
- **标签管理**（创建/编辑/删除 label、打标/去标）——仅展示 issue/PR 响应中已有的 `labels` 字段；标签 CRUD 端点不在本期范围
- PR 基于文件的逐行点评（inline diff review）——仅做整条 PR 的 review 提交（approved/changes_requested/commented）
- Web 端 Creator 工具链（diff 视图、3-way edit）不引入
- Go 侧无新代码（纯前端特性，全走既有 proxy 层）

---

## 2. 架构决策（已确认）

| 维度 | 决策 | 理由 |
|------|------|------|
| 实施顺序 | **先 web 补齐，再从 web 移植 desktop** | UI/逻辑只写一遍；desktop 组件直接复用 web 源码改 `apiRequest`→`proxyRequest` |
| Web 页面形态 | 仓库详情页新增**子路由** `/repositories/:owner/:repo/issues`、`/pulls`（均可带 `/:num` 详情） | 详情态需要可刷新/可深链，优于 tab 内嵌 state |
| Desktop 入口 | 沿用现有 `RepositoriesView` tabs（code/pullRequests/issues/settings），替换占位 | 最小侵入，符合 2A 架构；无 router，靠 tab 展示 |
| 当前用户 | desktop 新增 `stores/identity.ts`：登录后调 `GET /api/v1/users/me`（经 proxy）缓存；ServerShell 初始化时加载 | 用于 issue/PR 作者、创建者归属与头像展示 |
| 状态管理 | web 沿用 Zustand 既有 store；desktop 复制同名 store 逻辑（repoId 改从当前仓库取） | 与 2A 的 repositories store 移植模式一致 |
| 错误处理 | 复用 `ApiError`（offline/cached/status）；操作失败 `message.error` 透传 | 2A 已定标准 |

---

## 3. Web 端补齐

### 3.1 路由与导航

`client/web/src/App.tsx` 仓库详情下新增子路由（AppLayout 内）：
```
/repositories/:owner/:repo/issues            issues 列表
/repositories/:owner/:repo/issues/:num       issue 详情
/repositories/:owner/:repo/pulls             PR 列表
/repositories/:owner/:repo/pulls/:num        PR 详情
```
仓库详情页顶部 tabs 的 issues/PR 标签改为 `Link` 跳转子路由（沿用现有 `AppLayout`+`PageTransition` 包裹，与 dashboard 等一致）。

### 3.2 Issues

- **API/store**：复用现有 `api/issues.ts` + `stores/issues.ts`（已含全部方法，无需改）。
- **组件**（新增 `client/web/src/routes/repositories/issues/`）：
  - `index.tsx` — 列表：状态 tab（open/closed/all + 计数）、"新建 Issue"按钮（Modal 表单：标题/描述/优先级）、列表项（状态图标/标题/作者/相对时间/标签/评论数）。空态与加载态。
  - `[issueNumber].tsx` — 详情：标题头（状态 Tag、优先级、作者用户名、时间）+ 描述正文 + 评论列表 + 评论输入（`createComment`）+ 操作（close/reopen，banner 状态）。回到列表链接。
  - 复用 `relativeTime`、标签色映射（提取到 `web/src/lib/` 或组件内局部辅助函数，沿用既有点位）。
- **特征**：once mounted 时 `fetchIssues(repoId, status)`；操作后局部刷新当前行。

### 3.3 PR

- **API/store**：复用现有 `api/pullRequests.ts` + `stores/pullRequests.ts`（无需改动）。
- **组件**（新增 `client/src/routes/pull-requests/detail.tsx` 或子目录）：
  - `index.tsx` — 列表：状态 filter（open/merged/closed/all + 计数）、仓库选择（多仓库场景沿用现有 select）、"New Pull Request"按钮（创建表单：title/description/source/target 分支）、列表项（状态/标题/标签/作者/评论数/review 数）。
  - `detail.tsx` — 详情：标题头（状态、作者、时间、分支关系 source → target）、描述、`is_draft` 徽标、操作区（merge[merge/squash/rebase]/close）、评论列表 + 评论输入、Review 提交（approved/changes_requested/commented + comment）。
  - 无 diff/文件级点评（非目标）。

### 3.4 公共抽取

`getInitials`、`getAvatarColor`、`relativeTime`、标签色 map 在 web 与 desktop 各自已有局部副本；**仍在各自复制**（与当前代码风格一致，不做跨端共享包）。

---

## 4. Desktop 移植

### 4.1 API 层

- 新增 `client/desktop/frontend/src/api/issues.ts`、`pullRequests.ts`：复刻 web 同名类型与方法，内部走 `proxyRequest(serverId, ...)`（`serverId` 来自 `useGatewayStore`/servers 当前选中），`apiRequest` 用 `proxyRequest` 替换。
- 新增 `api/identity.ts`：`fetchCurrentUser(serverId)` → `GET /api/v1/users/me`。

### 4.2 stores

- 新增 `stores/issues.ts`、`stores/pullRequests.ts`：复制 web store 逻辑，`repoId` 改为从 `useRepositoriesStore` 当前 `currentRepo` 获取；错误用 `ApiError`。
- 新增 `stores/identity.ts`：`user: User|null`、`fetchIdentity(serverId)`；在 `ServerShell` 挂载时 + 切换服务器时重新拉取。

### 4.3 视图

- `views/repositories/RepositoriesView.tsx`：在 `activeTab === 'issues'` / `'pullRequests'` 分支渲染移植的 `IssuesView` / `PullRequestsView`（内部含列表+详情两态，state 切换，与仓库列表/详情同模式）。删除 `comingIn2b` 占位。
- 作者/当前用户头像展示用 `identity`。

### 4.4 i18n

- 新增命名空间：`desktop.issues.*`、`desktop.pullRequests.*`（`zh.json`/`en.json`），key 与文案与 web 层 (`app.issues.*` / `app.pullRequests.*`）对齐。

---

## 5. 错误处理与事件

- desktop 侧：`proxyRequest` 3xx/4xx → `ApiError`；61xxx 离线 → `offline:true`；页面显示离线/缓存的既有语义。
- 操作（create/close/merge/comment/review）失败 → `message.error((e as ApiError).message)`。
- web 侧沿用现有 `apiRequest` 错误行为（无桌面离线概念）。

---

## 6. 测试

| 层 | 方式 |
|----|------|
| Web 前端 | `npm run build`（tsc + vite）；手工：登入 → 进仓库 issues → 新建/关闭/评论；PR 新建/合并/关闭 |
| Desktop 前端 | `npm run build`（tsc）；手工验收：添加服务器 → 进仓库 issues/PR tabs → 全部操作走 proxy |
| 后端 | 无新代码，不需要新后端测试；依赖已存在 gateway 代理测试 |

手工验收清单（desktop）：添加服务器 → 仓库详情 → issues tab 列表/详情/新建/关闭 → PR tab 列表/创建/合并/评论 → identity 显示当前用户 → 断开发离线态。

---

## 7. Task 拆分（粗）

**Web 端：**
1. 仓库详情 issues 子路由 + 列表页（Tab 计数、筛选、空态/加载态）
2. issues 新建表单（Modal） + 详情页（评论/close/reopen）
3. 仓库详情 PR 子路由 + 列表页（filter/计数/仓库选择/新建按钮）
4. PR 详情页（分支/merge/close/评论/review） + 新建 PR 表单

**Desktop 端：**
5. api/issues.ts、api/pullRequests.ts、api/identity.ts （proxyRequest 化）
6. stores/issues.ts、stores/pullRequests.ts（复制逻辑）
7. stores/identity.ts + ServerShell 装配
8. IssuesView/PullRequestsView 移植进 RepositoriesView tabs（替换占位）
9. i18n 补充 + web build + desktop build 全绿
10. 手工冒烟验收 + README 更新

---

## 8. 风险与对策

| 风险 | 对策 |
|------|------|
| Web 端现有组件依赖 router（useParams/useNavigate）移植到 desktop 需剥离 | desktop 端用 state 传 repoId/prNumber；路由逻辑仅存在于 web 层 |
| 传输进 desktop 后 interface 与服务器不一致 | 代理透传不解析 body，天然兼容；以真实后端验收为准 |
| issues/PR 标签显示依赖后端返回字段 | `labels` 字段已存在于 issue/PR 返回结构与既有 store；无标签时优雅降级 |
| 合并（merge）联调需真实分支冲突等 | 手工验收涵盖 handle merge 成功/失败路径 |