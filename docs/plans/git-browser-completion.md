# Git 浏览器能力补齐（Commit Graph / Blame / Tag / Compare / Web Diff）

> **创建日期**: 2026-09-28
> **背景**: 2026-09-28 盘点 `dev` 分支发现——仓库底座（pygit2 bare 仓库 + 主库镜像）与
> 提交历史、分支、diff 的**底层能力已具备**，但相比 GitHub/GitLab 仍缺四类平台必备件：
> **提交图/分支网络**、**Blame 行级追溯**、**Tag 独立管理**、**Compare 对比视图**，
> 以及 **Web 端 commit/PR diff 渲染**（后端与桌面端已有）。
> **关联**: `docs/plans/todos.md`、`docs/wiki/01-overview.md`（产品能力矩阵）、`docs/api/http/README.md`
> **开发方针**: TDD；新 error_code 同步补 `core/i18n.py` ERROR_MESSAGES；禁止硬编码兜底假数据。

---

## 一、盘点结论（2026-09-28）

| 能力 | 现状 | 缺口 |
|------|------|------|
| 提交历史 | ✅ 后端 `repository_browser_service.get_commits` + `commit_controller` | — |
| 分支管理 | ✅ `branch_controller`（list/create/delete/protect/default） | — |
| 提交间 diff | ✅ `GET /{repo_id}/diff?head&base&path`（pygit2，含 hunks） | Web 未接 |
| PR diff | ⚠️ service `get_pr_diff`/`get_pr_file_diff` 已实现 | **未暴露 controller 路由**、Web 未接 |
| 提交图/分支网络 | ❌ | 无 graph 端点，`parent_hashes` 未用于拓扑渲染 |
| Blame | ❌ | 全库无实现 |
| Tag 管理 | ⚠️ `git_utils` 有 create/list/get/delete | 仅随 Release 隐式创建，**无独立端点** |
| Compare | ❌ | 无 base...head 对比端点（提交列表 + 合并基） |

> **桌面端**: `client/desktop/internal/git` 已具备本地 `status/diff/log/commit/push/pull/branch`，
> 本轮后端能力落地后按 `docs/plans/desktop-port-sync.md` 惯例跟进可视侧。

---

## 二、目标 API 契约（后端优先）

### B1 · Blame（行级追溯）

```
GET /api/v1/repositories/{repo_id}/blame?path={file}&ref={branch|sha}
→ { path, ref, hunks: [ { final_start_line_number, lines_in_hunk,
        orig_start_line_number, orig_commit_id, final_commit_id,
        orig_path, boundary,
        commit: { sha, summary, message, author:{name,email,date} } } ], is_empty? }
```

### B2 · Commit Graph（分支网络）

```
GET /api/v1/repositories/{repo_id}/graph?ref=HEAD&limit=100
→ { ref, is_empty?, commits: [ { sha, parents:[...], summary, message,
        author:{...}, committer:{...}, date, labels:["HEAD","main","tag: v1.0"], is_merge } ] }
```

- 拓扑序（`SortMode.TOPOLOGICAL`）；`labels` 聚合 HEAD / 本地分支 / tag，供前端画泳道与引用标签。
- 前端据 `parents` 自行计算 lane 布局（后端只出节点+边，不做像素）。

### B3 · Compare（跨 ref 对比）

```
GET /api/v1/repositories/{repo_id}/compare?base={ref}&head={ref}&path={file?}
→ { base, head, merge_base, ahead_by, commits:[...], files:[...], stats:{...} }
```

- `commits` = head 可达、base 不可达的提交（`walker.hide(base)`）。
- `files/stats` 复用 diff 序列化（与 `/{repo_id}/diff` 同构）。

### B4 · Tag 管理（独立资源）

```
GET    /api/v1/repositories/{repo_id}/tags?pattern=v1.*   # 公开
GET    /api/v1/repositories/{repo_id}/tags/{tag_name}      # 公开
POST   /api/v1/repositories/{repo_id}/tags                 # 需认证
       body { name, target, message? }   # message 空=轻量标签
DELETE /api/v1/repositories/{repo_id}/tags/{tag_name}      # 需认证
```

- 复用 `utils/git_utils.{list_git_tags,get_git_tag,create_git_tag,delete_git_tag}`。
- 目标提交缺省用 HEAD（`get_head_commit`）。

### B5 · PR Diff 路由暴露

```
GET /api/v1/repositories/{repo_id}/pull-requests/{pr_number}/diff
GET /api/v1/repositories/{repo_id}/pull-requests/{pr_number}/diff/{file_path:path}
```

- 直接调用既有 `pull_request_service.get_pr_diff` / `get_pr_file_diff`（service 已就绪）。

---

