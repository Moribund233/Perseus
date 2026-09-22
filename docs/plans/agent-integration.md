# 内置 Agent 集成规划（可行性 · 工具调用 · 代码索引）

> **日期**: 2026-09-22
> **状态**: 规划参考文档（非实施承诺）——本文件不产生代码
> **定位**: 评估在 Perseus 中内置 Agent 的可行性，界定执行模型、工具调用面、检索/token 成本与索引演进方向；按"服务端受限 / desktop 深化"两层组织。
> **关联**: [`roadmap.md`](roadmap.md)（阶段规划）、[`todos.md`](todos.md)（6.2 CI 仅外部回调决策）、[`collab-f204-vs-cwm.md`](collab-f204-vs-cwm.md)（独立网关先例）、[`redis-expansion.md`](redis-expansion.md)（Redis 设施）、[`desktop-port-sync.md`](desktop-port-sync.md)（desktop 基线）
> **代码定位基准**: `services/search_service.py` · `models/repo_search.py` · `services/repository_browser_service.py` · `api/websocket/manager.py` · `client/desktop/internal/gateway/` · `client/desktop/internal/lsp/` · `collab-gateway/server.mjs`

---

## 1. 结论速览

**一句话结论**：
把 Agent 作为**新业务域**接入，当前分层架构非常合适、接入成本低；但把它当作**请求内/后台协程里的长驻循环**则不合适——缺一个持久化异步执行层。这不是架构缺陷，而是从 Web 应用演进为"带后台作业系统"的必然一步，且仓库已有多个现成跳板。

**三维度评估**：

| 维度 | 评估 | 说明 |
|------|------|------|
| 业务接入面 | ✅ 合适 | `controller → service → model` 严格分层，Agent 即 `agent_service.py` + `agent_controller.py` + 模型，零架构改造 |
| 执行运行时 | ⚠️ 需新增 | 无任务队列；`gunicorn timeout=30` / `max_requests=10000` 杀长请求/长协程；长任务不能持请求级 `AsyncSession` |
| 检索底座 | ⚠️ 偏浅 | 现有索引为**文本检索**（`ILIKE` 子串 + 逐行正则符号），非语义代码模型；作为 Agent 检索面会显著推高 token |

**差距分层**：

| 层级 | 内容 | 端 |
|------|------|----|
| **P0 运行时** | 持久作业/执行单元、checkpoint、流式回传 | 服务端 |
| **P0 工具面** | 统一工具注册表 + server/local 执行面 + 反向 RPC | 服务端 + desktop |
| **P1 检索** | 代码块级切分、符号/引用、混合排序（降 token） | 服务端 |
| **P1 安全** | 本地执行授权边界、配额/成本、审计 | 两端 |
| **D 端深化** | LSP 工具化、本地 exec/fs/git 作为 Agent 工具面 | desktop |

---

## 2. 架构可行性评估

### 2.1 有利因素（接入面）

| 维度 | 现成能力 | 对 Agent 的意义 |
|------|----------|-----------------|
| 分层 | `controller → service → model` 单向依赖；Service 显式收 `db`/`user` | 新增 Agent 域即 `agent_service` + `agent_controller` + 模型 |
| 权限/身份 | `utils/permission_utils`、`ROLE_PRIORITY`、JWT 双令牌 + `revoked_tokens` | Agent 可建模为 bot user，复用全部鉴权；`repository_members` 天然限定可访问仓库 |
| 工具集 | `repository_browser_service`、`search_service`、`git_utils` | 即 Agent 的 read/diff/search/commit 工具，无需另造 |
| 流式通道 | `/ws` + 六个 handlers + `utils/realtime_bus`（Redis 跨 worker） | Agent token 流可直接复用 |
| 流式先例 | `build_log_entries` + `GET /logs?after_seq=N` 增量拉取 | 与 Agent 增量输出几乎同构，可照抄 |
| 阻塞处理 | 搜索索引已用 `asyncio.to_thread` 包 pygit2 | Agent 调 git 时的阻塞规避有先例 |
| 扩展点 | Alembic 迁移、`core/config.py` 分节、`error_code` i18n、controller 注册顺序 | 新增表/配置/错误码均为一等公民 |
| 破例先例 | `collab-gateway` 已是独立容器（打破"单服务"原则） | Agent 独立 worker 容器在决策上不突兀 |
| 跨进程回调先例 | `collab-gateway/server.mjs` `callApp()`（HTTP + 共享 HMAC） | 工具/执行跨进程 RPC 的形状已验证 |

