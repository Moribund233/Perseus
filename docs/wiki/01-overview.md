# 01 · 项目总览与架构

> 回答三个问题：**Perseus 是什么**、**长什么样**、**如何工作**。

---

## 1. 项目定位

**Perseus** 是一个基于 Git 的**自托管本地化协作开发平台**，提供代码仓库托管、Pull Request、Issue、实时协作编辑、WebHook、代码搜索和 CI 集成等 GitHub/GitLab 类核心能力。

### 产品能力矩阵

| 能力 | 后端模块 | 前端入口 |
|------|---------|---------|
| 用户 / OAuth 认证 | auth_controller · oauth_service | Landing 登录页 |
| 仓库 CRUD + 浏览 | repository_controller · repository_browser_service | RepositoriesView |
| PR 工作流 | pull_request_controller · pull_request_service | PullRequestsView |
| Issue 跟踪 | issue_controller · issue_service | IssuesView |
| Release + 附件 | release_controller · release_service | ReleasesPanel |
| Git LFS | lfs_controller · lfs_service + lfs_storage | — |
| 搜索（主库索引 + pg_trgm） | search_controller · search_service | GlobalSearchView |
| 实时协作编辑 | collab-* controller · collab-gateway | CollabMonaco |
| 聊天 / 通知 | chat/room_controller · notification_service | ChatView · NotificationsPanel |
| 构建 / CI | build_controller · build_service | BuildsPanel |
| 管理员控制台 | app_controller · redis_admin_service · monitoring_service | Admin 路由 |
| 统计 / 指标 | stats_controller · prometheus_metrics · metrics_service | Admin Overview |
| 健康 / 配置热加载 | app_controller · config_service | — |

---

## 2. 运行时拓扑

```
                           ╔══════════════════════╗
                           ║   浏览器 / 桌面端     ║
                           ╚═══════════╦══════════╝
                                       │ HTTPS / WS
                           ╔═══════════▼══════════╗
                           ║  Nginx / OpenResty   ║
                           ║  TLS · CORS · WS代理 ║
                           ║  Rate Limit · 路由    ║
                           ╚══════╦═══════╦═══════╝
                                  │       │
               ┌──────────────────┘       └──────────────────┐
               │                                             │
   ╔══════════─▼═════════╗                        ╔════════─▼═══════════╗
   ║  FastAPI 应用         ║                        ║  git-cgi (fcgi)       ║
   ║  gunicorn × workers   ║                        ║  git-http-backend     ║
   ║  ├─ HTTP /api/*       ║                        ║  (clone/push)         ║
   ║  ├─ WebSocket /ws*    ║                        ╚════════─╦═══════════╝
   ║  └─ /metrics 监控     ║                                  │
   ╚══════════╦═══════════╝                                  │
              │                                              │
              ▼                                              ▼
   ╔═══════════════════════╗                      ╔═══════════════════════╗
   ║ PostgreSQL            ║                      ║ 磁盘仓库 (bare)        ║
   ║ (主数据)               ║                      ║ ./repositories/*/     ║
   ╚══════════╦═══════════╝                      ╚═══════════════════════╝
              │
              ▼ （可选）
   ╔═══════════════════════╗        ╔═══════════════════════╗
   ║ Redis                  ║◄──────║ collab-gateway (Node) ║
   ║ 跨 worker 广播 · TTL   ║        ║ Yjs · lib0 · 协作编辑  ║
   ╚═══════════════════════╝        ╚═══════════════════════╝
              ▲
              │ （可选）
   ╔══════════╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴首保↗
                           ┌──────────────────────────────────┘
                           │
   ╔═══════════════════════╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴ref

   ╔═══════════════════════╗        ╔═══════════════════════╗
   ║ Grafana (可选)         ║        ║ Prometheus (可选)       ║
   ╚═══════════════════════╝        ╚═══════════════════════╝
```

---

## 3. 依赖关系图（分层）

