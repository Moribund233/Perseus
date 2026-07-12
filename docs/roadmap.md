# Perseus 产品路线图

> **更新日期**: 2026-07-11
> **定位**: 代码托管 + 在线协作（一体化平台）
> **架构**: 单服务 Python/FastAPI，内置认证授权、实时引擎、Git 托管

---

## 产品愿景

Perseus 是一个基于 Git 的本地化协作开发平台，提供完整的代码托管和团队协作能力。

平台为单一服务架构，所有能力自包含：

| 系统 | 技术栈 | 职责 |
|------|--------|------|
| **Perseus** | Python/FastAPI + Vue 3 + SQLite/PostgreSQL | 全部：代码托管 + 认证授权 + 实时引擎 + 团队聊天 |

### 核心设计原则

- **单服务部署** — 一个 Docker 镜像，统一运维，降低交付复杂度
- **内建实时引擎** — 基于 FastAPI/Starlette 原生 WebSocket，无需外部依赖
- **可插拔认证** — 支持本地账号 + OAuth2 第三方登录（GitHub、GitLab 等）
- **模块内聚** — 实时协作层作为独立模块（`services/realtime/`），与业务层松耦合

---

## 架构总览

```
浏览器 (Vue 3)
    │
    ├── /api/v1/*     ─── REST API（仓库/PR/Issue/用户）
    ├── /ws           ─── WebSocket（聊天/通知/协作/在线状态）
    └── /username/repo.git/* ─── Git HTTP Smart Protocol

Nginx/OpenResty (反向代理)
    │
    ├── app:8000 ─── FastAPI 单体服务
    │   ├── 代码托管核心
    │   │   ├── 仓库管理 / PR / Issue / Code Review
    │   │   ├── Webhook / Release / SSH Key
    │   │   └── 权限校验
    │   │
    │   ├── 认证授权层
    │   │   ├── 本地注册/登录 (JWT)
    │   │   ├── OAuth2 第三方登录 (GitHub, GitLab, …)
    │   │   └── 账号关联管理
    │   │
    │   └── 实时协作引擎 (services/realtime/)
    │       ├── WS 连接管理器
    │       ├── 房间/频道管理
    │       ├── 团队聊天
    │       ├── 在线状态
    │       ├── 业务事件广播 (PR/Issue/Review 变更)
    │       └── 协作文本编辑
    │
    └── git-cgi:9000 ─── fcgiwrap + git-http-backend
```

---

## 阶段规划

### ✅ Phase 0：OAuth2 认证 + 实时引擎基础设施（已完成）

**目标**：支持第三方账号登录，WebSocket 基础链路打通

| ID | 任务 | 说明 | 状态 |
|----|------|------|------|
| P-001 | OAuth2 客户端框架 | 抽象 OAuth2 provider 接口，支持 GitHub / GitLab 登录 | ✅ |
| P-002 | OAuth2 登录流程 | 前端引导 + 后端 code→token 交换 + 用户创建/绑定 | ✅ |
| P-003 | 账号关联管理 | 用户中心绑定/解绑第三方账号，支持多 provider | ✅ |
| P-004 | 现有 JWT 系统增强 | 签发用户时可携带 oauth provider 信息 | ✅ |
| P-005 | WS 连接管理器 | FastAPI WebSocket 路由 + 连接生命周期管理 | ✅ |
| P-006 | Token 身份校验中间件 | WS 建立时通过 query token 或 Auth header 鉴权 | ✅ |

---

### Phase 1：代码托管 MVP（4-6 周）

**目标**：用户可完成完整的代码托管流程

**相关 Prototype**：`landing.html`、`repos.html`、`repo-detail.html`、`pull-requests.html`

| ID | 任务 | 前端页面 | 后端依赖 |
|----|------|---------|---------|
| F-101 | Landing Page | 登录/注册、产品介绍 | — |
| F-102 | 仓库列表页 | 仓库列表、搜索、筛选 | Repo API |
| F-103 | 仓库详情 + 代码查看 | 文件树、代码内容、README | F-022/023/024 |
| F-104 | PR 列表 + 详情 | PR 概览、Diff、合并操作 | PR API (F-013~016) |
| F-105 | Issue 列表 + 详情 | Issue 看板、筛选、批量操作 | F-025/027 |
| F-106 | Code Review 视图 | 逐行评论、Review 审批 | F-028/029 |
| F-107 | Git HTTP 端到端验证 | — | Docker infra (F-017/018) |

**交付标准**：
- 用户可注册/登录（含 OAuth2 登录）
- 创建/浏览仓库
- 提交 PR、做 Code Review
- 通过 Git HTTP 协议 clone/push/pull

---

### Phase 2：实时协作（6-8 周）

**目标**：开发团队可在 Perseus 上实时协作沟通

