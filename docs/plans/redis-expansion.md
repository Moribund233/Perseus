# Redis 能力扩展规划

> **更新日期**: 2026-09-21
> **范围**: 后端 Redis 客户端（`utils/redis_client.py`）从"仅请求统计"扩展为可复用的基础设施，支撑跨 worker 实时广播、OAuth state、presence、缓存与黑名单等业务。
> **关联**: `docs/plans/todos.md`、`docs/plans/collab-f204-vs-cwm.md`、`docs/plans/roadmap.md`、`docs/api/websocket/README.md`
> **开发方针**: 沿用项目 TDD 约定；后端进程/测试只在 WSL Docker（`docker compose --profile test run --rm test`）运行，禁止在 Windows 宿主机跑 pytest/uvicorn。

> **2026-09-21 落地（R1 + R3 + R2）**：
> ① **R1 客户端硬化**——`utils/redis_client.py` 改为"冷却重试"（`reconnect_cooldown`，不再永久冻结）、新增 `require_redis()`（强依赖显式失败）、`create_pubsub_client()`（独立订阅连接）、`key()`/`ws_channel()`/`ws_pattern()`（统一 `perseus:` 命名空间）；`core/config.py` 的 `RedisSettings` 新增 `namespace`/`pubsub_prefix`/`reconnect_cooldown`；`middleware/request_stats.py` 键改用共享 `key("req", …)`。
> ② **R3 OAuth state**——`OAuthStateStore` 异步化，Redis 共享键 `perseus:oauth:state:<state>`（`SETEX`+`GETDEL`），不可用时回退内存并**告警**；`initiate_login` 改异步，controller 与既有测试同步更新。
> ③ **R2 跨 worker 广播**——新增 `utils/realtime_bus.py`（Hybrid：本地直投 + Redis pub/sub，`origin` 跳过回声），`ConnectionManager` 的 `send_to_*` 拆为 `_deliver_*`（本地）+ `_publish`（远端），由 `core/lifespan.py` 启停；调用点（chat/room/notification/event/presence）无需改动。
> ④ **D4 部署**——`docker-compose.base.yml` redis 改 `--maxmemory 512mb --maxmemory-policy volatile-lru`（仅淘汰带 TTL 键，保护 collab 无 TTL 快照），容器内存上限 320M→640M。
> **验证**：`test` 容器 **1331 passed / 3 skipped**；新增用例 `tests/test_redis_client.py`、`tests/test_oauth_state_store.py`、`tests/test_realtime_bus.py`。

---

## 一、背景与动机

当前 Redis 客户端是"够用但脆弱"的单点：仅服务请求统计，且设计上一次性探测、失败即永久降级。

而 Perseus 的生产部署是 **4 个 Uvicorn worker**（`Dockerfile:97`：`uvicorn app:app --workers 4`），
但后端 WebSocket 连接管理器是**进程内单例 + 内存索引**（`api/websocket/manager.py:106-137`）。
这意味着聊天、通知、仓库事件、presence 的广播（`send_to_user` / `send_to_room` / `send_to_repository`，
`manager.py:309/372/393`）**只能触达本 worker 持有的连接**——这是当前最大的正确性缺口。

同类问题还有 OAuth state（`services/oauth_service.py:19-47`，代码注释已自述"生产环境应换 Redis"）、
进程内热缓存（`services/repository_service.py:31-62`）等。

**重要先例**：协作文档网关（`collab-gateway/`，Node/Hocuspocus）已于 2026-09-17 通过
`@hocuspocus/extension-redis` + `redisPersistence.mjs` 完成 Redis pub/sub 多副本与快照持久化
（见 `docs/plans/collab-f204-vs-cwm.md:180-181`、`docs/plans/todos.md:92-94,175`），
compose 已接线 `REDIS_URL`。本次规划是把同样的模式补齐到 **FastAPI 应用侧**。

---

## 二、现状盘点

### 2.1 客户端与配置

| 项 | 现状 | 位置 |
|---|---|---|
| 客户端 | 异步单例，惰性建连、`ping()` 健康检查 | `utils/redis_client.py:27-60` |
| 探测语义 | `_resolved` 首次调用即置位；失败后**整个进程生命周期永久返回 None** | `utils/redis_client.py:35-37,57-60` |
| 连接参数 | `decode_responses=True`、connect/socket 超时 1s、health_check 2s | `utils/redis_client.py:47-53` |
| 配置 | `RedisSettings.url`，`PERSEUS_REDIS_URL` 优先，回退 `REDIS_URL`；空=禁用 | `core/config.py:110-121` |
| 依赖 | `redis>=5.0.0` 已声明 | `pyproject.toml:28` |
| 部署 | `redis:7-alpine`，`maxmemory 256mb`，`allkeys-lru`，关闭 AOF | `docker-compose.base.yml:44-49` |
| 接线 | app/collab 均注入 `REDIS_URL` | `docker-compose.yml:35,104` |

