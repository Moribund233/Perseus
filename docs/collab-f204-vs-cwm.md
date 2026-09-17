# F-204 × Code with Me 差距分析与演进规划

> **日期**: 2026-09-07；**2026-09-08 更新**: Yjs 统一底座已落地（5.1 方案 B / D1 决策实施完成）——
> Hocuspocus 哑管道网关 + web `y-codemirror.next` 迁移完成，3.6 方案 B（断线变更保留）随 CRDT 天然解决；
> desktop 待 `y-monaco` 接入。下文现状描述保留为迁移前记录，供追溯。
> **2026-09-14 更新**: desktop T9 y-monaco 接入完成，两端同 Yjs 底座；**M1 短期项全部落地**——
> 3.3 双态徽标（会话已同步/Git 已提交）与 3.2 短期「未保存离开提示」（`beforeunload` × `hasPendingChanges()`）两端实现，
> 详见 `docs/desktop-port-sync.md` 同步批次记录。M2+（邀请链接/TTL/跟随模式）仍待排期。
> **状态**: 规划参考文档（非实施承诺）
> **定位**: 以 JetBrains Code with Me（下称 CwM）为直接参照，梳理 F-204 协作文本编辑的功能差异，按"影响用户体验 → web 端取舍 → desktop 端深化"三层组织，供后续里程碑规划使用。
> **关联**: [`docs/api/websocket/README.md`](api/websocket/README.md) 第 7 节（协议）、[`docs/roadmap.md`](roadmap.md)（阶段三）、[`docs/superpowers/specs/2026-08-03-desktop-app-design.md`](superpowers/specs/2026-08-03-desktop-app-design.md)（desktop 基线）、[`docs/frontend-placeholders.md`](frontend-placeholders.md)（已知限制）

---

## 1. 结论速览

**一句话定位差异**：
CwM 是以 **host 本地磁盘为权威**、面向"结对编程/评审"的**重会话产品**（显式邀请、音视频、受限视图）；
F-204 是以**服务端会话 + Git 提交为权威**的**轻协作能力**（打开文件即共编、变更落 Git 可审计）。

两者是**不同的权威模型**，而非同一功能的完成度差异 —— 这决定了 F-204 不应照抄 CwM，而是吸收其 UX 关键设计。

**差距分层**：

| 层级 | 内容 | 端 |
|------|------|----|
| **P0 UX 关键缺口** | 邀请入口、会话生命周期/数据安全、保存语义心智 | web 可解 |
| **P1 体验增强** | 跟随模式、权限即时性、断线变更保留 | web 可解 |
| **P2 平台化** | 音视频/聊天联动、受限视图、多副本扩展 | web + 服务端 |
| **D 端深化** | host 会话模型、编辑器内核选型、多文件会话 | desktop |

---

## 2. 模型差异本质（规划的边界条件）

| 维度 | Code with Me | F-204 现状 |
|------|--------------|------------|
| 权威端 | host 的 IDE 进程 + 本地磁盘 | 服务端会话（`services/realtime/collab_service.py` 内存态） |
| 变更持久化 | host 决定何时保存文件；VCS 操作仅 host 可做 | 显式 `collab_save` → 服务端以权威文本提交 Git commit（全员广播） |
| 参与身份 | 邀请链接 + host 按人授权（读/写随时切换） | 平台账号 + 仓库角色（join 时校验读权限并缓存写权限） |
| 会话边界 | 显式创建/结束，host 关闭即终结 | 隐式：打开文件即 join，最后一人离开即销毁 |
| 拓扑 | host 星型（guest 流量经 host），host 离线 = 会话终结 | 中心化服务端，host 离线不影响他人 |

**推论**：
1. F-204 的"保存 = Git commit"是**审计优势**（协作内容即时可追溯），但引入了 CwM 没有的"会话内 ≠ 已保存"心智负担 → 见 3.3。
2. F-204 无 host 单点，可用性更好，但代价是**会话生命周期无人负责** → 见 3.2。
3. 服务端权威 + 进程内单例是当前部署约束（`workers=1`/单副本），多副本需要 Redis pub/sub 改造 → 见 5.6。

