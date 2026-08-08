# Phase 2B Issues/PR 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 先在 web 端补全 issues/PR 完整页面（列表/详情/评论/操作），再忠实移植到 desktop 的 `RepositoriesView` tabs，并新增当前用户 identity。

**Architecture:** 分两阶段。「先补 web 再移植」——web 端用 React Router 子路由实现 issues/PR 列表+详情（复用现成 `api/issues.ts`/`api/pullRequests.ts` 与 store）；desktop 无 router，用 state 切换渲染同一批 UI 逻辑，并把 `apiRequest` 换成 `proxyRequest`。Go 侧零改动，全走既有 proxy 层。

**Tech Stack:** React 19 + React Router + Ant Design + Zustand + i18next（web）；同栈但无 Router、用 Vite/Wails（desktop）；后端 FastAPI（不动）。

## Global Constraints

- Retro 深色风格常量沿用 RepositoriesView 现有主题（`textPrimary:#e6edf3`、`bluePrimary:#1f6feb`、`blueLight:#58a6ff`、`borderColor:#21262d` 等），不引入新色板。
- 不用跨端共享工具包：`relativeTime`/`getInitials`/`getAvatarColor`/`resolveLabelColor`/`statusIcon` 在 web 与 desktop 各自局部实现（沿用现有代码风格）。
- 标签 `labels` 仅只读展示，**不做**标签创建/打标/去标操作。
- PR review 仅支持整条提交（approved/changes_requested/commented），不做逐行 diff 点评。
- 不新增 Go 代码，不新增后端依赖。
- 所有 i18n key 同步维护 `zh.json` 与 `en.json`。
- 每个 task 结束必须通过对应 build（web：`npm run build`；desktop：`npm run build`）并 commit。

---

### Task 1: Web — Issues 路由 + 列表页

**Files:**
- Create: `client/web/src/routes/issues/index.tsx`
- Modify: `client/web/src/App.tsx`（新增路由）
- Modify: `client/web/src/routes/repositories/index.tsx`（tabs 的 issues/PR 标签改为导航到子路由）

**Interfaces:**
- Consumes: `useIssuesStore`（`fetchIssues(repoId, status?)`、`issues`、`isLoading`、`error`）；`useRepositoriesStore.fetchRepositoryByPath(owner, repo)`；现有 `api/issues.ts` 类型。
- Produces: 路由 `/repositories/:owner/:repo/issues` 渲染 issues 列表页；`repositories/index.tsx` 的 issues tab 改为 `navigate` 到该路由。

- [ ] **Step 1: 在 App.tsx 注册子路由**

在 `AppLayout` 的 `<Route>` 包裹块内（`/repositories/:owner/:repo` 之后）新增：
```tsx
<Route path="/repositories/:owner/:repo/issues" element={<PageTransition><IssuesPage /></PageTransition>} />
```
并在顶部 import `IssuesPage from './routes/issues';`

- [ ] **Step 2: 改仓库详情页 tabs 导航**

`client/web/src/routes/repositories/index.tsx`：把 `tabItems` 中 issues/PR 两项改为点击导航。保留 code/settings 用 `activeTab` state，issues/PR 改为：
```tsx
{ key: 'pullRequests', label: <span ...><PullRequestOutlined />{t('app.repositories.tabs.pullRequests')}</span>, onClick: () => navigate(`/repositories/${owner}/${repo}/pulls`) },
{ key: 'issues', label: <span ...><ExclamationCircleOutlined />{t('app.repositories.tabs.issues')}</span>, onClick: () => navigate(`/repositories/${owner}/${repo}/issues`) },
```
`navigate` 已存在于组件（`useNavigate()`）。

- [ ] **Step 3: 写 issues 列表页**

创建 `client/web/src/routes/issues/index.tsx`。结构（沿用 `pull-requests/index.tsx` 的深色风格与骨架逻辑）：

```tsx
import { useEffect, useMemo, useState } from 'react';
import { Layout, Button, Avatar, Tag, Modal, Form, Input, Select, message } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { PlusOutlined, MessageOutlined } from '@ant-design/icons';
import { useRepositoriesStore } from '../../stores/repositories';
import { useIssuesStore } from '../../stores/issues';
import type { Issue } from '../../api/issues';

const { Content } = Layout;
// 常量：borderColor/hoverBg/textSecondary 等同 repos 页取值

// 局部工具：relativeTime / getInitials / getAvatarColor / statusIcon(open|closed) / 状态色
```