### 2.2 唯一消费方：请求统计

`middleware/request_stats.py` 通过 `get_redis()`（`:25,68`）把请求指标写入 `perseus:req:*` 分钟桶
（`:84-96`），读取时聚合完整分钟窗口（`:123-156`）；无 Redis 时回退进程内 `deque`（`:98-113`）。
该模式（Redis 聚合 + 内存降级）正是本次要推广的范式。

### 2.3 待迁移的进程内状态

| 业务 | 现状 | 多 worker 后果 | 位置 |
|---|---|---|---|
| **WS 广播** | 进程内单例索引 | 聊天/通知/事件/presence 丢消息、在线列表不全 | `api/websocket/manager.py:106-137` |
| **OAuth state** | 进程内 dict + TTL | 回调落到别的 worker → state 校验失败，登录随机失败 | `services/oauth_service.py:19-47` |
| **在线用户** | 只统计本进程连接 | `get_room_online_users` 不完整 | `manager.py:555-565` |
| **仓库存在缓存** | 每 worker 一份 30s TTL | 各 worker 视图不一致（收益有限） | `services/repository_service.py:31-62` |
| **令牌黑名单** | 每次查 `RevokedToken` 表 | DB 读放大 | `services/token_service.py:243-303` |
| **协作邀请撤销** | 每次查 `CollabInviteRevocation` | DB 读放大 | `services/collab_invite_service.py:117-184` |
| **并发限制** | 每进程 `asyncio.Semaphore` | 4 worker 实际配额 ×4（Nginx 已限流，优先级低） | `middleware/concurrency.py:29-31` |

### 2.4 部署拓扑澄清

- 单容器内 **4 worker 已足以触发**上述所有跨进程问题；即使不横向扩容 `--scale app=N` 也需要处理。
- Nginx 把 `/ws/collab` 转 `collab` 网关、其余 `/ws/` 转 app（`docker/gateway/nginx.conf:75-76,127-134`）。
  WebSocket 连接按 TCP 粘到某个 worker，**不保证**同一用户的多条连接落在同一 worker，`ip_hash` 也无法修复房间广播。

---

## 三、候选场景评估

评分：价值 / 工作量 / 风险 / 建议优先级。P0=高价值先做，P3=暂缓。

| # | 场景 | 价值 | 工作量 | 风险 | 优先级 |
|---|------|------|--------|------|--------|
| 1 | 跨 worker WebSocket 广播（pub/sub 总线） | 高（正确性缺口） | 大 | 中（去重/循环/降级） | **P0** |
| 2 | OAuth state 迁移 Redis | 高（登录正确性） | 小 | 低 | **P0** |
| 3 | 客户端硬化（健康恢复/独立 pubsub 连接/命名空间） | 高（前置条件） | 小 | 低 | **P0** |
| 4 | presence / 在线用户全局注册表 | 中 | 中 | 低 | P1 |
| 5 | 令牌 / 邀请黑名单读缓存 | 中（降 DB 压） | 小 | 低 | P1 |
| 6 | 仓库/搜索热数据缓存 | 低-中 | 中 | 中（失效一致性） | P2 |
| 7 | 全局并发/限流 | 低（Nginx 已覆盖） | 中 | 中 | P3 |
| 8 | 分布式锁 / 幂等 | 视需求 | 中 | 中 | P3 |

---

## 四、总体架构设计

### 4.1 分层

```
业务层（chat / notification / event / presence / oauth / cache）
        │  仅依赖抽象接口
        ▼
RealtimeBus / StateStore / Cache 抽象（utils/redis_*.py）
        │  可插拔后端
        ├── Redis 后端（get_redis / get_pubsub）
        └── 内存后端（无 Redis 时，语义与现状一致）
```

原则：**业务代码不直接 import redis**，只依赖抽象；Redis 不可用时退回内存实现，行为与当前单进程一致。

### 4.2 客户端改造（`utils/redis_client.py`）

- 保留 `get_redis()` 命令客户端（供统计/缓存/state）。
- **新增 `get_pubsub()`**：订阅需要**独立连接**（订阅态会阻塞普通命令），且不能设 `socket_timeout`，
  需自带重连循环。
