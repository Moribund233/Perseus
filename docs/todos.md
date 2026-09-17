# Perseus 待办事项清单

> **创建日期**: 2026-09-15
> **用途**: 汇总 2026-09-15 文档盘点发现的待迭代任务与文档滞后项，作为后续排期与迭代输入。
> **最近更新**: 2026-09-17（批次 0/1/3/5/7 完成；会话 TTL 延迟销毁 + Redis 多副本/会话持久化落地；collab 网关多副本收紧：广播私密性/容量上限/403 即时吊销；构建日志流式、自动落盘草稿分支、协作会话级角色覆盖层落地；后端闭环补齐：邀请 token 撤销体系 + push 路径增量索引；test 服务补挂载 alembic）；
> 2026-09-16（批次 2 邀请链接后端+网关+web 完成）
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

> **决策（2026-09-16）**：邀请链接**仅仓库成员可生成**（非任意文档可分享）；被邀请人凭 token 获得会话级临时权限。

| 任务 | 说明 | TDD 要点 | 涉及文件 |
|------|------|----------|----------|
| 邀请链接生成 ✅ | `/collab/:sessionToken`，短时 JWT（绑定 docKey + 只读/可写两档 + 过期时间），仅仓库成员可签发；无仓库角色者凭 token 获得会话级临时权限 — **已完成**：`services/collab_invite_service.py` + `controller/collab_invite_controller.py`（`POST /{repo_id}/collab/invites`）；`/collab/auth`/`/collab/save` 接受 `invite_token` | `test_issue_invite_token()`、`test_invite_token_expired()`、`test_invite_token_grants_read_only()`、`test_invite_token_rejected_for_non_member()` ✅ | `services/collab_invite_service.py`、`controller/collab_invite_controller.py`、`controller/collab_internal_controller.py` |
| web 入口 ✅ | 编辑器工具栏「分享协作」按钮 → 生成/复制链接（仅成员可见） — **已完成**：`editor/index.tsx`（`handleShareCollab` + `isRepoMember`）；`?invite=` 经 `collabController.ts` JSON token 透传，网关 `parseConnectionToken` 解析转发 | — | `client/web/src/routes/editor/index.tsx`、`components/editor/collabController.ts`、`collab-gateway/server.mjs` |

### P0 — 会话生命周期数据安全（3.2）

| 任务 | 说明 | TDD 要点 | 涉及文件 |
|------|------|----------|----------|
| 会话 TTL 延迟销毁 ✅ | 最后一人离开后保留内存 Y.Doc（`PERSEUS_COLLAB_SESSION_TTL_MS`，默认 10 分钟），窗口内重 join 直接复用现场；TTL 到期卸载，下次 join 重新播种 — **已完成（2026-09-17）** | `gateway.test.mjs`：TTL 窗口内重连保留现场不重新加载 / TTL 到期重载 / TTL=0 立即卸载 ✅ | `collab-gateway/sessionTtl.mjs`、`collab-gateway/server.mjs` |
| 参与者「未保存」徽标 | 会话参与者列表常显未保存/已提交状态 | — | web/desktop 编辑器 UI |

### P1 — 跟随模式（M2 附带）

| 任务 | 说明 | TDD 要点 | 涉及文件 |
|------|------|----------|----------|
| Follow me | `collab_follow {targetClientID, on}` 状态机 + 滚动位置广播 + 前端平滑滚动跟随 | `test_collab_follow_attach()`、`test_collab_follow_rights()` | 协议扩展（`docs/api/websocket/README.md` 第 7 节）、`collabController.ts`、编辑器工具栏开关 |

### P1 — 断线策略决策落地（M3）

> **决策（2026-09-16）**：选 **方案 B（rebase 保留）**——断线后本地继续编辑，本地未确认变更缓冲保留，重连后利用 Yjs CRDT 收敛合并。截止前未确认的普通提交不做全本地支持（B 的复现面为 P1 范围）。

| 任务 | 说明 | 涉及文件 |
|------|------|----------|
| 按方案 B 落地 | 断线本地缓冲 + 重连 rebase 重放（验证 CRDT 收敛语义后实现） | `collabController.ts`、`client/web/src/components/editor/` |