```
core  ───────────────────────────────────────► 配置 / 异常 / 生命周期
 │
 ├──► models/async_db  ──► SQLAlchemy 异步引擎
 │
 ├──► utils/*          ──► 跨领域工具函数
 │
 └──► middleware/*      ──► HTTP 请求管线
 
api/routes_config ──► controller/* ──► services/* ──► models/*
                      │                  │
                      └──► services/realtime (WebSocket 事件)
                      └──► utils/git_utils (pygit2 裸仓操作)
                      └──► utils/redis_client (Redis)
                      └──► utils/email_utils (SMTP)
```

### 外部依赖

| 依赖 | 模块 | 说明 |
|------|------|------|
| pygit2 | repository_browser_service · git_utils | 仓库树/blob/diff/merge 等 Git 操作 |
| python-jose | token_service | JWT access + refresh 双令牌 |
| passlib + bcrypt | password_utils | 密码哈希 |
| redis | realtime_bus · worker_registry · redis_admin_service | 跨 worker 广播 / 注册表 / 管理 |
| httpx | webhook_service · oauth_service · git_auth_controller | HTTP 客户端（WebHook 投递 / OAuth / Smart Protocol） |
| aiosmtplib | email_utils | SMTP 邮件通知 |
| prometheus_client | prometheus_metrics | /metrics 端点 |
| sentry-sdk | core.sentry | Sentry 错误监控 |
| jinja2 | release_service（生成 Changelog 模板）| Release 描述模板 |

---

## 4. 典型请求流

### 4.1 HTTP REST API

```
客户端 → Nginx
          │
          ▼
   FastAPI (gunicorn/uvicorn)
          │
   ┌──────┴──────┬──────────────┬──────────────┐
   ▼             ▼              ▼              ▼
Concurrency  Timeout  Security  Audit  RequestStats
Middleware   Logger   Headers   Logger Middleware
          │
          ▼
api/routes_config.create_api_router()
          │ （依赖注入 get_current_user）
          ▼
controller/<X>_controller.py  router.<method>("/path")
          │ （解析 Pydantic 请求体、调用 service）
          ▼
services/<X>_service.py  async def do_xxx(db, ...)
          │ （业务校验 · 权限 · pygit2 操作 · 写库）
          ▼
models/<X>.py  async_session.execute(select/insert/...)
          │
          ▼
     PostgreSQL / SQLite
```

### 4.2 Git Smart Protocol

```
git clone/push ──► Nginx (location ~ .git)
                       │ ┌─ auth_request → Git-Auth Controller (/api/v1/git/auth)
                       │ │  ← JWT 校验 / SSH 指纹 / 权限检查
                       │ └─ 成功后 → git-cgi 容器
                       │
                       ▼
                  git-http-backend
                       │
                       ▼
                  磁盘裸仓 ./repositories/owner/repo.git
```

### 4.3 WebSocket 实时协作

```
浏览器 ──► /ws?token=<access>
              │
              ▼
        api.websocket.auth 校验 JWT
              │
              ▼
        ConnectionManager 注册 + 心跳
              │
        ┌─────┼──────┬──────────┬──────────┬──────────┐
        ▼     ▼      ▼          ▼          ▼          ▼
      chat  room  notification  sync    progress   log
     handler handler handler  handler handler handler
        │
        ├──► 进程内 → Connection.broadcast()
        │
        └──► utils.realtime_bus  ──► Redis PUBSUB
                                            │
                                            ▼ 其他 worker 的 bus 转发
                                                  │
                                                  ▼
                                            其他 worker 的 ConnectionManager
```

### 4.4 协作编辑（Yjs + collab-gateway）

```
桌面端 / Web 端 (Monaco + lib0/client)
              │  WebSocket (Yjs protocol)
              ▼
collab-gateway (Node.js, server.mjs + lib0)
              │
              ├──► Redis (session 持久化 TTL, versionCounter, redisPersistence)
              │
              ├──► /api/v1/collab-internal/* (Python 内部回调, HMAC 签名)
              │       └──► collab_internal_controller
              │             └──► collab_session_service / collab_invite_service
              │                   （权限 / 踢人 / 邀请校验）
              │
              └──► 客户端 ack / awareness 广播
```

---

## 5. 启动流程（精确顺序）