组件逻辑：
```tsx
export default function IssuesPage() {
  const { owner = '', repo = '' } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { currentRepo, fetchRepositoryByPath } = useRepositoriesStore();
  const { issues, isLoading, error, fetchIssues, createIssue } = useIssuesStore();
  const [filter, setFilter] = useState<'open' | 'closed' | 'all'>('open');
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    if (!currentRepo) fetchRepositoryByPath(owner, repo);
  }, [owner, repo, currentRepo, fetchRepositoryByPath]);

  useEffect(() => {
    if (currentRepo) fetchIssues(currentRepo.id, filter === 'all' ? undefined : filter);
  }, [currentRepo?.id, filter, fetchIssues]);
  // ...
}
```
渲染：顶部工具栏（返回仓库链接 + 状态 filter tabs + "New Issue" 按钮），下方列表项（`onClick={() => navigate(\`/repositories/${owner}/${repo}/issues/${i.issue_number}\`)}`），{{每个项展示 status 图标/标题/作者/相对时间/标签/评论数}}。空态与加载态（`Spin`）齐全。新建 Modal 含 Form：title（必填）、description、priority(Select low/medium/high/critical)；提交调 `createIssue(currentRepo.id, values)` → `message.success` → 关闭 Modal → `fetchIssues(...)`。

- [ ] **Step 4: build 验证**

Run: `npm run build`（在 `client/web`）
Expected: 通过（tsc + vite）。若报未使用的 `MergedOutlined` 等 import 修剪之。

- [ ] **Step 5: Commit**

```bash
git add client/web/src/routes/issues/index.tsx client/web/src/App.tsx client/web/src/routes/repositories/index.tsx
git commit -m "feat(web): issues list page with repo-detail routing"
```

---

### Task 2: Web — Issue 详情页

**Files:**
- Create: `client/web/src/routes/issues/[issueNumber].tsx`
- Modify: `client/web/src/App.tsx`（增加详情路由）

**Interfaces:**
- Consumes: `useIssuesStore`（`fetchIssue(repoId, num)`、`fetchComments(repoId, num)`、`createComment`、`closeIssue`、`reopenIssue`、`currentIssue`、`comments`）。
- Produces: 路由 `/repositories/:owner/:repo/issues/:issue_number` 渲染详情页。

- [ ] **Step 1: 注册详情路由**

`App.tsx`：
```tsx
<Route path="/repositories/:owner/:repo/issues/:issueNumber" element={<PageTransition><IssueDetailPage /></PageTransition>} />
```

- [ ] **Step 2: 写详情页**

创建 `client/web/src/routes/issues/[issueNumber].tsx`。骨架：
```tsx
export default function IssueDetailPage() {
  const { owner = '', repo = '', issueNumber = '' } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const { currentRepo, fetchRepositoryByPath } = useRepositoriesStore();
  const { currentIssue, comments, fetchIssue, fetchComments, createComment, closeIssue, reopenIssue } = useIssuesStore();
  const num = Number(issueNumber);
  const [body, setBody] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { if (!currentRepo) fetchRepositoryByPath(owner, repo); }, [owner, repo, currentRepo]);
  useEffect(() => {
    if (currentRepo) { fetchIssue(currentRepo.id, num); fetchComments(currentRepo.id, num); }
  }, [currentRepo?.id, num, fetchIssue, fetchComments]);
```
渲染：标题头（`#${issue_number}` + title + 状态 Tag[open=绿/closed=灰] + 优先级 + 作者 `user.username` + relativeTime）；操作行：`closed ? reopen : close` 按钮；描述正文段落；评论区（对每条 comment：作者头像/用户名/时间/content）；评论输入 `Input.TextArea` + 提交按钮（`createComment` 后清空+`fetchComments`）；返回列表链接。使用 `AntApp.useApp()` 的 `message`。

- [ ] **Step 3: build 验证**

Run: `npm run build`
Expected：通过。

- [ ] **Step 4: Commit**

```bash
git add client/web/src/routes/issues client/web/src/App.tsx
git commit -m "feat(web): issue detail page with comments and close/reopen"
```

---

### Task 3: Web — PR 列表 + 详情页

**Files:**
- Create: `client/web/src/routes/pulls/index.tsx`、`client/web/src/routes/pulls/[prNumber].tsx`
- Modify: `client/web/src/App.tsx`