### 2.2 关键障碍（执行模型）

1. **无任务队列/持久作业系统** —— 最关键。CI 已明确决策"执行外置、仅外部回调"（见 `todos.md` §6.2）。Agent 是长任务，不能塞进请求作用域；`core/gunicorn.conf.py` 的 `timeout=30` + `max_requests=10000` 会杀掉长请求/长协程。lifespan 里的后台协程（`worker_registry` 心跳、进程指标）是"固定周期"型，非"可调度/可取消/可重试"型。
2. **请求级 `AsyncSession` 耦合** —— Service 签名统一 `db: AsyncSession`（`models/async_db.py:139` 的 `get_async_db`）。长任务不能持 session，须改用 `get_async_db_context()`（`models/async_db.py:172`）自管事务并逐步 checkpoint。
3. **无模型 provider 抽象与密钥管理** —— 全局 `config.toml` 装不下 per-user/per-repo 的 API key；需加密凭据存储（可参考 `UserOAuthAccount.access_token` 加密字段做法）。
4. **无配额/成本控制** —— 只有 `ConcurrencyMiddleware` 与 `GlobalConcurrencyLimiter`（并发维度）；Agent 调用有真实成本，需 quota/budget。
5. **无沙箱** —— 若 Agent 要执行命令/代码，服务端无隔离（desktop 有 `internal/term`，`docker-write-proxy` 仅为 git ACL）。属安全专项。
6. **多 worker 状态** —— `ConnectionManager`/`presence`/`revocation_cache` 均为进程内 + Redis 兜底；Agent 会话状态同理需落 Redis。

### 2.3 评估结论

**功能域接入合适、运行时需新增执行层。** 风险集中在"执行运行时 + 安全/配额"，不在业务接入。项目已有的 Redis、WS 广播总线、外部回调 CI 模式、collab 独立容器四个跳板，使新增执行层的增量成本可控。

---

## 3. Agent 执行模型（循环放哪里）

### 3.1 候选形态

| 形态 | 说明 | 优点 | 代价 |
|------|------|------|------|
| **A. 进程内后台协程** | 请求触发后 `asyncio.create_task` 长跑 | 零新增设施 | ❌ 被 gunicorn 超时/回收杀掉；无重试/持久；多 worker 不可达 |
| **B. 持久作业队列** | 引入 **arq**（Redis 已具备）或 RQ/Celery，独立 worker 消费 | 可调度/重试/取消；贴合现有 Redis 栈 | 新增一个 worker 进程与作业表 |
| **C. 独立 agent 服务** | 仿 `collab-gateway`，独立容器/进程承载循环，经 HMAC/Redis 与主应用通信 | 隔离彻底；可独立扩缩；与"执行外置"决策一致 | 新增服务与部署单元 |

### 3.2 建议

- **首选 B（arq + Redis）**：最小增量解决持久性、重试、取消，且 Redis 已是核心设施（`utils/redis_client.py`）。
- **规模化后演进到 C**：与 `collab-gateway` 同构，把模型调用/工具执行/沙箱从主应用剥离。
- **明确否决 A**：仅可用于只读、秒级、可丢失的"轻问答"，不作为正式执行模型。
- **短步长 + checkpoint**：无论 B/C，Agent 每步经 Service 层落库，状态可恢复，天然绕开 worker 超时。
- **回传**：输出经 `utils/realtime_bus` → WS 流式推送，复用 `build_log_entries` 模式；长连接仅承载推送，不承载循环。

---

## 4. 工具调用设计

### 4.1 统一工具注册表 + 执行面标注

在服务端建 `services/agent/tool_registry.py`，每个工具是现有 service 的薄适配器：