## 三、批次计划

| 批次 | 内容 | 类型 | 状态 |
|------|------|------|------|
| **B1** | Blame service + controller + i18n + 测试 | 后端 | ✅ 2026-09-28 |
| **B2** | Commit Graph service + controller + 测试 | 后端 | ✅ 2026-09-28 |
| **B3** | Compare service + controller + 测试 | 后端 | ✅ 2026-09-28 |
| **B4** | Tag controller + 路由注册 + 测试 | 后端 | ✅ 2026-09-28 |
| **B5** | PR diff 路由暴露 + 测试 | 后端 | ✅ 2026-09-28 |
| **F1** | Web `repositories.ts` 接 blame/graph/compare/tags/diff API | 前端 | ✅ 2026-09-28 |
| **F2** | Web 仓库页新增 Commits/Branches/Tags/Compare 视图 + 提交图 + Blame | 前端 | ✅ 2026-09-28 |
| **F3** | Web PR 详情页接 PR diff（文件列表 + 行级 hunk） | 前端 | ✅ 2026-09-28 |
| **D1** | Desktop 端口图/Blame/Compare 视图（对齐 web） | 桌面 | ✅ 2026-09-28 |
| **P** | 代码 Wiki（`docs/plans/agent-integration.md` 规划，独立立项） | 产品 | ⬜ 未定 |

### 建议迭代顺序

1. **后端 B1–B5**（本轮完成）——一次性补齐所有 API，前端可并行接线。
2. **F1**（纯 API 封装，低风险）→ **F2/F3**（视图）。
3. **D1** 按 `desktop-port-sync.md` 登记移植。

---

## 四、落地记录（2026-09-28）

- **service**: `services/repository_browser_service.py`
  - 抽出 `_serialize_diff(diff)` 复用（`get_diff` 与新 `compare` 共用）。
  - 新增 `get_blame` / `get_commit_graph` / `compare`。
- **controller**: `controller/repository_browser_controller.py` 新增
  `GET /{repo_id}/blame`、`GET /{repo_id}/graph`、`GET /{repo_id}/compare`。
- **tag**: 新增 `controller/tag_controller.py`，在 `api/routes_config.py` 于
  `repository_controller`（`/{owner}/{repo}` 通配）**之前**注册。
- **pr diff**: `controller/pull_request_controller.py` 新增 diff 两路由。
  - **顺带修复既有缺陷**：`PullRequest` 模型无 `base_commit`/`head_commit` 列，
    原 `get_pr_diff`/`get_pr_file_diff` 访问 `pr.base_commit` 必然 AttributeError，
    被吞成 `pr_diff_failed` 400。现改为按 `target_branch`/`source_branch`
    当前 tip 用新增的 `utils.git_utils.resolve_ref_commit()` 解析；分支缺失给
    `pr_base_branch_not_found` / `pr_source_branch_not_found` 明确 400。
- **i18n**: `core/i18n.py` 补 `blame_failed` / `tag_*` / `pr_base_branch_not_found`
  / `pr_source_branch_not_found` 文案。
- **测试**: `tests/test_repo_browser_completion.py`（blame 6 + graph 5 + compare 4）、
  `tests/test_tag_api.py`（13）、`tests/test_pr_diff_controller.py`（5）。

### 验证

- 定向：`tests/test_repo_browser_completion.py tests/test_tag_api.py
  tests/test_pr_diff_controller.py tests/test_pr_diff_async.py
  tests/test_repo_browser_controller.py` → **65 passed**。
- 全量：`docker compose --profile test run --rm test python -m pytest tests/ -q`
  → **1427 passed / 3 skipped**（无回归）。

---

## 五、进度追踪

- [x] B1 Blame
- [x] B2 Commit Graph
- [x] B3 Compare
- [x] B4 Tag 管理
- [x] B5 PR Diff 路由
- [x] F1 Web API 接线
- [x] F2 Web 仓库视图
- [x] F3 Web PR diff 渲染
- [x] D1 Desktop 移植
- [ ] P 代码 Wiki

---

## 六、前端落地（F1–F3，2026-09-28）

### API

- `client/web/src/api/repositories.ts`：新增 `getDiff` / `getBlame` / `getGraph` /
  `getCompare` / `listTags` / `getTag` / `createTag` / `deleteTag` /
  `deleteBranch` / `setDefaultBranch` 及类型（DiffFile/DiffHunk/BlameHunk/
  CommitGraphNode/RepoTag/CompareResponse）。
- `client/web/src/api/pullRequests.ts`：新增 `getDiff` / `getFileDiff` 及类型。

### 组件