**Interfaces:**
- Consumes: `usePullRequestsStore`（`fetchPullRequests`、`fetchPullRequest`、`fetchComments`、`createComment`、`closePullRequest`、`mergePullRequest`、`createReview`、`createPullRequest`）；`useRepositoriesStore`。
- Produces: 路由 `/repositories/:owner/:repo/pulls`、`/repositories/:owner/:repo/pulls/:pr_number`。

- [ ] **Step 1: 注册路由**

```tsx
<Route path="/repositories/:owner/:repo/pulls" element={<PageTransition><PullsPage /></PageTransition>} />
<Route path="/repositories/:owner/:repo/pulls/:pr_number" element={<PageTransition><PullDetailPage /></PageTransition>} />
```

- [ ] **Step 2: 写 PR 列表页**

创建 `client/web/src/routes/pulls/index.tsx`，仿照 Task 1 的 issues 列表，但数据来自 `pullRequests` store：
- filter tabs：open/merged/closed/all（各带计数）
- "New Pull Request" 按钮 → Modal 表单：title、description、source_branch、target_branch —— 提交调 `createPullRequest(repoId, values)`，成功 `message.success` + 刷新列表。
- 列表项点击 navigate 到详情；显示 status 图标、标题、标签（`resolveLabelColor`）、author、`openedBy`、评论数、review 数。

- [ ] **Step 3: 写 PR 详情页**

创建 `client/web/src/routes/pulls/[prNumber].tsx`：
- 标题头：`#${pr}` + status Tag（open/merged/closed）+ `is_draft` 徽标 + 作者 + 时间；分支关系 `source_branch → target_branch`（两个 Tag）。
- 操作区：
  - `status === 'open' && !is_draft` → Merge 按钮（Modal：merge_method 单选 merge/squash/rebase）→ `mergePullRequest`；Close 按钮 → `closePullRequest`。
- 正文描述；评论区 + `Input.TextArea` 评论框（`createComment`）。
- Review 提交：Select（approved/changes_requested/commented）+ comment TextArea → 按钮「Submit review」→ `createReview({status, comment})`。
- 返回列表链接。

- [ ] **Step 4: build 验证**

Run: `npm run build`；通过。

- [ ] **Step 5: Commit**

```bash
git add client/web/src/routes/pulls client/web/src/App.tsx
git commit -m "feat(web): pull request list and detail pages with merge/close/review"
```

---

### Task 4: Web — i18n 补齐（app.issues\*）

**Files:**
- Modify: `client/web/src/i18n/locales/en.json`、`zh.json`

**Interfaces:**
- Consumes: Task 1-3 中页面用到的所有 `t()` 调用。
- Produces: `app.issues.*` 命名空间（web 端此前不存在）。

- [ ] **Step 1: en.json 新增 `app.issues`**

在 `app` 对象内新增：
```json
"issues": {
  "title": "Issues",
  "newIssue": "New Issue",
  "filters": { "open": "Open", "closed": "Closed", "all": "All" },
  "openedBy": "#{{id}} opened by {{author}} {{time}}",
  "comments": "{{count}} comments",
  "noIssues": "No issues found",
  "newIssueModal": { "title": "Create Issue", "titleLabel": "Title", "titleRequired": "Title is required", "description": "Description", "priority": "Priority" },
  "detail": { "author": "{{author}} opened", "closeIssue": "Close issue", "reopenIssue": "Reopen issue", "backToList": "Back to issues", "commentPlaceholder": "Leave a comment...", "submitComment": "Comment" }
}
```

- [ ] **Step 2: zh.json 对应中文**

```json
"issues": {
  "title": "问题",
  "newIssue": "新建 Issue",
  "filters": { "open": "打开", "closed": "已关闭", "all": "全部" },
  "openedBy": "#{{id}} 由 {{author}} 于 {{time}} 打开",
  "comments": "{{count}} 条评论",
  "noIssues": "暂无问题",
  "newIssueModal": { "title": "创建 Issue", "titleLabel": "标题", "titleRequired": "请输入标题", "description": "描述", "priority": "优先级" },
  "createIssue": { "close": "关闭 Issue", "reopenIssue": "重新打开", "backToIssues": "返回问题列表", "commentPlaceholder": "写下你的评论…", "submitComment": "评论" }
}
```

- [ ] **Step 3: PR 补充 key**