```python
ToolSpec(
    name="search_code",
    schema={...},          # JSON Schema，供模型 function calling
    plane="server",        # server | local
    scope="repo:read",     # 复用 utils/permission_utils 的角色判定
    requires_approval=False,
)
```

`plane` 是核心字段，决定调用是**进程内直调**还是**下发到客户端**。工具实现不重写——包住现有 service 函数。

### 4.2 server-plane：进程内直调（Web 的基线）

Agent 循环跑在服务端时，工具即现有 service 调用，权限走当前用户的 `utils/permission_utils`。Web 端能力边界：**读码/搜索/建 PR/评论/建 Issue/建分支提交**，无本地文件与执行。这是**设计上的安全边界**，而非缺陷。

### 4.3 local-plane：复用现有 WS 做反向 RPC（Desktop 的发挥空间）

**物理约束**：desktop 本地网关绑定 `127.0.0.1:<随机端口>` + 私有 token（`client/desktop/internal/gateway/gateway.go`），**服务端拨不进去**。因此调用链必须是 `服务端 → 桌面前端 → 本地网关`：

1. Agent 经 `ConnectionManager.send_to_user()`（`api/websocket/manager.py:421`）下发
   `{type:"agent_tool_call", id, tool, args}`；desktop 的 `/ws` 本就经 `handleProxyWS`（`client/desktop/internal/gateway/ws.go`）隧道透传，双向可用。
2. 桌面前端收到后：危险工具（write/exec）先弹**用户授权**，再执行。
3. 前端用自身持有的 gateway token 调本地网关：`/api/local/workspaces/{id}/tree|read-file|write-file|search`（`handlers_fs.go`/`handlers_search.go`）、`handleTerminal`、`handleLSP`。
4. 前端沿同一 WS 回 `{type:"agent_tool_result", id, ok, result|error}`，服务端 resolve pending future。

跨进程调用的先例即 `collab-gateway/server.mjs` 的 `callApp()`（HTTP + 共享 HMAC）——此处为**反方向、同形状**。

**待解工程点**：
- **Future 的 worker 亲和性**：pending future 只存在于持有该 WS 连接的 worker；Agent 循环可能在别的 worker/进程。方案：经 Redis request/reply 按 `services/worker_registry.py` 的 worker_id 路由；或 v1 让循环与用户连接同进程。**此点使 §3 的持久作业层从"可选"变为"必须"。**
- **新增 handler**：`api/websocket/handlers/agent.py`（服务端收结果）、前端新增 `agentSocket`（web/desktop 各一）。

### 4.4 信任模型与安全

- **服务端不是本地执行的可信主体，用户才是。** 本地工具绝不能因服务端 push 就自动执行——必须"Agent 提议 → 桌面弹窗确认 → 执行 → 回传"。
- 服务端永远拿不到 gateway token；该边界不可破（前端持有 token，gateway `validToken` 校验）。
- 危险工具分级：`read`（自动）/ `write`（确认）/ `exec`（确认 + 明确风险提示）；`scope` 限定到工作区。
- 服务端执行（若未来引入）必须沙箱化，不在本期范围。

### 4.5 能力映射（web vs desktop）

| 工具 | Web | Desktop | 实现面 |
|------|-----|---------|--------|
| 读码/搜索/PR/Issue/评论 | ✅ | ✅ | server plane（现有 service） |
| 建分支/提交/开 PR | ✅ | ✅ | server plane（`git_utils`） |
| 本地工作区读/写 | ❌ | ✅ | Go `handlers_fs.go` |
| 本地工作区搜索 | ❌ | ✅ | Go `handlers_search.go` |
| 本地 git（status/diff/commit/push） | ❌ | ✅ | Go `internal/git` |
| LSP（符号/诊断/跳转/引用） | ❌ | ✅ | Go `internal/lsp` |
| 终端执行 | ❌ | ✅（需授权） | Go `internal/term` |

### 4.6 流式与取消

- 每个工具带 timeout/cancel；`exec` 输出复用现有 `progress`/`log` handlers 流式回传。
- Agent 中间步骤（思考/工具调用/结果）走 WS 增量推送，复用 `build_log_entries` 的 `seq` 增量语义。