---

## 3. 影响用户体验的差异（规划优先级依据）

> 每项给出：CwM 行为 / F-204 现状 / UX 影响 / 规划建议。

### 3.1 入口与邀请 — **P0**

- **CwM**：host 一键生成邀请链接（可设只读/可写、有效期），访客浏览器打开即加入，零配置。
- **F-204**：协作者必须拥有平台账号 + 仓库读权限，并**恰好打开同一文件**才会进入同一会话。不存在"邀请"动作。
- **UX 影响**：这是与 CwM 差距最大的一项。协作的建立成本从"发一个链接"变成"注册 → 授权角色 → 找到文件"，即时协作场景（"帮我看下这段代码"）基本不可用。
- **规划建议**：
  - 会话邀请链接：`/collab/:sessionToken`，短时 JWT（绑定 docKey + 只读/可写两档 + 过期时间），无仓库角色者凭 token 获得会话级临时权限。
  - web 端入口：编辑器工具栏"分享协作"按钮 → 生成/复制链接；服务端新增 token 校验层（`collab_join` 支持 token 换临时权限）。
  - 涉及：`api/websocket/handlers/collab.py`（join 权限判定）、新邀请 token service、编辑器 UI。

### 3.2 会话生命周期与数据安全 — **P0**

- **CwM**：host 显式开关会话；guest 内容随时写在 host 磁盘上，会话结束**不丢数据**。
- **F-204**：会话纯内存态，最后一人离开（或断连）即销毁；**未 `collab_save` 的变更直接丢失**，无任何提示。
- **UX 影响**：数据丢失风险 + "我走了别人还在编辑吗"的不确定感。多人协作中最后一人静默离开是常态路径，风险真实存在。
- **规划建议**（按成本递增）：
  1. 短期：前端 `beforeunload`/关闭 tab 时若有 `hasPendingChanges()` 提示；会话参与者列表常显"未保存"徽标。→ **✅ 2026-09-14 beforeunload 拦截已落地（web `routes/editor/index.tsx` / desktop `EditorTabs.tsx`）**；参与者"未保存"徽标未做。
  2. 中期：服务端会话 TTL 延迟销毁（如最后一人离开后保留 10 分钟，期间重 join 恢复现场）。→ **✅ 2026-09-17 网关落地**：`collab-gateway/sessionTtl.mjs`（`PERSEUS_COLLAB_SESSION_TTL_MS`，默认 600000ms；合并 Redis 会话快照后，未提交编辑跨副本/重启也可恢复）。
  3. 长期：可选"自动落盘"策略——会话空闲 N 分钟自动 `collab_save` 到草稿分支（`collab/draft-...`），避免污染目标分支。
  - 涉及：`collab-gateway/sessionTtl.mjs`（TTL/GC）、`collabController.ts`、编辑器 UI。

### 3.3 保存语义心智 — **P0**

- **CwM**：guest 没有"保存"概念（host 磁盘即真相），用户零学习成本。
- **F-204**："协作保存"= Git commit，全员广播 `collab_saved`。用户必须区分"已同步到会话"与"已提交到 Git"两个状态。
- **UX 影响**：当前编辑器仅有 `isDirty` 标记，用户无法得知"当前内容是否已被某人提交过"。CwM 用架构回避了这个问题，F-204 必须用 UI 交代清楚。
- **规划建议**：编辑器状态区显示双态徽标："会话已同步 ✓（版本 N）" / "Git 已提交（短 SHA）"；`collab_saved` 广播已具备全部所需信息。
  - 涉及：`client/web/src/routes/editor/index.tsx`（状态栏）、`collabController.ts`（版本透出）。
  → **✅ 2026-09-14 双态徽标已落地（两端）**：web 编辑器状态栏 + desktop StatusBar（`stores/editorStatus.ts`）；"会话已同步"= connected 且无未同步变更（Yjs `hasUnsyncedChanges` 轮询），"Git 已提交"= 最近一次协作保存 short-SHA（内容再编辑即失效）。「版本 N」未透出，与规划略有出入。

