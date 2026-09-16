# Perseus 待办事项清单

> **创建日期**: 2026-09-15
> **用途**: 汇总 2026-09-15 文档盘点发现的待迭代任务与文档滞后项，作为后续排期与迭代输入。
> **最近更新**: 2026-09-16（批次 0/1 完成；前端轻量批次完成并回填）
> **关联**: `docs/api/roadmap.md`、`docs/frontend-placeholders.md`、`docs/collab-f204-vs-cwm.md`、`docs/desktop-port-sync.md`
> **开发方针**: 所有新功能必须采用 TDD（测试驱动开发）；新文案同步补 `{zh,en}.json`；禁止硬编码兜底假数据。

---

## 🌟 优先级说明

| 级别 | 含义 |
|------|------|
| P0 | 阻塞性/高价值，建议立即排期 |
| P1 | 后端 API 已就绪，仅缺前端接线或小型开发（低成本高收益） |
| P2 | 前后端都需少量开发 |
| P3 | 需要新后端能力（存储/推送/聚合），工作量较大 |
| P4 | 暂无规划价值，建议保持现状、移除或文档澄清 |

---

## 一、文档滞后项（先修正，供后续排期失真最小化）

> 这些在 `docs/frontend-placeholders.md` 中标记为「缺后端能力」，但**后端已实现未回填**。应先更新该文档，避免后续重复规划。

| 占位点 | 原标记 | 实际现状 | 待办 |
|--------|--------|----------|------|
| 消息 reactions（chat 3.3） | P3「无后端存储」 | ✅ API 已实现：`chat_controller.py:62-83` POST/DELETE + `chat_service.py:228 add_reaction`；`get_messages` 已透出 reactions | ✅ 已回填 `frontend-placeholders.md`；前端接线确认已实现（批次 E） |
| 文件树 last-commit 列（repo 3.2） | P3「需后端聚合端点」 | ✅ `repository_browser_service.py` 支持 `last_commit=True` 逐文件附带最近提交 | ✅ 已回填 `frontend-placeholders.md`；前端全层级接线完成（批次 E） |

---

## 二、协作增强（来自 `docs/collab-f204-vs-cwm.md` 待排期项）

### P0 — 会话邀请链接 + 会话级临时权限（M2）

| 任务 | 说明 | TDD 要点 | 涉及文件 |
|------|------|----------|----------|
| 邀请链接生成 | `/collab/:sessionToken`，短时 JWT（绑定 docKey + 只读/可写两档 + 过期时间），无仓库角色者凭 token 获得会话级临时权限 | `test_issue_invite_token()`、`test_invite_token_expired()`、`test_invite_token_grants_read_only()` | 新邀请 token service、`api/websocket/handlers/collab.py`（join 权限判定） |
| web 入口 | 编辑器工具栏「分享协作」按钮 → 生成/复制链接 | — | `client/web/src/routes/editor/index.tsx` |

### P0 — 会话生命周期数据安全（3.2）

| 任务 | 说明 | TDD 要点 | 涉及文件 |
|------|------|----------|----------|
| 会话 TTL 延迟销毁 | 最后一人离开后保留 ~10 分钟，期间重 join 恢复现场（`collab_init` 续版本号） | `test_collab_session_ttl_rejoin()`、`test_collab_session_gc_after_ttl()` | `services/realtime/collab_service.py`（TTL/GC） |
| 参与者「未保存」徽标 | 会话参与者列表常显未保存/已提交状态 | — | web/desktop 编辑器 UI |

### P1 — 跟随模式（M2 附带）

| 任务 | 说明 | TDD 要点 | 涉及文件 |
|------|------|----------|----------|
| Follow me | `collab_follow {targetClientID, on}` 状态机 + 滚动位置广播 + 前端平滑滚动跟随 | `test_collab_follow_attach()`、`test_collab_follow_rights()` | 协议扩展（`docs/api/websocket/README.md` 第 7 节）、`collabController.ts`、编辑器工具栏开关 |

### P1 — 断线策略决策落地（M3）

