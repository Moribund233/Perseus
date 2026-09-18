# Desktop 开发决策记录（2026-09-07）

> **日期**: 2026-09-07
> **背景**: web 端迭代速度远超 desktop（20 vs 8 commits，聊天/通知/协作编辑/搜索/Releases/Builds 均未移植），继续开发前对代码现状与方向做了全面评审，确认以下五项决策。
> **代码现状结论**: Phase 1 / 2A / 2B 均已完成（以代码为准，plan checkbox 未回填）；架构（Wails v2 + Go 本地网关 + 密钥库 + 反向代理 + 离线缓存）经实践验证，定位"远程客户端 + 本地工作区，IDE 优先"继续成立。

---

## 决策清单

| # | 决策项 | 结论 | 影响 |
|---|--------|------|------|
| **D1** | 编辑器内核与协同协议 | **Monaco + 现在冻结 Yjs 统一协同层** | web（CM6）与 desktop（Monaco）未来协作统一迁移 Yjs 底座；LSP 桥按 spec §8 继续走 WS JSON-RPC（与协同层正交） |
| **D2** | 前端复用策略 | **维持拷贝移植 + 移植同步清单** | 不做 monorepo/共享包改造；以 [`desktop-port-sync.md`](../../desktop-port-sync.md) 跟踪两端差异，移植时对照 |
| **D3** | 2A/2B 收尾批次 | **5 项全做**：push/pull UI、clone 凭据输入 UI、多标签编辑器（Ctrl+S/关闭保护）、Settings 实做、servers.update 死路由修复 | 下一批开发内容，均为小体量；push/pull 的服务器端依赖（git-http-auth）已就绪 |
| **D4** | Phase 2C（聊天/通知移植） | **推后，聚焦 IDE 能力** | LSP/多标签/Git 面板增强优先级高于聊天移植；web 端已覆盖协作沟通场景；2C 重排期待定 |
| **D5** | 平台范围 | **维持 Windows-only**（NSIS 收尾期） | keychain 维持 Windows Credential Manager；macOS/Linux 架构已预留，不提前投入 |

---

## D1 展开说明（影响最大）

**选择**：编辑器内核维持 Monaco（spec 既定），协同协议**现在**冻结为 **Yjs 统一协同层**（对应 [`collab-f204-vs-cwm.md`](../../collab-f204-vs-cwm.md) 5.1 方案 B），而非"协作需求出现时再重估"。

**落地含义与依赖**（按实施顺序）：

1. **Phase 3 LSP 不受阻塞**：LSP 走 `WS /ws/lsp/{workspaceId}` JSON-RPC + Monaco providers（spec §8），与 Yjs 正交，可先行推进；pyright/tsserver 最小验证仍为前置。
2. **服务端新增 Y 网关基建**：y-websocket/y-redis（多副本）承担 CRDT 同步；现 F-204 的 CM6 collab OT authority（`services/realtime/collab_service.py`）是**过渡实现**，迁移时以 Yjs 文档模型重接"会话 ↔ Git 快照落盘"（`collab_save` 语义保留）。
3. **两端客户端改造**：web `@codemirror/collab` → `y-codemirror.next`；desktop `y-monaco`。协议层（`/ws/collab` 消息族）将由 Yjs 同步协议取代或包裹，迁移窗口内两者并存。
4. **附带收益**：CRDT 天然离线合并，`collab-f204-vs-cwm.md` 3.6 的"断线变更保留"（方案 B）随之解决；desktop 断线本地缓冲（该文 5.5）同一底座。
5. **排期建议**：Y 网关基建与 web 端迁移宜在 desktop 协作排期前完成（避免两次迁移）；作为独立里程碑规划，见 collab-f204-vs-cwm.md §6 修订。

## 排期修订（覆盖 collab-f204-vs-cwm.md §6 与 desktop spec §10 的重叠部分）

```
下一批（收尾批次, D3）
  → push/pull UI + clone 凭据 + 多标签编辑器 + Settings + servers.update 修复
下一批之后二选一（可并行）:
  → Phase 3 LSP 最小验证（pyright 诊断链路 → monaco providers）✅ LSP/终端 WS 桥已落地（2026-09-08）
  → Y 网关基建 + web 端 F-204 迁移 Yjs（D1 既定路线）✅ 2026-09-08 完成
之后:
  → desktop 接入 Yjs 协同（y-monaco）✅ 2026-09-10 完成（T9：Go 首帧 token 注入代理 + Monaco 绑定）
  → Phase 2C 聊天/通知 ✅ 已随 UI 补全批次完成（T4/T5，2026-09-10）；follow ✅ 2026-09-17 双端、受限视图 ✅ 2026-09-18（邀请 token 绑定 docKey 准入天然实现）；host-authoritative 模型在 Yjs 底座下已非必需，维持未决观察
  → Phase 4 增强收尾（SSH 推送、mDNS、托盘/单实例/NSIS）
```

## 未决事项（无需现在拍板，到排期时再议）

- mDNS 服务发现：依赖服务器端 `_perseus._tcp` 发布（跨项目），维持 Phase 4
- LSP 语言范围：维持 Python（pyright）+ TS/JS（tsserver）
- desktop 协作的 host-authoritative 模型（collab-f204-vs-cwm.md 5.2）：待 Yjs 底座落地后评估
