# Perseus 产品路线图

> **更新日期**: 2026-06-15
> **定位**: 代码托管 + 在线协作
> **架构**: Perseus (代码托管) + CapellaRoom (授权 & 实时引擎)

---

## 产品愿景

Perseus 是一个基于 Git 的本地化协作开发平台，提供完整的代码托管和团队协作能力。

平台由两大子系统构成：

| 系统 | 技术栈 | 职责 |
|------|--------|------|
| **Perseus** | Python/FastAPI + Vue 3 | 代码托管核心：仓库、PR/Issue、Code Review、Webhook |
| **CapellaRoom** | Rust/Axum + PostgreSQL/Redis | 实时协作引擎：认证授权、WebSocket、团队聊天 |

---

## 架构总览

```
浏览器 (Vue 3)
    │
    ├── Perseus :8000 (FastAPI ─ SQLite/PostgreSQL)
    │   ├── 代码托管 API (/api/v1)
    │   ├── Git HTTP Smart Protocol (/git/*)
    │   └── CapellaRoom 集成层
    │
    └── CapellaRoom :3000 (Axum ─ PostgreSQL + Redis)
        ├── 认证授权 API (/api/v1/auth)
        ├── 用户/好友/设备 API
        ├── WebSocket 实时服务 (/ws)
        └── Perseus 集成端点

Nginx/OpenResty (反向代理，按路径分发)
```

### 对接设计

#### 认证集成
- CapellaRoom 作为认证中心，统一 JWT 签发/验证
- Perseus 将注册/登录委托给 CapellaRoom
- 用户绑定：Perseus 用户 ID 与 CapellaRoom 账号 ID 映射
- Perseus API 层保留权限校验，身份验证调用 CapellaRoom

#### 实时通信
- Perseus 前端直接连接 CapellaRoom WebSocket (`/ws`)
- 事件类型：PR 变更、Issue 更新、Code Review 评论、聊天消息、@提及
- CapellaRoom 扩展事件类型，覆盖 Perseus 业务场景

#### 部署拓扑
- 两个服务独立部署，通过 docker-compose 编排
- Nginx/OpenResty 统一入口，按路径分发
- CapellaRoom 可选启用 Redis 支持分布式

---

## 阶段规划

### Phase 0：基础设施对接（2-3 周）

**目标**：两个项目完成集成对接，可本地联调

| ID | 任务 | 项目 | 说明 |
|----|------|------|------|
| P-001 | 暴露 OAuth-like 授权端点 | CapellaRoom | 供 Perseus 调用（code → token 交换） |
| P-002 | 用户信息查询 API | CapellaRoom | 供 Perseus 同步用户信息 |
| P-003 | 认证客户端 SDK | Perseus | 注册/登录委托 CapellaRoom |
| P-004 | 统一 JWT 策略 | 共同 | 共享 secret 或 token 交换机制 |
| P-005 | 部署整合 | 共同 | docker-compose 网络互通 + 反向代理路由 |
| P-006 | Perseus 认证替换 | Perseus | 移除现有本地 auth，改为 CapellaRoom 委托 |

**交付标准**：Perseus 用户可通过 CapellaRoom 登录，两服务 docker-compose 一键启动

---

### Phase 1：代码托管 MVP（4-6 周）

**目标**：用户可完成完整的代码托管流程

**相关 Prototype**：`landing.html`、`repos.html`、`repo-detail.html`、`pull-requests.html`

| ID | 任务 | 项目 | 前端页面 | 后端依赖 |
|----|------|------|---------|---------|
| F-101 | Landing Page | Perseus | 登录/注册、产品介绍 | — |
| F-102 | 仓库列表页 | Perseus | 仓库列表、搜索、筛选 | Repo API |
| F-103 | 仓库详情 + 代码查看 | Perseus | 文件树、代码内容、README | F-022/023/024 |
| F-104 | PR 列表 + 详情 | Perseus | PR 概览、Diff、合并操作 | PR API (F-013~016) |
| F-105 | Issue 列表 + 详情 | Perseus | Issue 看板、筛选、批量操作 | F-025/027 |
| F-106 | Code Review 视图 | Perseus | 逐行评论、Review 审批 | F-028/029 |
| F-107 | Git HTTP 端到端验证 | 共同 | — | Docker infra (F-017/018) |

**交付标准**：
- 用户可注册/登录
- 创建/浏览仓库
- 提交 PR、做 Code Review
- 通过 Git HTTP 协议 clone/push/pull

---

### Phase 2：实时协作（4-6 周）

**目标**：开发团队可在 Perseus 上实时协作沟通

**相关 Prototype**：`chat.html`、`collab-editor.html`

| ID | 任务 | 项目 | 说明 |
|----|------|------|------|
| F-201 | 项目房间映射 | CapellaRoom | 新增仓库↔聊天室关联 API |
| F-202 | 团队聊天 | Perseus | prototype chat.html 生产化，嵌入仓库页面 |
| F-203 | 业务事件推送 | CapellaRoom | 扩展 WS 事件：PR/Issue/Review 变更 |
| F-204 | 协作文本编辑器 | Perseus | prototype collab-editor.html 生产化 |
| F-205 | 实时通知 | 共同 | PR 评论、@提及、CI 状态推送到聊天 |
| F-206 | 在线状态 | 共同 | 仓库/项目内在线成员可见 |

**交付标准**：
- 团队成员可在仓库页面内聊天
- PR/Issue 变更实时推送
- 支持协作文本编辑
- 在线成员状态可见

---

### Phase 3：增强与完善（持续）

| ID | 任务 | 项目 | 说明 |
|----|------|------|------|
| F-301 | CI/CD 构建状态 | Perseus | Webhook → CI 触发 + 结果展示 |
| F-302 | 代码搜索 | Perseus | 仓库内/跨仓库全文搜索 (F-037/038/039) |
| F-303 | Git LFS | 共同 | 大文件存储支持 (F-034/035/036) |
| F-304 | 国际化 | Perseus | 中英文翻译 + API 错误 i18n (F-048/049/050) |
| F-305 | 生产部署 | 共同 | Docker 完善、监控、压测、安全审计 (F-051~057) |

---

## 项目分工矩阵

| 能力 | Perseus | CapellaRoom |
|------|---------|-------------|
| 代码仓库管理 | ✅ 核心 | — |
| Git HTTP/Smart Protocol | ✅ 核心 | — |
| PR / Issue / Code Review | ✅ 核心 | — |
| Webhook | ✅ 核心 | — |
| 用户认证授权 | — | ✅ 核心 (OAuth/SSO) |
| WebSocket 实时通信 | — | ✅ 核心 |
| 团队聊天 | 前端集成 | ✅ API + WS |
| 协作文本编辑 | 前端集成 | ✅ 实时同步能力 |
| 在线状态 / 设备管理 | — | ✅ |
| 文件上传 | ✅ (代码) | ✅ (附件) |
| 通知系统 | 前端展示 | ✅ 推送管道 |
| 系统管理/审计 | 各自实现 | 各自实现 |

---

## 现有后端进度参考

后端 API/功能点交付进度详见 [`docs/api/roadmap.md`](api/roadmap.md)，当前状态：

- **阶段一（基础功能）**：物理仓库创建、配置系统、PR 合并、JWT 刷新 — **全部完成** ✅
- **阶段二（核心协作）**：SSH Key、代码查看器、Issue、Code Review、Webhook — **后端全部完成** ✅
- **阶段三（高级功能）**：LFS、代码搜索、WebSocket、通知、CI/CD、i18n — **待开发**
- **阶段四（生产准备）**：Docker、监控、压测、安全审计 — **待开发**