> **需产品决策**：方案 A（断线即编辑锁定，对齐 CwM，简单）vs 方案 B（rejoin 保留本地未确认变更 rebase，超越 CwM，复杂）。当前 Yjs CRDT 底座已天然支持离线合并，建议验证后选 B。

| 任务 | 说明 | 涉及文件 |
|------|------|----------|
| 决策并落地 | 决策后实现锁定或本地缓冲重放 | `collabController.ts`、`client/web/src/components/editor/` |

### P1 — 受限视图（M3，依赖邀请 token scope）

| 任务 | 说明 | 涉及文件 |
|------|------|----------|
| 单文档受限视图 | token 绑定 docKey 时仅该文档可 join；仓库角色用户维持全仓库视图 | `collab.py` join handler（已按 docKey 判定，天然可落地） |

### P2 — 权限即时性（3.5，M2 落地后余项）

| 任务 | 说明 | 涉及文件 |
|------|------|----------|
| 会话级角色覆盖层 | 发起人可改权限/踢人，协议加 `collab_permission` / `collab_kick` | `collab_service.py`、`collab.py` handler |

### P2 — 多副本支持（服务端演进 5.6）

| 任务 | 说明 | 涉及文件 |
|------|------|----------|
| Redis pub/sub 多副本 | 会话注册表与广播从进程内单例迁至 Redis pub/sub，解除 `workers=1` 约束 | `collab_service.py`、`api/websocket/manager.py` |
| 会话持久化 | 变更日志周期快照 + TTL 恢复窗口 | `collab_service.py` |
| 邀请 token 体系 | 签发/校验/撤销服务（与 P0 邀请链接联动） | 新 service |

---

## 三、前端轻量（P1/P2 纯前端，后端零依赖）

| 任务 | 级别 | 现状 | 待办 |
|------|------|------|------|
| 消息按日期分组 | P2 | ~~所有消息归入 "Today"~~ | ✅ 已完成（批次 E）：按 created_at 分组渲染 Today/Yesterday/本地化日期头（`chat/index.tsx`） |
| 编辑器面包屑点击跳转 | P2 | ~~cursor:pointer 无跳转~~ | ✅ 已完成（批次 E）：目录段钉出浮动面板 + 根段回根文件树（`editor/index.tsx`） |
| 顶栏全局搜索三类分组 | P2 | ~~web 为纯代码搜索~~ | ✅ 已完成（批次 C + 2026-09-14）：`GlobalSearch.tsx` 与 `/search` 页均接 `GET /api/v1/search/global` 仓库/Issue/PR/代码分组（`search/index.tsx:50`） |
| PR Filter 装饰按钮 | P4 | ~~无 onClick，云遮雾绕~~ | ✅ 已完成（批次 E）：移除按钮及 unused i18n key（`pull-requests/index.tsx`） |
| 聊天侧边栏搜索框 | P3 | 无 value/onChange | 依赖消息检索端点（后端待做） |
| 主题切换 | P3 | 应用固定 dark | 全站 CSS 变量化，工程量大，可暂缓 |

---

## 四、后端能力新增（P3）

| 任务 | 说明 | TDD 要点 | 涉及文件 |
|------|------|----------|----------|
| Watch 仓库 API | 新表/字段 + 端点（当前只有 star/fork） | `test_watch_repository()`、`test_unwatch_repository()` | 新模型字段 + `repository_controller.py` |
| DM 私聊模型 | 当前仅 repo room，无私信 | `test_dm_room_creation()` | 新模型 + `room_service.py` |
| 文件重命名/移动端点 | move 端点（或 copy+delete 组合提交） | `test_move_file_in_repo()` | `repository_browser_service.py` + controller |
| 行内评论锚定 | 文件+行号存储，可复用 PR 评论模型扩展 | `test_inline_comment_on_file()` | 新模型 + 评论服务 |
| 自动落盘草稿分支 | 会话空闲 N 分钟自动 `collab_save` 到 `collab/draft-...` | `test_autosave_to_draft_branch()` | `collab_service.py` 集成 |