---

## 5. 代码索引与 token 成本

### 5.1 现状：浅索引（文本检索）

- **内容来源**：Git 对象（pygit2 读 ref 的 tree/blob）——bare 仓库无工作树。
- **存储**：`repo_search_files` 每文件一行，字段 `(repository_id, path, content, size)`，`content` 为**完整文件文本**；`repo_search_state` 记 `indexed_commit`。
- **查询**：`content ILIKE '%q%'`（PostgreSQL `pg_trgm` GIN 加速），命中后**逐行子串匹配**返回 `SearchResult(file, line, content)`；`max_results=100`、`SCAN_FILE_LIMIT=200`。
- **符号提取**：`_SYMBOL_PATTERNS`（`services/repository_browser_service.py:786`）+ `_extract_symbols`（:875）——**逐行正则**，仅认声明行，单文件、无跨文件解析、无类型/作用域/引用。
- **维护**：`_ensure_index` 懒构建；push/PR merge/collab save 经 `diff_changed_files` 做**文件级**增量。

### 5.2 token 消耗分析

给 Agent 一个解析/分析任务时，**token 消耗高，且是数量级上的浪费**，根因不在索引体积，而在**检索粒度与语义缺失**：

1. **检索粒度是"整文件"**：命中返回行文本，但 Agent 要理解上下文只能 `get_blob_content` 拉**整个文件**——定位一行、读整个文件。
2. **只有子串匹配，无语义**："认证流程""A 到 B 的调用链"等字面不命中即**返回空**，Agent 退化为多轮 grep 式试探。
3. **无排序/重排**：命中即截断，Agent 无法判断重要性，只能过度获取。
4. **符号非解析**：无引用/类型，Agent 无法低成本回答"定义在哪、被谁用"。

> 结论：浅检索面 → Agent 迭代式过度抓取 + 整文件读取 → token 膨胀。精确的语义检索（"定义 + N 处引用"几行返回）可降 1~2 个数量级。

### 5.3 JetBrains 索引对照

JetBrains 导入项目时的 Indexing 建的是**语义代码模型**：

| 维度 | Perseus 现状 | JetBrains |
|------|--------------|-----------|
| 解析 | 逐行正则（仅声明） | Lexer + Parser → AST/PSI（分语言插件） |
| 模型 | 扁平表（path, content, symbol line） | 符号表 + 类型系统 + **引用图** + 继承层次 |
| 检索 | `ILIKE` 子串（pg_trgm GIN） | 结构化：解析符号、找引用、层级、补全 |
| 增量 | 按 git diff **文件级**重索引 | **AST/文件级细粒度**增量 + 后台守护 |
| 持久化 | 共享主库（每仓库行） | 本地 stub/index 文件 + 内存索引（mmap） |
| 消费方 | 搜索框 | 导航/补全/重构/检查 + AI 上下文 |

**一句话差距**：`文本搜索 → 语义代码模型`，且 `文件级增量 → AST 级增量`。这是整套语言服务基础设施，不应照抄。

### 5.4 关键洞察：desktop 已有 JetBrains 的"精简版"

`client/desktop/internal/lsp/` 已内嵌 **LSP 管理器**（`Manager.Start` 按扩展名惰性启动语言服务器，`DetectLanguage`）。**语言服务器本身即 JetBrains 式语义引擎**（go-to-definition / find-references / hover / document-symbols），且为**本地计算，不消耗 LLM token**。

由此真实差距分布为：

- **Desktop**：已有本地语义引擎（LSP）+ 本地 exec + 本地 fs → Agent 可获**精确、廉价**的符号/引用/定义信息。
- **Server/Web**：仅有 pg_trgm 文本索引，无语义层 → Agent 只能过度抓取，token 消耗高。

这正解释"Web 受限、Desktop 强"的根因：**语义层的有无**。

### 5.5 索引演进建议（按投入产出排序）