### 3.4 跟随模式（Follow me / Spotlight） — **P1**

- **CwM**：guest 可跟随 host 光标与滚动（"跟我来"），host 可聚焦指定 guest —— 教学/评审场景的核心手段。
- **F-204**：仅有远端光标/选区渲染（`collab_cursor` + widget 标签），无跟随、无聚焦。
- **UX 影响**：远程讲解时对方"看不见我在看哪"，评审场景需要反复口头描述位置。
- **规划建议**：`collab_cursor` 协议已含位置信息，缺的是：跟随状态机（`collab_follow {targetClientID, on}`）+ 滚动位置广播 + 前端平滑滚动跟随。web 端成本可控，建议排入 P1。
  - 涉及：协议扩展（README 第 7 节）、`collabController.ts`、编辑器工具栏开关。

### 3.5 权限颗粒度与即时性 — **P1**

- **CwM**：host 按人、按会话授权，可随时切换只读/可写、可移出会话。
- **F-204**：权限绑定仓库角色（viewer/developer），join 时校验并缓存 `can_write`；会话中变更角色不生效（需重新 join）。
- **UX 影响**：临时协作者必须先经过管理员授予仓库角色，破坏"即时协作"；会话内无法降权/请出捣乱者。
- **规划建议**：
  - 若 3.1 的邀请链接落地（会话级临时权限），本项解决大半；
  - 剩余部分：会话级角色覆盖层（创建者/发起人可作为会话管理员改权限、踢人），协议加 `collab_permission` / `collab_kick` 广播。
  - 涉及：`collab_service.py`（参与者元数据）、`collab.py` handler。

### 3.6 断线容忍 — **P1**

- **CwM**：guest 断线期间**不能编辑**（明确提示连接丢失），重连后恢复当前状态——简单但可预期。
- **F-204**：断线期间可继续本地编辑；重连后重新 join，`collab_init` 会**整篇覆盖为服务端文本**（`handleInit` 的 remote dispatch），断线期间的输入静默丢失。已修复的 rejoin 逻辑保证了同步正确性，但未保证输入保留。
- **UX 影响**：弱网环境（地铁/差旅）下的真实输入丢失，比"不能编辑"更糟——用户以为自己在编辑。
- **规划建议**（二选一，需产品决策）：
  - **方案 A（对齐 CwM，简单）**：断线即编辑锁定（`EditorState.readonly` compartment + 覆盖层提示），重连解锁。
  - **方案 B（超越 CwM，复杂）**：rejoin 时保留本地未确认变更——`collab` 扩展 reconfigure 后将本地 buffer 作为新变更 rebase 到服务端版本（CM6 collab 的 rebase 机制天然支持，需重构 `handleInit` 的整篇覆盖路径）。
  - 涉及：`collabController.ts`。

### 3.7 音视频与聊天联动 — **P2**

- **CwM**：会话内置音视频通话与聊天。
- **F-204**：无；但平台已有独立规划——`services/realtime/room.py`（音视频房间）、`services/realtime/chat.py`（团队聊天），均属 Phase 2 路线。
- **UX 影响**：协作时需切换到聊天/房间上下文，会话内无法感知"正在通话的人就是光标的主人"。
- **规划建议**：不做编辑器内自研音视频，而是**联动既有模块**：协作者列表挂接 presence（正在房间中的人显示通话图标）、会话内一键发起房间并邀请当前参与者。列入 Phase 2 集成项。

### 3.8 访客受限视图 — **P2**

- **CwM**：guest 默认只见 host 打开/共享的文件，不能浏览整个项目。
- **F-204**：持有仓库读权限（或未来邀请 token）即可打开任意文件加入任意会话。
- **UX 影响**：隐私边界（协作者可能只想展示一个文件，而非开放全仓库浏览）。
- **规划建议**：依赖 3.1 邀请 token 的 scope 设计——token 绑定 docKey 时，仅该文档可 join（服务端 join handler 已按 docKey 判定，天然可落地）；仓库角色用户维持全仓库视图不变。