### P1 — 受限视图（M3，依赖邀请 token scope）

| 任务 | 说明 | 涉及文件 |
|------|------|----------|
| 单文档受限视图 | token 绑定 docKey 时仅该文档可 join；仓库角色用户维持全仓库视图 | `collab.py` join handler（已按 docKey 判定，天然可落地） |

### P2 — 权限即时性（3.5，M2 落地后余项）

| 任务 | 说明 | 涉及文件 |
|------|------|----------|
| 会话级角色覆盖层 ✅ | 发起人（仓库 owner/admin）可改成员会话权限（read/write）或踢出；覆盖优先于仓库角色与邀请 token，`/collab/auth` 与 `/collab/save` 即时强制执行；改权限即重新接纳；清空覆盖（scope=null）回落仓库角色；顺带修复 `readonly` 角色无法加入会话的缺陷 — **已完成（2026-09-17）** | `test_collab_session_override.py`：10 用例 ✅ | `controller/collab_session_controller.py`、`services/collab_session_service.py`、`models/collab_session_override.py`、`controller/collab_internal_controller.py` |

### P2 — 多副本支持（服务端演进 5.6）

| 任务 | 说明 | 涉及文件 |
|------|------|----------|
| Redis pub/sub 多副本 ✅ | `@hocuspocus/extension-redis` 经 Redis pub/sub 跨副本广播 CRDT 变更与感知，同一文档落在不同副本也收敛 — **已完成（2026-09-17）**；compose 已接线 `REDIS_URL`、可 `--scale collab=N`（nginx 动态解析留待扩容） | `redisIntegration.test.mjs`：副本间同步 / 快照恢复不回源 Git（需 `TEST_REDIS_URL`）✅ | `collab-gateway/server.mjs`、`collab-gateway/redisPersistence.mjs`、`docker-compose.yml` |
| 会话持久化 ✅ | `@hocuspocus/extension-database` + Redis Y.Doc 快照：周期落盘、冷加载优先恢复未提交编辑；多副本冷启动播种用 Redis 锁串行化防重复（`hellohello`） — **已完成（2026-09-17）** | 同上 | `collab-gateway/redisPersistence.mjs`、`docker-compose.yml` |
| 多副本收紧（bugfix） ✅ | 广播私密性（`collab-saved` 仅回 `commit_id`+`docKey`，不再泄漏 `saved_by/branch/path/message`）；单文档内容上限（`PERSEUS_COLLAB_MAX_CONTENT_CHARS`，超限拒加载 413/拒保存）；每文档并发连接上限（`PERSEUS_COLLAB_MAX_CONNECTIONS_PER_DOC`，超限拒新连接）；保存被 app 回 403 即断连强制重认证（多副本即时吊销） — **已完成（2026-09-17）** | `gatewayHardening.test.mjs`：5 用例 ✅ | `collab-gateway/server.mjs`、`client/web/src/components/editor/collabController.ts`、`client/desktop/frontend/src/api/collabSocket.ts` |
| 邀请 token 体系 ✅ | 签发/校验/**撤销**服务（与 P0 邀请链接联动）— **已完成（2026-09-17）**：新增 `collab_invite_revocations` 黑名单表（按 jti）+ `POST /{repo_id}/collab/invites/revoke`（仅 owner/admin）；`/collab/auth` 与 `/collab/save` 改用 `verify_invite_token_active` 叠加撤销校验，已撤销 token 即时 403 | `test_collab_invite_revocation.py`：8 用例 ✅ | `services/collab_invite_service.py`、`controller/collab_invite_controller.py`、`models/collab_invite_revocation.py` |

---

## 三、前端轻量（P1/P2 纯前端，后端零依赖）

| 任务 | 级别 | 现状 | 待办 |
|------|------|------|------|
| 消息按日期分组 | P2 | ~~所有消息归入 "Today"~~ | ✅ 已完成（批次 E）：按 created_at 分组渲染 Today/Yesterday/本地化日期头（`chat/index.tsx`） |
| 编辑器面包屑点击跳转 | P2 | ~~cursor:pointer 无跳转~~ | ✅ 已完成（批次 E）：目录段钉出浮动面板 + 根段回根文件树（`editor/index.tsx`） |
| 顶栏全局搜索三类分组 | P2 | ~~web 为纯代码搜索~~ | ✅ 已完成（批次 C + 2026-09-14）：`GlobalSearch.tsx` 与 `/search` 页均接 `GET /api/v1/search/global` 仓库/Issue/PR/代码分组（`search/index.tsx:50`） |
| PR Filter 装饰按钮 | P4 | ~~无 onClick，云遮雾绕~~ | ✅ 已完成（批次 E）：移除按钮及 unused i18n key（`pull-requests/index.tsx`） |
| 聊天侧边栏搜索框 | P3 | 无 value/onChange | 后端已就绪（2026-09-17）：`GET /api/v1/messages/search?q=`（跨会话）+ `GET /rooms/{room_id}/messages?q=`（单会话）；待前端接线 |
| 主题切换 | P3 | 应用固定 dark | 全站 CSS 变量化，工程量大，可暂缓 |

---

## 四、后端能力新增（P3）

| 任务 | 说明 | TDD 要点 | 涉及文件 |
|------|------|----------|----------|
| Watch 仓库 API ✅ | 新表/字段 + 端点（当前只有 star/fork） — **已完成**：`Watcher` 表 + `Repository.watch_count`，`watch_service.py` + `watch_controller.py`（POST/DELETE/GET `/{repo_id}/watch`、GET `/watchers`）；web 仓库页 Watch 按钮已接线 | `test_watch_repository()`、`test_unwatch_repository()` ✅ | `models/watcher.py`、`services/watch_service.py`、`controller/watch_controller.py` |
| DM 私聊模型 ✅ | **已完成**（2026-09-17）：`RealtimeRoom.room_type`（`repository`/`dm`）+ `repository_id` 可空 + `DirectMessage` 规范化 pair（`user_a_id < user_b_id`）；`RoomService.get_or_create_dm_room()` 幂等（任一方发起命中同一会话）、`list_dm_rooms()`、`list_rooms()` 仅返回 repo room；复用既有房间消息/WS 广播。端点：`POST/GET /api/v1/dm` | `test_dm_room_creation()` 等 15 例 ✅ | `models/realtime_room.py`、`services/realtime/room_service.py`、`controller/dm_controller.py` |
| 文件重命名/移动端点 ✅ | move 端点（或 copy+delete 组合提交） — **已完成**：`git_utils.move_file_changes` 单次提交内 copy+delete，`POST /{repo_id}/contents/move` | `test_move_file_in_repo()` ✅ | `utils/git_utils.py`、`services/repository_browser_service.py`、`controller/repository_browser_controller.py` |
| 行内评论锚定 ✅ | **已完成**（2026-09-17）：新增 `FileComment`（repository_id/file_path/line_number/branch/commit_hash/parent_id/resolved）；`file_comment_service.py` + `controller/file_comment_controller.py`，端点 `/api/v1/repositories/{repo_id}/discussions`（创建/列表/回复/解决/删除，含仓库读权限与作者/负责人鉴权）。另补消息检索：`ChatService.search_messages()` + `GET /api/v1/messages/search`、`get_messages(q=)` | `test_inline_comment_on_file()` 等 13 例 ✅ | `models/file_comment.py`、`services/file_comment_service.py`、`controller/file_comment_controller.py` |
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
| P1 | 增量索引接入（push 已增量） ✅ | PR merge / collab save 已 `update_files`；**push 路径（`event_service.py:broadcast_push`）已改为增量**：携带 `old_sha` 时经 `diff_changed_files` 只重索引变更文件，diff 不可用才回退全量 `rebuild_index`；均经 `asyncio.to_thread` 不阻塞事件循环 — **已完成（2026-09-17）** | `test_broadcast_push_incremental_index_when_old_sha_given`、`test_broadcast_push_falls_back_to_rebuild_when_diff_unavailable` ✅ | `services/realtime/event_service.py`、`services/search_service.py` |
| P1 | push 后索引重建异步化 ✅ | `event_service.py:167` 已用 `asyncio.to_thread(SearchService.rebuild_index, ...)`，不再阻塞事件循环（与 PR merge 一致）— **已在批次 1 落地** | `test_push_index_rebuild_not_blocking()`（批次1 用例 ✅） | `services/realtime/event_service.py` |
| P1 | collab save 进索引 ✅ | `collab_internal_controller.py:237` save → `SearchService.update_files()` 增量更新，搜索立即可检索 — **已在批次 1 落地** | `test_collab_save_index_updated()`（批次1 用例 ✅） | `controller/collab_internal_controller.py`、`SearchService.update_files` |
| P2 | 索引生命周期管理 ✅ | 仓库删除/改名后索引残留已清理（`repository_service.py` 改名调 `cleanup_index`、删除随物理目录 `rmtree`）；构建失败状态由 `build_service.py:116` 落 `finished_at`，重试按「仅外部回调」决策归外部 CI — **已在批次 1 落地并测试（2026-09-17 复核）** | `test_delete_repository_removes_search_index`、`test_update_repository_cleans_legacy_index_on_path_change`、`test_cleanup_index_removes_directory` ✅ | `repository_service.py`、`services/search_service.py` |

> 前端侧：Web 搜索页接 `/search/global` 三类分组已列于批次 3（见第七节），后端已就绪。

### 6.2 CI/CD 触发闭环 —— 只有记录，没有执行器

**现状**: Build 记录 CRUD + 状态机（`services/build_service.py`）；PR merged 自动建 build（`services/pull_request_service.py:514`）+ 手动 POST；WebHook 投递+重试+签名/投递记录（`services/webhook_service.py:396,545`）。**系统内没有任何进程会把 build 从 pending 推进**——状态更新仅靠外部 `PATCH /builds/{id}` 回调（`controller/build_controller.py:126`）。

| 优先级 | 任务 | 缺口说明 | TDD 要点 | 涉及文件 |
|--------|------|----------|----------|----------|
| ~~P0~~ | ~~CI 执行器形态决策~~ | ✅ **已决策（2026-09-16）：仅外部回调（GHA 式）**——系统只存 build 记录 + 状态机，执行由外部 CI 完成后 `PATCH` 回写 | — | — |
| ~~P0~~ | ~~push 触发 build~~ ✅ | `broadcast_push`（`event_service.py`）已扩展：携带 `db`/`commit_sha` 时经 room 解析仓库并 `ensure_build_for_commit` 去重建 pending build（避免与 PR merge 重复） | `test_push_creates_build()`、`test_broadcast_push_creates_build_for_commit()` ✅ | `event_service.py`/`build_service.py` |
| ~~P1~~ | ~~本地 runner~~ | ❌ **取消**（决策为仅外部回调，无需内置轮询/clone/执行器） | — | — |
| ~~P1~~ | ~~外部回调接入增强~~ ✅ | 外部 CI 回调签名鉴权（`X-Perseus-Signature`，HMAC-SHA256 复用 `generate_signature`）+ `Repository.ci_secret`（alembic 迁移）；`PATCH /builds/{id}` 支持签名或用户 token 双通道 | `test_external_callback_signed()`（`test_update_build_via_signature` 等）✅ | `build_controller.py`、`webhook_service.py`、`models/repository.py` |
| ~~P2~~ | ~~构建日志流式~~ ✅ | 新增 `build_log_entries` 子表（seq 每 build 自增、stream 分流、logged_at timestamptz）；签名回调 PATCH 支持 `log_entries` **追加**（不再整串覆盖）；`GET /logs?after_seq=N` 增量拉取返回 `{logs, entries, next_seq}` | `test_build_log_stream.py` ✅（红→绿，全量 1170 passed） | 模型字段 + 外部回调写入 + 增量拉取 |

### 6.3 实时协作增强 —— 底座齐，缺会话能力

**现状**: 内部密钥三端点 auth/doc/save（`controller/collab_internal_controller.py:124-224`）+ 读/写角色划分 + Yjs 底座已可用。缺口任务详见第二节（协作增强），此处仅列闭环相关性最强的三项。

| 优先级 | 任务 | 缺口说明 | 涉及文件 |
|--------|------|----------|----------|
| P0 | 邀请链接 + 会话级临时权限 ✅ | 已落地：docKey 绑定短时 JWT（`collab_invite_service.py`），`/collab/auth`/`/collab/save` 接受 `invite_token`（无仓库角色者可读写受控） | 第二节 P0 表 |
| P1 | 会话 TTL 延迟销毁 ✅ | **已完成（2026-09-17）**：网关 `sessionTtl.mjs`（`PERSEUS_COLLAB_SESSION_TTL_MS`，默认 10 分钟），最后一人离开后保留内存现场，窗口内重 join 复用；TTL 到期卸载 | 第二节 P0 表 |
| P2 | Redis pub/sub 多副本 ✅ | **已完成（2026-09-17）**：`@hocuspocus/extension-redis` pub/sub 跨副本广播 + `extension-database` Redis 快照会话持久化（`redisPersistence.mjs`），解除 `workers=1`/单副本约束；compose 已接线 `REDIS_URL` | 第二节 P2 表 |

---

## 七、需产品决策项

> 2026-09-16 已批量决策：F-204 断线策略 → 方案 B（rebase 保留）；邀请链接 → 仅成员可分享；CI 执行器 → 仅外部回调（GHA 式）。

| 项 | 决策点 | 出处 |
|----|--------|------|
| F-204 断线策略 | ✅ **已决策（2026-09-16）：方案 B rebase 保留**（保留未确认变更，重连 CRDT 收敛） | `docs/collab-f204-vs-cwm.md` 3.6 |
| 双态徽标「版本 N」 | ⏳ 待定：是否透出协作版本号（当前仅短 SHA）——不阻塞排期 | 同上 3.3 |
| 邀请链接默认存在 | ✅ **已决策（2026-09-16）：仅成员可分享**（非任意文档可分享），被邀请人凭 token 获会话级临时权限 | M2 设计时明确 |
| **CI 执行器形态** | ✅ **已决策（2026-09-16）：仅外部回调（GHA 式）**，push 触发 build 即可排期 | 6.2 分析（2026-09-15） |

---

## 八、建议迭代顺序

| 批次 | 内容 | 预估 | 前置依赖 |
|------|------|------|----------|
| **批次 0（文档回填）** ✅ | 修正 `frontend-placeholders.md`（reactions / last-commit 已就绪） + `roadmap.md`/`README.md` 控制器计数 — **已完成** | 0.5 天 | — |
| **批次 1（搜索保鲜）** ✅ | 增量索引接入、push 异步化、collab save 进索引、索引生命周期清理 — **已完成（pytest 1082 passed, 3 skipped, 无回归）** | 2~3 天 | 无决策依赖，最快收益 |
| **批次 2（协作 P0）** ✅ | 邀请链接 + 会话级临时权限（M2）+ 会话 TTL 延迟销毁 **均已完成**（后端 + 网关透传 + web 分享按钮） | 1~2 周 | ✅ 邀请链接决策已定（仅成员可分享，2026-09-16） |
| **批次 3（前端轻量）** ✅ | reactions 前端（确认已实现）、last-commit 列全层级、日期分组、面包屑、`/search/global` 分组（确认已实现）、PR Filter 移除 — **已完成（web tsc+eslint+build 通过）** | 3~5 天 | 批次 0 回填 |
| **批次 4（协作 P1）** | 跟随模式、断线策略（方案 B rebase 保留，✅ 已决策）、受限视图 | 1 周 | 批次 2 |
| **批次 5（CI/CD 闭环）** ✅ | push 触发 build + 外部回调签名（GHA 式）**已完成**；仅剩余双态徽标「版本 N」非阻塞项 | 1~2 周 | 仅剩余双态徽标「版本 N」非阻塞项 |
| **批次 6（服务端演进）** ✅ | Redis pub/sub 多副本、会话持久化、索引生命周期 — **均已完成** | 1~2 周 | — |
| **批次 7（后端 P3）** ✅ | Watch ✅、文件 move ✅、DM ✅、行内评论 ✅、消息检索 ✅、自动落盘草稿分支（后端 `draft→collab/draft-{branch}`）✅；仅剩「会话空闲 N 分钟自动触发」前端计时 — **后端已完成（2026-09-17）** | 2 周+ | — |