---

## 五、desktop 跟进项

> 2026-09-14 起移植债务已清零。web 端上述协作增强（M2/M3）落地后，需在 `docs/desktop-port-sync.md` 第 3 节按登记规则追加债务行并移植。

| 触发项 | 预期 desktop 跟进 |
|--------|------------------|
| 邀请链接（M2） | 协作会话邀请入口（y-monaco 会话） |
| 跟随模式 | EditorTabs 跟随开关 + 滚动联动 |
| 会话 TTL / 未保存徽标 | StatusBar 已有双态徽标，补齐参与者列表 |

---

## 六、下一阶段三闭环任务（对应 `docs/api/roadmap.md` 7.1）

> 三块围绕「为前端提供完整可用的后端能力」补齐闭环。以下任务均带源码定位（盘点于 2026-09-15）。

### 6.1 代码搜索闭环 —— 已闭环但索引保鲜有断层

**现状**: 单仓 `/{repo_id}/search`（`controller/search_controller.py:49`）+ 跨仓 `/search/code` 聚合 + `/search/global` 三类聚合已可用；FTS5 SQLite 索引存于仓库内 `.perseus_search_index/`（`services/search_service.py:29`），ripgrep fallback。

| 优先级 | 任务 | 缺口说明 | TDD 要点 | 涉及文件 |
|--------|------|----------|----------|----------|
| P1 | 增量索引接入 | `SearchIndex.update()`（`search_service.py:78`）已实现但**无任何调用点**；push/PR merge 均为全量 rebuild | `test_index_incremental_update()`：改 1 文件只更新该文件，mtime 不变项跳过 | `search_service.py`、push/merge 触发点 |
| P1 | push 后索引重建异步化 | `event_service.py:162` 在协程内**同步调用** `rebuild_index`，大仓阻塞事件循环（PR merge 已用 `asyncio.to_thread`，此处理应一致） | `test_push_index_rebuild_not_blocking()`：重建期间心跳/其他请求不被卡住 | `services/realtime/event_service.py` |
| P1 | collab 保存进索引 | `collab/save` → `commit_file` 直接写 git，**不触发索引更新** → 协作编辑后搜不到新内容 | `test_collab_save_index_updated()`：save 后 /search 命中新内容 | `controller/collab_internal_controller.py`（collab_save）、索引更新调用 |
| P2 | 索引生命周期管理 | 仓库删除/改名后 `.perseus_search_index/` 残留；构建失败无重试/状态上报 | `test_index_cleanup_on_repo_delete()` | `repository_service.py` 删除/重命名路径 |

> 前端侧：Web 搜索页接 `/search/global` 三类分组已列于批次 3（见第七节），后端已就绪。

### 6.2 CI/CD 触发闭环 —— 只有记录，没有执行器

**现状**: Build 记录 CRUD + 状态机（`services/build_service.py`）；PR merged 自动建 build（`services/pull_request_service.py:514`）+ 手动 POST；WebHook 投递+重试+签名/投递记录（`services/webhook_service.py:396,545`）。**系统内没有任何进程会把 build 从 pending 推进**——状态更新仅靠外部 `PATCH /builds/{id}` 回调（`controller/build_controller.py:126`）。

| 优先级 | 任务 | 缺口说明 | TDD 要点 | 涉及文件 |
|--------|------|----------|----------|----------|
| P0 | CI 执行器形态决策 | 内置本地 runner（轮询 pending → clone/checkout → 执行脚本 → 回写日志/状态）vs 仅保留外部回调（GHA 式）；**决定后才能排后续任务** | 决策（需产品） | `docs/deployment-guide.md` |
| P0 | push 触发 build | `broadcast_push`（`event_service.py:145`）只建索引+推事件，**不建 build** → CI 仅对 PR merge 生效，feature 分支状态不落库 | `test_push_creates_build()`：非 PR 分支推送建 pending 记录 | `event_service.py`/`pull_request_service.py` |
| P1 | 本地 runner（若选内置） | 执行配置（`.perseus-ci.yml` 或命令约定）→ sandbox 隔离 + 超时 + 日志流式写回 + 并发上限 | `test_runner_executes_build()`、`test_runner_timeout()`、`test_runner_logs()` | 新 `worker/ci_runner.py`、`build_service.py` |
| P1 | 构建配置校验 | `.perseus-ci.yml` 解析/校验/缓存；禁止任意 shell（白名单命令，防 RCE） | `test_ci_config_valid()`、`test_ci_config_rejects_dangerous()` | 新 `services/ci_config_service.py` |
| P2 | 构建日志流式 | 当前 `logs` 为整串字段（`build_controller.py:145`），无分步/时间戳 | `test_build_log_stream()` | 模型字段 + runner 集成 |