**相关 Prototype**：`chat.html`、`collab-editor.html`

| ID | 任务 | 模块 | 说明 |
|----|------|------|------|
| F-201 | 房间/频道管理 | `realtime/room` | 仓库↔聊天频道关联，成员加入/离开 |
| F-202 | 团队聊天 | `realtime/chat` | 仓库内聊天、消息持久化、历史记录 |
| F-203 | 业务事件推送 | `realtime/events` | PR/Issue/Review 变更实时广播到房间 |
| F-204 | 协作文本编辑器 | `realtime/collab` | OT/CRDT 基础实现 + 嵌入代码编辑器 |
| F-205 | 实时通知 | `realtime/notify` | @提及、评论、CI 状态 → 站内推送 |
| F-206 | 在线状态 | `realtime/presence` | 仓库/项目内在线成员可见，心跳检测 |

**交付标准**：
- 团队成员可在仓库页面内聊天
- PR/Issue 变更实时推送
- 支持协作文本编辑
- 在线成员状态可见

---

### Phase 3：增强与完善（持续）

| ID | 任务 | 说明 |
|----|------|------|
| F-301 | CI/CD 构建状态 | Webhook → CI 触发 + 结果展示 |
| F-302 | 代码搜索 | 仓库内/跨仓库全文搜索 (F-037/038/039) |
| F-303 | Git LFS | 大文件存储支持 (F-034/035/036) |
| F-304 | 国际化 | 中英文翻译 + API 错误 i18n (F-048/049/050) |
| F-305 | 生产部署 | Docker 完善、监控、压测、安全审计 (F-051~057) |

---

## 项目模块矩阵

| 能力 | 归属模块 | 状态 |
|------|---------|------|
| 代码仓库管理 | `controller/` `models/` `services/` | ✅ 核心 |
| Git HTTP/Smart Protocol | git-cgi 容器 + Nginx | ✅ 就绪 |
| PR / Issue / Code Review | `controller/` `models/` `services/` | ✅ 核心 |
| Webhook | `services/webhook_service.py` | ✅ 核心 |
| 用户认证（本地 JWT） | `services/token_service.py` `controller/auth_controller.py` | ✅ 核心 |
| OAuth2 第三方登录 | `services/auth/oauth.py` | ✅ Phase 0 |
| WebSocket 连接管理 | `api/websocket/manager.py` | ✅ Phase 0 |
| Git LFS | `services/lfs_service.py` `controller/lfs_controller.py` | ✅ Phase 3 |
| 代码搜索 | `services/search_service.py` `controller/search_controller.py` | ✅ Phase 3 |
| 通知系统（站内/邮件） | `services/notification_service.py` `utils/email_utils.py` | ✅ Phase 3 |
| CI/CD Webhook 触发 | `utils/webhook_trigger.py` | ✅ Phase 3 |
| 房间/频道管理 | `services/realtime/room.py` | ✅ Phase 2 |
| 团队聊天 | `services/realtime/chat.py` | ✅ Phase 2 |
| 业务事件广播 | `services/realtime/event_service.py` | ✅ Phase 2 |
| 协作文本编辑 | `services/realtime/collab.py` | ⏳ Phase 2 |
| 在线状态 | `services/realtime/room_service.py`<br>`api/websocket/manager.py` | ✅ Phase 2 |
| 通知系统（实时推送） | `services/realtime/notify.py` | ⏳ Phase 2 |
| 文件上传 | ✅ (代码附件) | ✅ |
| 系统管理/审计 | `middleware/` | ✅ 基础 |

---

## 现有后端进度参考

后端 API/功能点交付进度详见 [`docs/api/roadmap.md`](api/roadmap.md)，当前状态：

- **阶段一（基础功能）**：物理仓库创建、配置系统、PR 合并、JWT 刷新 — **全部完成** ✅
- **阶段二（核心协作）**：SSH Key、代码查看器、Issue、Code Review、Webhook — **后端全部完成** ✅
- **阶段三（高级功能）**：
  - **已完成** ✅：LFS、站内/邮件通知系统与偏好、Webhook 签名与投递、构建状态 API、单仓库代码搜索、Release 附件上传、实时房间/聊天/在线状态/业务事件广播
  - **已完成** ✅：跨仓库代码搜索（F-038）、搜索索引自动维护（F-039）、CI/CD 触发闭环（F-046 后端 PR merge 触发 Build）、Webhook 重试机制（F-031）
  - **未开始** 🔴：协作文本编辑（F-204）、独立实时通知模块（F-205）、国际化（F-048~050）
- **阶段四（生产准备）**：Docker 基础、Nginx 反向代理、基础中间件审计已就绪；监控、压测、安全审计、日志告警 — **待开发** 🔴