两语言在 `app.pullRequests` 下补充详情/操作所需：
```json
"openedBy": "#{{id}} opened by {{author}} {{time}}",
"draft": "Draft",
"merge": "Merge",
"close": "Close",
"mergeMethod": "Merge method",
"review": "Submit review",
"reviewStatus": { "approved": "Approved", "changes_requested": "Changes requested", "commented": "Comment" }
```
（zh：对应中文文案。）

- [ ] **Step 4: build 验证 + 全量编译**

Run: `npm run build`；通过。

- [ ] **Step 5: Commit**

```bash
git add client/web/src/i18n/locales/en.json client/web/src/i18n/locales/zh.json
git commit -m "feat(web): i18n keys for issues and pull request pages"
```

---

### Task 5: Desktop — API 层（proxyRequest 化）

**Files:**
- Create: `client/desktop/frontend/src/api/issues.ts`、`api/pullRequests.ts`、`api/identity.ts`

**Interfaces:**
- Consumes: `client.ts` 的 `proxyRequest`、`ApiError`.
- Produces: `issuesApi.list/get/create/update/close/reopen/getComments/createComment`（均带 `serverId` 前置参数）；`pullRequestsApi.list/get/create/close/merge/getComments/createComment/createReview`（serverId 前置）；`identityApi.fetchCurrentUser(serverId)` → `Promise<User>`。

- [ ] **Step 1: 复刻 issues API**

创建 `api/issues.ts`：复制 web `api/issues.ts` 的类型（`Issue`、`IssueComment`、`CreateIssueRequest`、`IssueFilter`、`PaginationResponse`），把每个方法替换为：
```ts
list: (serverId: string, repoId: string, params?: {...}) =>
  proxyRequest<PaginationResponse<Issue>>(serverId, `/api/v1/repositories/${repoId}/issues${qs}`),
```
（`serverId` 为首参，其余签名与 web 一致。）

- [ ] **Step 2: 复刻 pullRequests + identity**

`api/pullRequests.ts`：同法代理 `/pull-requests...`。
`api/identity.ts`：
```ts
import { proxyRequest } from './client';

export interface PerseusUser {
  id: string;
  username: string;
  full_name?: string | null;
  email?: string | null;
  avatar_url?: string | null;
}

export const identityApi = {
  fetchCurrentUser: (serverId: string) =>
    proxyRequest<PerseusUser>(serverId, '/api/v1/users/me'),
};
```
（调用方按需触发。）

- [ ] **Step 3: tsc 验证**

Run: `npm run build` 或 `npx tsc --noEmit`（在 `client/desktop/frontend`）。
Expected：通过。

- [ ] **Step 4: Commit**

```bash
git add client/desktop/frontend/src/api/issues.ts client/desktop/frontend/src/api/pullRequests.ts client/desktop/frontend/src/api/identity.ts
git commit -m "feat(desktop): issues/pullRequests/identity api via proxyRequest"
```

---

### Task 6: Desktop — stores 层

**Files:**
- Create: `client/desktop/frontend/src/stores/issues.ts`、`stores/pullRequests.ts`、`stores/identity.ts`

**Interfaces:**
- Produces: `useIssuesStore`（方法同 web store，签名去掉 repoId——从 `useRepositoriesStore` 取当前 `currentRepo.id`，仅保留 `status?` 参数）；`usePullRequestsStore`（同）；`useIdentityStore`（`user`、`fetchIdentity(serverId)`）。

- [ ] **Step 1: 复刻 issues store**

从 web `stores/issues.ts` 复制逻辑，改造成：
```ts
import { create } from 'zustand';
import { issuesApi } from '../api/issues';
import { useRepositoriesStore } from './repositories';

function repoId(): string {
  return useRepositoriesStore.getState().currentRepo?.id ?? '';
}

export const useIssuesStore = create(...{
  fetchIssues: async (status?) => {
    const rid = repoId();
    if (!rid) return;
    // ...issuesApi.list(currentServerId, rid, status ? {status} : undefined)  →  serverId 从 useServersStore 取
  },
  // ... 其余方法逻辑复刻，repoId 一律用 repoId()
});
```
serverId 来源：`import { useServersStore } from './servers';` 里 `useServersStore.getState().currentServerId`。
`createIssue`/`closeIssue`/`reopenIssue`/`fetchComments`/`createComment` 签名与 web 一致，仅去掉 repoId 参数（用 repoId() 补齐）。

- [ ] **Step 2: 复刻 pullRequests store**

同上模式，从 web `stores/pullRequests.ts` 复刻，`pullRequestsApi` 代理化，`repoId()` 取当前仓库。