### 6.3 实时协作增强 —— 底座齐，缺会话能力

**现状**: 内部密钥三端点 auth/doc/save（`controller/collab_internal_controller.py:124-224`）+ 读/写角色划分 + Yjs 底座已可用。缺口任务详见第二节（协作增强），此处仅列闭环相关性最强的三项。

| 优先级 | 任务 | 缺口说明 | 涉及文件 |
|--------|------|----------|----------|
| P0 | 邀请链接 + 会话级临时权限 | docKey 无 token 化，join 必须仓库角色（`collab_internal_controller.py:140,200`） | 第二节 P0 表 |
| P1 | 会话 TTL 延迟销毁 | 最后一人离开即销毁，重 join 现场不恢复 | 第二节 P0 表 |
| P2 | Redis pub/sub 多副本 | `workers=1` 单副本约束仍在 | 第二节 P2 表 |

---

## 七、需产品决策项

| 项 | 决策点 | 出处 |
|----|--------|------|
| F-204 断线策略 | 方案 A 锁定 vs 方案 B rebase 保留（CRDT 底座已支持 B） | `docs/collab-f204-vs-cwm.md` 3.6 |
| 双态徽标「版本 N」 | 是否透出协作版本号（当前仅短 SHA） | 同上 3.3 |
| 邀请链接默认存在 | 是否存在「任意文档可分享」vs 仅成员可分享 | M2 设计时明确 |
| **CI 执行器形态** | 内置本地 runner vs 仅外部回调（GHA 式）——阻塞 6.2 P0 之后全部任务 | 6.2 分析（2026-09-15） |

---

## 八、建议迭代顺序

| 批次 | 内容 | 预估 | 前置依赖 |
|------|------|------|----------|
| **批次 0（文档回填）** ✅ | 修正 `frontend-placeholders.md`（reactions / last-commit 已就绪） + `roadmap.md`/`README.md` 控制器计数 — **已完成** | 0.5 天 | — |
| **批次 1（搜索保鲜）** ✅ | 增量索引接入、push 异步化、collab save 进索引、索引生命周期清理 — **已完成（pytest 1082 passed, 3 skipped, 无回归）** | 2~3 天 | 无决策依赖，最快收益 |
| **批次 2（协作 P0）** | 邀请链接 + 会话级临时权限（M2）、会话 TTL 延迟销毁 | 1~2 周 | 邀请链接默认存在决策 |
| **批次 3（前端轻量）** ✅ | reactions 前端（确认已实现）、last-commit 列全层级、日期分组、面包屑、`/search/global` 分组（确认已实现）、PR Filter 移除 — **已完成（web tsc+eslint+build 通过）** | 3~5 天 | 批次 0 回填 |
| **批次 4（协作 P1）** | 跟随模式、断线策略（含决策）、受限视图 | 1 周 | 批次 2 |
| **批次 5（CI/CD 闭环）** | push 触发 build + runner/配置校验（先等执行器形态决策） | 1~2 周 | CI 执行器形态决策 |
| **批次 6（服务端演进）** | Redis pub/sub 多副本、会话持久化、索引生命周期 | 1~2 周 | — |
| **批次 7（后端 P3）** | Watch、DM、move、行内评论、自动落盘 | 2 周+ | — |