```python
# app.py
def create_app() -> FastAPI:
    # 1. init_app() —— 分层初始化管线
    core.init.AppInitializer.initialize()
        ├─ 加载 .env（非 pytest）
        ├─ 检查必需环境变量
        ├─ 延迟导入 core.config / utils.logging
        ├─ 加载并校验 config.toml
        ├─ 校验配置完整性
        ├─ 初始化日志系统
        ├─ 检查 PERSEUS_SECURITY_SECRET_KEY
        ├─ 数据库迁移 + 管理员引导（自动模式）或就绪校验（生产模式）
        └─ 创建仓库根目录 ./repositories

    # 2. Sentry init（未配置 DSN 零开销）
    core.sentry.init_sentry(config)

    # 3. 创建 FastAPI 实例（带 lifespan）
    app = FastAPI(lifespan=core.lifespan.app_lifespan)

    # 4. 添加 6 个中间件（顺序：最先添加 = 最外层）
    app.add_middleware(ConcurrencyMiddleware, ...)
    app.add_middleware(RequestTimeLoggerMiddleware, ...)
    app.add_middleware(SecurityHeadersMiddleware, ...)
    app.add_middleware(AuditLoggerMiddleware)
    app.add_middleware(RequestStatsMiddleware, ...)
    app.add_middleware(PrometheusMetricsMiddleware, ...)

    # 5. 注册所有 API 路由（34 个 controller + WS + error）
    from api.routes_config import api_v1_router
    app.include_router(api_v1_router)

    # 6. 全局异常处理器
    utils.exception_handler.setup_exception_handlers(app)

    # 7. Sentry ASGI 中间件（最外层）
    app = core.sentry.sentry_middleware(app)

    return app


# lifespan (应用启动后、请求进入前)
async def app_lifespan(app):
    # startup:
    #   ├─ get_async_engine() —— 异步引擎初始化
    #   ├─ SELECT 1 连接验证
    #   ├─ WebSocket heartbeat_checker 协程
    #   ├─ realtime_bus.start()（Redis 可用 → 启用跨 worker 广播）
    #   ├─ worker 心跳（写 Redis worker_registry，20s 周期）
    #   └─ 进程指标采样（内存/CPU）
    yield {"lifecycle_manager": ...}
    # shutdown:
    #   ├─ 取消 worker 心跳
    #   ├─ 停止指标采样
    #   ├─ 停止 realtime_bus
    #   ├─ 优雅关闭所有 WS 连接（广播 shutdown 消息, code=1001）
    #   └─ dispose 异步引擎
```

---

## 6. 跨切面关注点

### 认证

- HTTP：`Authorization: Bearer <access_token>`（JWT HS256，默认 30 min）
- Refresh：双令牌，7 天有效；`RevokedToken` 表支持注销
- WebSocket：URL query `?token=<access_token>`（由 `api.websocket.auth` 校验）
- Git HTTP Smart Protocol：Nginx `auth_request` 到 `/api/v1/git/auth`
- 协作网关：由网关独立生成 JWT（`parseConnectionToken`），内含 session_id + owner 签名

### 权限

```
core.constants.ROLE_PRIORITY = {
    "owner": 4, "admin": 3, "developer": 2, "readonly": 1
}
```

仓库成员权限 = 角色优先级比较（`utils.permission_utils` 封装）。

### 日志

- 应用日志：`utils.logging.init_logging`（按日期目录，app.log + error.log 分开）
- 审计日志：`AuditLoggerMiddleware` → `logs/audit.log`（按大小轮转 10MB × 5 份）
- 审计日志可选：通过 WebSocket 实时广播到管理员控制台
- 敏感信息过滤：`utils.security_utils`（password / token / secret 脱敏）

### 监控

- Prometheus：`/metrics`（RequestCount / RequestLatency / 进程指标）
- 进程指标：`ProcessMetrics`（内存/CPU 15s 采样，后台任务）
- Admin 控制台 `/api/v1/admin/*` 提供完整实时管理面板

---

## 下一章

👉 [02 · 核心基础设施（core）](02-core.md)