1. **块级切分（最低成本、最大 token 收益）**：用 **tree-sitter**（Python 可跑、跨语言、比 PSI/LSP 轻）解析变更文件，切出符号级 chunk `(path, symbol, start_line, end_line)`，索引只存 chunk。Agent 取 `file:12-34` 而非整文件。
2. **轻量符号/引用图**：tree-sitter query 提定义与标识符引用，存 `def → refs` 边，提供 find-usages（无需类型推断）。
3. **混合检索**：Postgres 已是核心设施，引入 **pgvector**，chunk 向量 + pg_trgm 关键词做 RRF 重排，使语义提问不再返回空。
4. **增量升级到 chunk 级**：现 `update_files` 为文件级 diff，改为"只重解析变更文件、复用未变 chunk"。
5. **desktop 把 LSP 暴露给 Agent**（反向 RPC，见 §4.3）：定义/引用/诊断/符号由本地 LSP 现算，**零 token 成本**且精度高于服务端任何索引——这是 desktop "发挥更好"的技术实质。

---

## 6. 安全、配额与审计

| 项 | 要求 | 复用/新增 |
|----|------|-----------|
| 身份 | Agent 作为 bot user，或"以用户身份代理"，全程可追溯 | 复用 `User`/`permission_utils` |
| 权限 | 工具调用按 `scope` 与仓库角色收敛 | 复用 `utils/permission_utils` |
| 本地执行 | 用户显式授权，服务端不可自动触发 | 新增桌面授权 UI + WS 协议 |
| 配额/成本 | per-user/per-repo token/调用预算 | 新增（可参考 `GlobalConcurrencyLimiter` 的 Redis 计数） |
| 审计 | 每次工具调用/模型调用落 `Activity` | 复用 `activity_service` + 审计中间件 |
| 密钥 | per-user/per-repo API key 加密存储 | 新增（参考 `UserOAuthAccount` 加密字段） |
| 沙箱 | 服务端执行隔离 | 不在本期；desktop 依赖用户授权 |

---

## 7. 明确不做

- 不在服务端自建 JetBrains 级完整语义模型（类型推断、重构、检查）——投入产出不划算。
- 不在本期做服务端代码沙箱/任意执行。
- 不让服务端持有 desktop 本地 gateway token 或直接触发本地执行。
- 不做 Agent 专用前端外壳；复用现有 WS/通知/聊天/编辑器通道。

---

## 8. 里程碑草案（供排期参考）

| 里程碑 | 端 | 内容 | 对应章节 | 前置 |
|--------|----|------|----------|------|
| **A1** | 服务端 | 持久作业层选型落地（arq + Redis）、`agent_service` 骨架、bot user 建模 | §3 / §6 | 无 |
| **A2** | 服务端 | 工具注册表 + server-plane 工具（读/搜/PR/Issue），只读 Agent 闭环（问答/总结） | §4.1 / §4.2 | A1 |
| **A3** | 服务端 | 块级索引（tree-sitter chunk）+ 符号/引用 + pgvector 混合检索 | §5.5 | 可与 A1 并行 |
| **A4** | 服务端 | 写操作工具（建 PR/评论/提交），全程走现有服务与权限 | §4.2 | A2 |
| **A5** | desktop | local-plane 反向 RPC（WS 协议 + handler + `agentSocket`）+ 授权 UI + fs/git/term 工具 | §4.3 / §4.4 | A2 |
| **A6** | desktop | LSP 工具化（定义/引用/诊断/符号，零 token） | §5.4 / §5.5 | A5 |
| **A7** | 服务端 | 配额/成本、审计完善、独立 agent 服务化评估（形态 C） | §3 / §6 | A4 |

> 建议顺序：A1 → A2（先只读验证管道）→ A4 → A5 → A6；A3 可与 A1/A2 并行，越早落地 token 收益越明显。

---

## 9. 参考基准说明

- **架构与端点**：基于本文撰写时的仓库快照（`docs/wiki/` 九章 + 源码定位）。
- **JetBrains 索引行为**：基于 JetBrains 公开文档与产品行为（导入项目 Indexing、PSI/AST、引用图、增量重索引、dumb mode）。
- **LSP 语义能力**：基于 LSP 规范与 `client/desktop/internal/lsp/` 现有实现。
- 本文为规划参考，非实施承诺；代码与文档不符时以代码为准。