---

## 4. Web 端取舍（有意的简化，非遗漏）

> 以下是 web 端相对 CwM 的**主动取舍**，规划时不应视为"待补齐"，除非产品定位变化。

| 取舍点 | CwM 对照 | 理由 / 备注 |
|--------|----------|-------------|
| 单文件会话（`repo:branch:path`） | 多文件项目级会话 | 浏览器场景以"打开一个文件共编"为主；多文件留给 desktop（见 5.3） |
| 无终端/运行/调试/重构 | guest 可用有限 IDE 能力 | web 编辑器职责边界；desktop 端以 LSP 补齐（desktop spec 既定） |
| 服务端权威 + 单变更日志（5000 条环形，超出即 `collab_resync`） | IntelliJ 双端 OT + undo 协同 | 实现简单、可测（26 例覆盖）；undo 协同（跨用户 undo 语义）暂不支持，属已知取舍 |
| 光标位置在本地有未确认变更时短暂偏移（自校正） | 精确映射 | 已记录于 `docs/frontend-placeholders.md`；显示层问题，不影响数据 |
| 无离线合并 | 同样受限（CwM 断线即不可编辑） | 见 3.6 方案决策 |
| 消息上限 2MB（UTF-8 字节）/ 文档 2M 字符 | — | 防御性上限，超大文件协作不在场景内 |
| **进程内单例会话注册表** | CwM 专用 relay 基础设施 | **部署约束**：仅支持 `workers=1` / 单副本；多副本需 Redis pub/sub 改造（见 5.6），上线规模化前必须处理 |

---

## 5. Desktop 端深化方向

> 基线：desktop spec（Wails v2 + React + **Monaco Editor**，定位"远程 Perseus 客户端 + 本地工作区"）。
> CwM 的 host-centric 模型恰好与 desktop 的"本地文件系统权威"定位同构 —— **desktop 是承接 CwM 完整体验的合适载体**（协作场景在 desktop spec 中标注为"非目标（首版）"，本文档为后续版本规划输入）。

### 5.1 编辑器内核与协同协议选型 — **✅ 已冻结（2026-09-07 决策 D1）**

- **现状**：web 端 CM6 + `@codemirror/collab`（ChangeSet JSON 协议）；desktop spec 选定 **Monaco**（VS Code 同源、monaco-languageclient 生态）。
- **冲突**：Monaco 无原生 OT 协同，与 F-204 协议不兼容；重写 Monaco OT 适配成本高。
- **候选方案**：
  - **A. desktop 嵌入 CM6**（编辑器区域用 CM6，其余 IDE 布局不变）：零协议适配直接复用 `/ws/collab` 全栈，但与 Monaco/LSP 生态割裂，编辑器内核双轨。
  - **B. 统一协同层 Yjs**：web/desktop 均迁 Yjs（y-codemirror.next + y-monaco），服务端 y-websocket/Y 网关；CRDT 天然支持离线合并（连带解决 3.6 方案 B），但需重写 F-204 服务端与前端同步层，Git 快照落盘逻辑需重接。
  - **C. F-204 协议 + Monaco 适配层**：在 Monaco 上实现 ChangeSet 协议客户端（自维护 OT 映射），成本最高，不建议。
- **✅ 决策：方案 B**——两端统一 Yjs 协同底座，现在冻结并作为独立里程碑（Y 网关基建 + web 端先行迁移，desktop `y-monaco` 随后接入）；LSP 桥（spec §8）与 Yjs 正交，Phase 3 不受阻塞。落地依赖与排期见 [`superpowers/specs/2026-09-07-desktop-decisions.md`](superpowers/specs/2026-09-07-desktop-decisions.md) D1。

### 5.2 Host 会话模型（desktop 独有能力）