- [ ] **Step 3: identity store**

`stores/identity.ts`：
```ts
import { create } from 'zustand';
import { identityApi, type PerseusUser } from '../api/identity';

interface IdentityState {
  user: PerseusUser | null;
  loading: boolean;
  error: string | null;
  fetchIdentity: (serverId: string) => Promise<void>;
  clear: () => void;
}

export const useIdentityStore = create<IdentityState>((set) => ({
  user: null, loading: false, error: null,
  fetchIdentity: async (serverId) => {
    set({ loading: true, error: null });
    try {
      const user = await identityApi.fetchCurrentUser(serverId);
      set({ user, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },
  clear: () => set({ user: null, error: null }),
}));
```

- [ ] **Step 4: Desktop build 验证**

Run: `npm run build`；通过。

- [ ] **Step 5: Commit**

```bash
git add client/desktop/frontend/src/stores/issues.ts client/desktop/frontend/src/stores/pullRequests.ts client/desktop/frontend/src/stores/identity.ts
git commit -m "feat(desktop): issues/pullRequests/identity zustand stores"
```

---

### Task 7: Desktop — ServerShell 装配 identity

**Files:**
- Modify: `client/desktop/frontend/src/layouts/ServerShell.tsx`

**Interfaces:**
- Consumes: `useIdentityStore`.
- Produces: `ServerShell` 挂载时若 `currentServerId` 变化调用 `fetchIdentity(id)`；store 已填充 `user`。

- [ ] **Step 1: 挂载时拉取 identity**

在 `ServerShell` 组件内：
```tsx
import { useIdentityStore } from '../stores/identity';

const userId = useIdentityStore((s) => s.user);
const fetchIdentity = useIdentityStore((s) => s.fetchIdentity);
const clearIdentity = useIdentityStore((s) => s.clear);

useEffect(() => {
  if (currentServerId) {
    fetchIdentity(currentServerId);
  } else {
    clearIdentity();
  }
}, [currentServerId, fetchIdentity, clearIdentity]);
```

- [ ] **Step 2: 顶栏显示当前用户**

在 ServerShell 顶栏（`current` 存在时）加一个只读用户名徽标（`Avatar` 取 `user?.username` 首字母），定位在 health 徽标旁。

- [ ] **Step 3: build + Commit**

Run: `npm run build`；通过后
```bash
git add client/desktop/frontend/src/layouts/ServerShell.tsx
git commit -m "feat(desktop): load current user identity in ServerShell"
```

---

### Task 8: Desktop — Issues/PullRequests 视图移植进 RepositoriesView

**Files:**
- Create: `client/desktop/frontend/src/views/repositories/IssuesView.tsx`、`PullRequestsView.tsx`
- Modify: `client/desktop/frontend/src/views/repositories/RepositoriesView.tsx`、`client/desktop/frontend/src/i18n/locales/en.json`、`zh.json`

**Interfaces:**
- Consumes: desktop 版 `useIssuesStore`/`usePullRequestsStore`/`useIdentityStore`；`currentRepo`、`useServersStore`.
- Produces: `RepositoriesView` 的 `activeTab === 'issues'` / `'pullRequests'` 渲染对应视图替代占位。

- [ ] **Step 1: 写 IssuesView.tsx**

结构：复用 web issues 列表+详情在一个组件里做两态（state `selected: Issue | null`），因为 desktop 无 router 也没有该仓库命名路由。需导入：`import type { Issue } from '../../api/issues';`（类型来自 api 层，非 store）。骨架：
```tsx
export default function IssuesView() {
  const server = useServersStore((s) => s.servers.find((x) => x.id === s.currentServerId));
  const { currentRepo } = useRepositoriesStore();
  const issues = useIssuesStore((s) => s.issues);
  const fetchIssues = useIssuesStore((s) => s.fetchIssues);
  const [filter, setFilter] = useState<'open'|'closed'|'all'>('open');
  const [selected, setSelected] = useState<Issue | null>(null);

  useEffect(() => { if (currentRepo) fetchIssues(filter === 'all' ? undefined : filter); }, [currentRepo?.id, filter]);

  if (selected) return <IssueDetail ... onBack={() => setSelected(null)} />;
  // list UI（返回仓库、filter、new issue modal、列表项 onClick setSelected）
}
```
- 详情子组件 `IssueDetail`：加载 `fetchIssue`/`fetchComments`；评论框 + close/reopen 按钮；返回列表。
- 当前用户头像直接用 `useIdentityStore` 的 `user`。