- **健康恢复**：把"探测一次永久冻结"改为"带冷却的可重试"——首次失败后允许在下次调用（或后台探活）
  重连；对强依赖场景（OAuth、广播）暴露 `require_redis()`（不可用即显式报错，而非静默 None）。
- **命名空间**：统一 `perseus:` 前缀，新增配置项（建议 `PERSEUS_REDIS_NAMESPACE`、`PERSEUS_REDIS_PUBSUB_PREFIX`）。

### 4.3 广播总线（核心）

- 抽象：`RealtimeBus.publish(scope, target_id, message, origin_id)`，scope ∈ `user|room|repository|broadcast`。
- Redis 通道：`perseus:ws:<scope>:<id>`。
- **投递路径（推荐 hybrid，避免重复）**：
  1. 发送方先投递给**本 worker 本地** manager；
  2. 同时 `PUBLISH`，payload 带 `origin_id`（worker 唯一标识）；
  3. 各 worker 的订阅循环收到后，**跳过 origin 自身**，只投递给本地连接。
- 订阅循环在 `core/lifespan.py` 启动（参照现有心跳任务 `:95-101`），关闭时优雅取消（`:68-82`）。
- 迁移调用点：`services/realtime/event_service.py:32`、通知 handler、chat/room handler、
  `manager.disconnect` 的 `presence_leave`（`manager.py:207-219`）。
- 无 Redis 时：`RealtimeBus` 走纯本地实现，**行为退化为现状**，不引入错误。

### 4.4 强依赖 vs 可选依赖的降级分级

| 依赖类型 | 无 Redis 行为 | 场景 |
|---|---|---|
| 可选（加速） | 静默回退内存/直连 DB | 请求统计、热缓存、黑名单缓存 |
| 强依赖（正确性） | **显式降级 + 可观测告警**，不静默 | OAuth state、WS 广播 |

---

## 五、分阶段实施计划

> 每阶段遵循 TDD：先写失败测试（`tests/`），再实现；每阶段结束在 `test` 容器全绿。

### R1 — 客户端硬化（前置，0.5~1 天）✅ 2026-09-21

| 任务 | 交付 | TDD 要点 |
|---|---|---|
| R1-1 健康恢复 | `get_redis()` 支持失败后按冷却重探，而非永久冻结 | 首次失败→再次调用（冷却后）成功 |
| R1-2 pubsub 工厂 | `get_pubsub()` 独立连接 + 重连循环 | mock 连接验证不设 socket_timeout、断线重订阅 |
| R1-3 命名空间配置 | `RedisSettings.namespace` / pubsub 前缀 | 配置解析 + 键前缀拼接 |
| R1-4 依赖分级 | `require_redis()` / `is_configured()` | 未配置时强依赖抛错、可选依赖返回 None |

**涉及**：`utils/redis_client.py`、`core/config.py`、`tests/test_request_stats.py`（扩展）。

### R2 — 跨 worker WebSocket 广播（核心，3~5 天）✅ 2026-09-21

| 任务 | 交付 | TDD 要点 |
|---|---|---|
| R2-1 总线抽象 | `utils/realtime_bus.py`（local/redis 双实现） | 内存后端单测：scope 路由正确 |
| R2-2 订阅循环 | lifespan 启停、origin 去重、异常自愈 | 伪 Redis：两"worker"互发不重复、origin 不回声 |
| R2-3 调用点迁移 | event/chat/room/notification/presence 全走总线 | 现有 `test_websocket_manager` / `test_notification_ws` 回归 |
| R2-4 降级 | 无 Redis 时纯本地，行为不变 | 拔掉 Redis 的等价性测试 |
| R2-5 集成 | 真 Redis 下双 worker 端到端（房间广播、定向通知） | 集成用例（test 容器内起临时 Redis 或复用 compose redis） |

**涉及**：`api/websocket/manager.py`、`api/websocket/handlers/*`、`services/realtime/event_service.py`、`core/lifespan.py`。

### R3 — OAuth state 迁移（0.5~1 天）✅ 2026-09-21

| 任务 | 交付 | TDD 要点 |
|---|---|---|
| R3-1 StateStore 抽象 | `OAuthStateStore` 接口 + 内存/Redis 实现 | `generate/consume` 语义、TTL 过期、provider 校验 |
| R3-2 Redis 实现 | `SETEX perseus:oauth:state:<s>` + `GETDEL` 消费 | 一次性消费、跨实例可见 |
| R3-3 接线 | `services/oauth_service.py` 改用抽象 | 现有 OAuth 测试回归 |

### R4 — presence / 在线用户全局化（1~2 天，依赖 R2）

