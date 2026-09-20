# 文档归档区

> **建立日期**: 2026-09-18；**2026-09-20 整理**: 移除 `superpowers` 目录约定（源自外部 skill，仓库不再使用），规划文档统一迁往 `docs/plans/`。
> **用途**: 存放已交付/已落地的历史设计与规划文档（desktop 全生命周期），与活跃规划（`docs/plans/`）和活跃文档（`docs/` 根目录、`docs/api/`）分离。
> **约定**: 归档文件一律标注「**已归档，不再更新**」。归档仅移动位置与修正链接，不改写实施记录。

---

## 目录结构

```
docs/
  plans/             → 活跃规划文档（进行中/未来计划 + roadmap/todos/port-sync 台账）；新建规划请放这里
  guides/            → 活跃指南（部署 + 用户手册）
  api/               → API 契约文档（README/roadmap/http/websocket）
  archive/
    plans/           → 已完成的实现计划
    specs/           → 已交付的基线设计与决策 Spec
    reports/         → 一次性交付的验收报告（压测、安全审计）
```

## 已归档实现计划（`archive/plans/`）

| 文件 | 归属阶段 | 完成依据 |
|------|----------|----------|
| `2026-07-13-git-http-auth` | Git HTTP Smart Protocol JWT 认证 | `controller/git_auth_controller.py` + `docker/gateway/nginx.conf` `auth_request` 均在库中（2026-09-07 回填） |
| `2026-08-03-desktop-app-phase1` | Desktop Phase 1 骨架（store/keychain/fs/git/gateway/IDE 布局） | Phase 1/2A/2B 全部交付，以代码为准（2026-09-07 回填；`internal/{store,fs,git,gateway}` 均在库中） |
| `2026-08-08-phase2b-issues-pullrequests` | Web/Desktop Issues + PR 页面与迁移 | 全部任务完成；遗留小项见 `docs/plans/desktop-port-sync.md`（2026-09-07 回填） |
| `2026-09-08-desktop-ui-completion` | Desktop UI 补全 + y-monaco 协作接入（T1–T10） | 全部落地；预留 Task 8（Builds/Releases）亦由 2026-09-14 的 port-sync T8 补齐 |

## 已交付设计/Spec（`archive/specs/`）

| 文件 | 角色 |
|------|------|
| `2026-08-03-desktop-app-design` | desktop 基线设计（多处链接指向） |
| `2026-08-04-desktop-app-phase2a-design` | Phase 2A 阶段设计（已交付） |
| `2026-08-08-phase2b-issues-pullrequests-design` | Phase 2B 阶段设计（已交付；含指向归档计划的链接） |
| `2026-09-07-desktop-decisions` | desktop 方向决策记录 D1–D5（长期引用） |

## 规划约定

- 新建规划/待办/方案文档请放置于 **`docs/plans/`**（当前含 `roadmap.md`、`todos.md`、`desktop-port-sync.md`、`collab-f204-vs-cwm.md`、`admin-console.md`、`frontend-placeholders.md`）。
- 新建指南（部署/用户/运维）请放置于 **`docs/guides/`**。
- 实施完成后标注完成状态，并按需移入 `docs/archive/` 对应子目录（计划→`plans/`、设计→`specs/`、验收报告→`reports/`）。
- 双端移植差异仍以 `docs/plans/desktop-port-sync.md` 为准；任务总账与迭代状态见 `docs/plans/todos.md`。