- `utils/diff.ts` — 统一 diff 文本解析器（PR patch → 结构化 DiffFile）。
- `components/repo/DiffView.tsx` — 结构化逐文件 diff 渲染（增删行高亮、行号、折叠）。
- `components/repo/CommitsTab.tsx` — 提交历史（分支选择 + 分页）＋ **提交图**（拓扑序 + 泳道 + 引用标签）。
- `components/repo/BranchesTab.tsx` — 分支列表 + 默认/保护徽标 + 保护切换 + 删除。
- `components/repo/TagsTab.tsx` — 标签列表 + 新建（含附注）+ 删除。
- `components/repo/CompareTab.tsx` — base/head 选择 + 领先提交 + 文件 diff。
- `components/repo/BlameView.tsx` — 代码查看器内 **Blame** 追溯（行级作者/提交边栏）。
- `routes/repositories/index.tsx` — 新增 提交/分支/标签/对比 tab；文件查看器加 Blame 开关。
- `routes/pull-requests/[prNumber].tsx` — 新增「文件变更」区块（文件列表 + 行级 hunk）。
- i18n：zh/en 各补 `app.repositories.tabs.{commits,branches,tags,compare}`、
  `app.repositories.gitBrowser.*`、`app.pullRequests.detail.changes`。

### 前端验证

- `pnpm lint` ✅ / `pnpm build`（tsc + vite）✅ / `pnpm test`（37 passed）✅。
- 网关镜像在容器内重建成功并重建容器；`/graph`、`/tags`、`/compare`、`/blame`、
  `/diff` 经网关实测 HTTP 200。

> 注意：组件 `BlameView` 的引用参数命名为 `gitRef` 而非 `ref`——`ref` 是 React
> 保留 JSX 属性，会误导 `eslint-plugin-react-hooks` 的 refs 规则。

---

## 六·bis、桌面端落地（D1，2026-09-28）

桌面端仓库浏览全部经本地 Go 网关 `proxyRequest` 转发到目标服务器（首个参数为
`serverId`），本轮无 Go 改动。

- `api/repositories.ts`：新增 `getDiff/getBlame/getGraph/getCompare/listTags/getTag/
  createTag/deleteTag/deleteBranch/setDefaultBranch` + 类型（与 web 同构）。
- `api/pullRequests.ts`：新增 `getDiff/getFileDiff` + 类型。
- `utils/diff.ts`：统一 diff 解析器（与 web 相同）。
- `views/repositories/`：新增 `RepoDiffView`、`GitCommitsTab`（含提交图）、
  `GitBranchesTab`、`GitTagsTab`、`GitCompareTab`、`GitBlameView`。
- `views/repositories/RepositoriesView.tsx`：新增 提交/分支/标签/对比 tab +
  文件查看器 Blame 开关（引用参数 `gitRef`）。
- `views/repositories/PullRequestDetail.tsx`：新增「文件变更」区块。
- i18n：zh/en 各补 `app.repositories.tabs.{commits,branches,tags,compare}`、
  `app.repositories.gitBrowser.*`、`app.pullRequests.detail.changes`。

### 桌面端验证

- `pnpm build`（`tsc && vite build`）✅（仅既有 chunk 体积告警）。
- 桌面端无独立 lint/测试脚本；类型检查随 build 通过。


---

## 七、环境恢复记录（本次副作用）

本次 `--build app` 引入了两个既有环境/依赖问题，已一并修复：

1. **SQLAlchemy 2.1 默认驱动变更**：`pyproject.toml` 约束为 `sqlalchemy>=2.0.34`
   且无上限，重建后解析到 2.1.1；2.1 起 `postgresql://` 默认 DBAPI 由 psycopg2
   改为 psycopg3（未安装）→ app 启动崩溃。修复：在
   `utils/db_migrate._to_sync_db_url`、`utils/init_database._to_sync_db_url`、
   `alembic/env.py::_to_sync_database_url` 显式归一化为 `postgresql+psycopg2://`
   （与 `models/__init__.py` / `utils/db_validation.py` 既有约定一致）。
   测试：`tests/test_db_url_sync.py`。
2. **迁移版本分叉**：运行中的 PostgreSQL 由 `dev-Agent` 分支初始化
   （head=`f0a1b2c3d4e5`，含 search chunks/refs、agent、embeddings 迁移），
   而 `dev` 的迁移链 head=`c9d0e1f2a3b4` 且不含这些 revision，导致
   `Can't locate revision`。`dev` schema 是 `dev-Agent` 的子集，故将
   `alembic_version` 直接置为 `c9d0e1f2a3b4` 后 app 正常启动。
   **回切 `dev-Agent` 时**需把 `alembic_version` 置回 `f0a1b2c3d4e5`
   （或合并两分支迁移链），否则 alembic 会因表已存在而失败。