| 任务 | 交付 | TDD 要点 |
|---|---|---|
| R4-1 连接注册 | 连接建立/断开写 Redis（Hash/Set + TTL 心跳续期） | 加入/离开/TTL 过期 |
| R4-2 全局查询 | `get_room_online_users` 聚合多 worker | 双 worker 聚合去重 |
| R4-3 降级 | 无 Redis 回退本进程（现状） | 等价性 |

### R5 — 缓存与黑名单（1~2 天，可拆分）

| 任务 | 交付 | TDD 要点 |
|---|---|---|
| R5-1 黑名单读缓存 | `token_service` / `collab_invite_service` 命中缓存降低 DB 读 | 撤销即写缓存、TTL 与 token 过期对齐 |
| R5-2 仓库存在缓存 | 可选：`repository_service` 30s 缓存共享 | 失效/一致性；收益不足则放弃 |
| R5-3 全局限流 | 可选：Redis 计数器替代/补充 Nginx 限流 | 仅当有明确需求再做 |

---

## 六、关键技术决策（已评审）

> **2026-09-21 决策**：本期范围 **R1 + R3 + R2**（P0 全部），按易→难落地：R1 客户端硬化 → R3 OAuth state → R2 跨 worker 广播。

| # | 决策点 | 结论 | 状态 |
|---|--------|------|------|
| D1 | 广播去重策略 | **Hybrid**：本 worker 连接直投；同时 `PUBLISH` 带 `origin_id`，订阅端跳过 origin 自身，保证每连接恰好一次 | ✅ 已决策 |
| D2 | 强依赖不可用时 | **显式降级 + 告警**：`require_redis()` 不可用即抛错/记 WARN；可选场景仍静默回退内存 | ✅ 已决策 |
| D3 | 测试后端 | **伪实现单测 + 真 Redis 集成**（compose 已有 redis；跨 worker 用例在 test 容器内用真 Redis） | ✅ 已决策 |
| D4 | `allkeys-lru` 与持久数据 | **保护持久键**：调整 redis 淘汰策略为仅淘汰带 TTL 的键并提升 `maxmemory`；所有新增持久键均带 TTL | ✅ 已决策 |
| D5 | 键命名空间 | **统一 `perseus:` 前缀、分域命名**（`perseus:req:*` / `perseus:oauth:*` / `perseus:ws:*`） | ✅ 已决策 |
| D6 | 是否拆分独立 WS 网关 | **不拆**：采用 Redis pub/sub，成本低于独立网关 | ✅ 已决策 |

---

## 七、风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 消息重复投递 / 循环 | 客户端重复渲染、风暴 | origin_id 去重；订阅端不二次 publish |
| Redis 抖动导致广播中断 | 实时功能降级 | 订阅循环自动重连；无 Redis 退回本地 |
| `allkeys-lru` 淘汰持久键 | state/黑名单丢失 | 独立 DB / 改策略 / 提升 maxmemory |
| 强依赖静默失败 | 登录/广播静默错误 | `require_redis()` 显式失败 + 日志/监控 |
| 迁移引入回归 | 聊天/通知异常 | 每阶段回归现有 WS 测试；等价性测试 |
| 订阅连接泄漏 | 连接数增长 | lifespan 统一关闭；断线重连计数可观测 |

---

## 八、测试与验收

- 所有后端测试经 WSL Docker：`wsl bash -lc "cd ~/perseus && docker compose --profile test run --rm test"`（先 `sync_to_wsl.py`）。
- 单测：内存/伪 Redis 后端覆盖路由、去重、降级、TTL、一次性消费。
- 集成：真 Redis 下双 worker 场景（房间广播、定向通知、OAuth state 跨实例、presence 聚合）。
- 回归：`tests/test_websocket_manager.py`、`tests/test_notification_ws.py`、`tests/test_request_stats.py`、
  OAuth 相关测试全绿。
- 验收标准（R2）：4 worker 下，用户在任意 worker 的连接都能收到其订阅房间/仓库/定向通知的消息，且不重复。

---

## 九、遗留与范围界定

1. **部署形态**：本期不依赖横向扩容——单容器 **4 worker 已足以触发**跨进程问题，测试矩阵按 4 worker 设计；`--scale app=N` 作为天然延伸。
2. **Redis 容量/淘汰**：按 D4 调整（仅淘汰带 TTL 键 + 提升 `maxmemory`），随实现更新 `docker-compose.base.yml` 说明。
3. **跨实例**：假定单 Redis 实例，单实例 pub/sub 即可；跨机房不在本期。
4. **R4 / R5**：本期不纳入，完成 R1~R3 后按需再评估（presence、黑名单缓存、热缓存、全局限流）。