- desktop 拥有本地文件系统与本地 git CLI（desktop spec 既定），可承载 **CwM 同构的 host 模型**：guest 变更实时写入 host 工作区，host 决定何时 commit/push；服务端仅做信令与中继（可复用 `/ws/collab` 通道或独立信令通道）。
- 价值：guest 无需平台账号即可经邀请链接协作（权限收敛到 host），F-204 web 模型（服务端 Git 权威）保持不变 —— 两种会话类型并存：`server-authoritative`（web）/ `host-authoritative`（desktop）。

### 5.3 多文件/项目级会话与受限视图

- desktop 侧具备项目树能力，可做**多文件会话**（一次邀请覆盖多个打开的文件）与 **guest 受限视图**（仅暴露会话文件集合），对应 CwM 的完整体验；web 端维持单文件会话不变。

### 5.4 音视频深化

- web 端走"联动既有 room/chat 模块"（3.7）；desktop 端可考虑 WebRTC 直连（本地应用无 CORS/自动播放限制），并共享同一 presence 身份体系。

### 5.5 断线容忍与本地缓冲

- desktop 本地有完整文件缓冲，断线期间编辑写入本地 op 缓冲、重连重放 rebase（方案 B 的桌面版天然更强）；配合 5.2 host 模型时，guest 断线语义与 CwM 对齐。

### 5.6 服务端演进（两端共用）

1. **多副本支持** ✅ **2026-09-17**：Hocuspocus 网关经 `@hocuspocus/extension-redis` 在副本间经 Redis pub/sub 广播 CRDT 变更与感知（进程内广播不再跨进程），解除 `workers=1` 约束 —— 规模化前置条件。实现于 `collab-gateway/server.mjs` + `redisPersistence.mjs`；compose `collab` 服务已接 `REDIS_URL`、移除 `container_name` 以支持 `--scale`。（nginx 动态解析/负载均衡留待真正扩容时处理）
2. **会话持久化** ✅ **2026-09-17**：`@hocuspocus/extension-database` 将 Y.Doc 全量快照周期写入 Redis，冷加载优先恢复（未提交编辑跨副本/短重启不丢），TTL 保留窗口支撑 3.2 中期方案；多副本冷启动播种经 Redis 锁（`seed-lock`）串行化，避免各自独立 insert 造成 `hellohello` 重复。实现于 `collab-gateway/redisPersistence.mjs`。
3. ** invited-token 体系**（3.1/3.8）：邀请签发/校验/撤销服务。

### 5.7 明确不做（成本收益衡量）

- 对齐 Live Share 级别的能力（共享终端、共享调试会话、协同 IDE 重构）——超出平台定位；
- 编辑器内自研音视频栈 —— 复用 room 模块。

---

## 6. 里程碑草案（供排期参考）

| 里程碑 | 端 | 内容 | 对应章节 |
|--------|----|------|----------|
| **M1（短期）** | web | ~~未保存离开提示、保存/同步双态徽标~~ **✅ 2026-09-14 两端落地**；会话 TTL 延迟销毁 **✅ 2026-09-17 网关落地** | 3.2 / 3.3 |
| **M2** | web | 邀请链接 + 会话级临时权限（token 换权限）、跟随模式基础版 | 3.1 / 3.4 / 3.5 |
| **M3** | web | 断线策略决策落地（锁定 or rebase 保留）、受限视图（token scope） | 3.6 / 3.8 |
| **M4** | 服务端 | Redis pub/sub 多副本、会话持久化 **✅ 2026-09-17 网关落地（= 5.6 第 1/2 项）** | 5.6 |
| **M5** | desktop | 内核选型冻结 → host 会话模型、多文件会话、音视频联动 | 5.1 / 5.2 / 5.3 / 5.4 |
| 随 Phase 2 | 平台 | room/chat presence 联动 | 3.7 |

---

## 7. 参考基准说明

- CwM 行为描述基于 JetBrains Code with Me 公开文档与产品行为（host-guest 模型、邀请链接与按人授权、follow/spotlight、guest 受限视图、内置音视频、host 磁盘权威）。
- F-204 现状描述基于本文撰写时的代码（含本轮修复：重连 rejoin、pull 协议统一、写权限会话内缓存）。