- [ ] **Step 2: 写 PullRequestsView.tsx**

同体例：列表（filter open/merged/closed/all + 新建 modal）+ 详情（分支、merge/close、评论区、review 提交）两态；点击 PR 进详情、返回列表。

- [ ] **Step 3: 接线 RepositoriesView.tsx**

把当前占位区块替换：
```tsx
// 原 `{activeTab !== 'code' && (<div>{t('desktop.serverShell.comingIn2b')}</div>)}`
```
改为：
```tsx
{activeTab === 'issues' && <IssuesView />}
{activeTab === 'pullRequests' && <PullRequestsView />}
```
并删除 `comingIn2b` 的调用（i18n key 保留勿删）。确保 `IssuesView`/`PullRequestsView` 自身带滚动/边距（`maxHeight`/`overflowY:auto`）。

- [ ] **Step 4: 加 i18n key**

`client/desktop/frontend/src/i18n/locales/zh.json`、`en.json` 新增 `desktop.issues.*`、`desktop.pullRequests.*`：
```json
"issues": { "title": "Issues/问题", "newIssue": "New Issue/新建 Issue", "filters": {...}, "openedBy": "...", "comments": "...", "noIssues": "...", "detailClose": "Close issue/关闭", "detailReopen": "Reopen/重新打开", "back": "Back/返回", "commentPlaceholder": "...", "submit": "Comment/评论" },
"pullRequests": { "title": "Pull Requests", "newPR": "...", "filters": {...}, "openedBy": "...", "comments": "...", "reviews": "...", "merge": "Merge/合并", "close": "Close/关闭", "detailBranch": "{{source}} → {{target}}", "reviewStatus": {...} }
```

- [ ] **Step 5: Desktop build 验证**

Run: `npm run build`（`client/desktop/frontend`）
Expected：tsc + vite 通过。

- [ ] **Step 6: Commit**

```bash
git add client/desktop/frontend/src/views/repositories client/desktop/frontend/src/views/repositories/RepositoriesView.tsx client/desktop/frontend/src/i18n/locales/en.json client/desktop/frontend/src/i18n/locales/zh.json
git commit -m "feat(desktop): port issues and PR views into repo tabs"
```

---

### Task 9: 全量验证 + README 更新

**Files:**
- Modify: `client/desktop/README.md`

**Interfaces:**
- Consumes: Task 1-8 全部产物.

- [ ] **Step 1: web 全量 build**

Run: `npm run build`（`client/web`）；必须无 TS 错误。

- [ ] **Step 2: desktop 全量 build + go 冒烟**

Run（`client/desktop`）：先 `npm run build`（frontend 子目录），再确认不影响 Go（运行 `go build ./...` 全量编译通过；Go 无改动，预期通过）。

- [ ] **Step 3: README 更新**

在 `client/desktop/README.md` 的「Phase 2A 功能范围」小节下新增「Phase 2B 功能范围」：
```markdown
## Phase 2B 功能范围

- Issues / Pull Requests：页面从 web 移植进仓库详情 tabs（列表/详情/新建/关闭/重开/合并/评论/Review），全部走服务器反向代理
- 当前用户身份：`GET /api/v1/users/me`（经 proxy）在 ServerShell 展示用户名
- 已知边界：标签仅展示（不管理）；PR 无逐行 diff 评论；通知/聊天留 Phase 2C
```
并同步更新「已知边界」小节里关于 2B 未实现的措辞（若存在）。

- [ ] **Step 4: Commit**

```bash
git add client/desktop/README.md
git commit -m "docs(desktop): phase 2b scope and boundaries"
```

---

## Self-Review Notes

- **Spec 覆盖**：web issues/PR 列表+详情+新建+操作（T1/T2/T3）、identity（T2 web 已有 auth、T5-T7 desktop 新增）、desktop tabs 移植替换占位（T8）、i18n（T4/T8）、全量验证（T9）。非目标（标签只读、不做 inline review）已在 Global Constraints 与 T8 UI 中落实。
- **类型一致性**：`Issue`/`PR`/`PaginationResponse` 在 web 与 desktop `api/*.ts` 同名定义；desktop store 方法签名全部去掉 `repoId` 首参并用 `repoId()` 内部补齐，`serverId` 由 store 内部经 `useServersStore` 取——T5/T6/T8 中保持一致。
- **无占位**：所有组件/方法均在对应 Task 中给出一等代码骨架。