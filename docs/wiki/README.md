# Perseus — Code Wiki

> 本目录是 Perseus 后端项目的结构化代码百科，面向新成员上手和资深成员速查。
> 文档基于实际仓库代码生成，若代码与文档不符，以代码为准。

---

## 阅读顺序

建议按以下顺序阅读，可循序渐进理解项目：

| 序号 | 文档 | 覆盖范围 |
|------|------|----------|
| 0 | [📐 项目总览与架构](01-overview.md) | 项目定位、技术栈、分层架构图、运行时拓扑、数据流 |
| 1 | [⚙️ 核心基础设施（core）](02-core.md) | 配置管理、应用初始化、生命周期、异常体系、常量 |
| 2 | [🗄️ 数据模型层（models）](03-models.md) | ORM 基类、UUID7、同步/异步引擎、25+ 数据模型一览 |
| 3 | [🔌 服务层（services）](04-services.md) | 40+ Service 职责、依赖关系、关键类与入口函数 |
| 4 | [🛣️ 控制器与 API 路由（controller + api）](05-controllers.md) | 34 个 Controller 清单、路由注册顺序、依赖注入 |
| 5 | [📡 WebSocket 子系统](06-websocket.md) | 连接管理器、消息路由、handlers、实时广播总线 |
| 6 | [🛡️ 中间件与工具库（middleware + utils）](07-middleware-utils.md) | 请求管线、6 个中间件、19 个 utils 模块 |
| 7 | [🧱 协同网关与桌面端（collab-gateway + client）](08-collab-client.md) | Node.js Yjs 网关、Go 桌面端 Wails 应用、前端 |
| 8 | [🚀 部署与运行](09-deployment.md) | Docker Compose、Nginx、启动脚本、测试、数据库迁移 |

---

## 关键事实速查

| 事实 | 值 |
|------|----|
| Python 版本 | 3.12（`>=3.12,<3.13`） |
| 包管理 | UV（构建后端 hatchling） |
| Web 框架 | FastAPI 0.141 |
| ORM | SQLAlchemy 2.0（同步 psycopg2 + 异步 asyncpg） |
| 数据库 | PostgreSQL（生产） / SQLite（测试/开发） |
| 迁移工具 | Alembic |
| Git 引擎 | pygit2（libgit2） |
| 异步引擎 | uvicorn[standard] 0.52 |
| WSGI 生产 | gunicorn + 自定义 `PerseusUvicornWorker` |
| Git HTTP | Nginx + `git-http-backend`（独立容器） |
| 可选 Redis | 跨 worker 广播 + 并发计数 |
| 可选 Sentry | 错误监控（DSN 为空自动跳过） |
| 测试 | pytest + pytest-asyncio（auto 模式） |
| 前端 | React 19 + Vite 8 + Zustand 5 + React Router v7 |
| 桌面端 | Wails（Go + WebView） |
| 协同网关 | Node.js（Yjs 协议 + Redis 持久化） |

---

## 项目分层一览

```
┌───────────────────────────────────────────────────────────────────┐
│  Perseus                                                           │
│                                                                   │
│  ┌─────────────────────── 外部交互层 ───────────────────────┐    │
│  │  Nginx · git-cgi · collab-gateway · 客户端 (Web/Desktop) │    │
│  └─────────────────────────────┬────────────────────────────┘    │
│                                │                                   │
│  ┌─────────────────────── 应用层 ────────────────────────────┐    │
│  │  controller/ · api/routes_config · api/websocket/          │    │
│  │  (34 控制器 · WS 路由 · 依赖注入)                          │    │
│  └─────────────────────────────┬────────────────────────────┘    │
│                                │                                   │
│  ┌─────────────────────── 业务层 ────────────────────────────┐    │
│  │  services/ · services/realtime/ · services/auth/         │    │
│  │  (40+ Service · token · oauth · realtime · metrics …)     │    │
│  └─────────────────────────────┬────────────────────────────┘    │
│                                │                                   │
│  ┌─────────────────────── 数据层 ────────────────────────────┐    │
│  │  models/ · models/async_db · alembic/                     │    │
│  │  (SQLAlchemy ORM · 25+ 表 · UUID7 PKs · 双引擎)           │    │
│  └─────────────────────────────┬────────────────────────────┘    │
│                                │                                   │
│  ┌─────────────────────── 基础设施 ──────────────────────────┐    │
│  │  core/ · middleware/ · utils/ · docker/                    │    │
│  │  (config · lifespan · exception · 6 middleware · 19 utils) │    │
│  └───────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────┘
```

---

## 目录约定

- Python 源码以 `snake_case.py` 命名
- 数据模型（`models/`）按业务域一个文件一个模型/聚合
- Service 层遵循"每个业务域一个 service 文件"
- Controller 层与 Service 层一一对应（`pull_request_controller.py` ↔ `pull_request_service.py`）
- WebSocket handlers 按消息类型拆分（chat / room / notification / sync / progress / log）
- 测试文件按 `test_<module>.py` 命名，与源码同层或集中在 `tests/`
- 数据库迁移版本存放在 `alembic/versions/`，前缀字母按字母序执行

---

## 代码风格

- Black（line-length=88, target-version=py312）
- isort（profile=black）
- flake8
- pytest asyncio_mode=auto

---

## 变更说明

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-09-21 | 基于仓库快照首次生成 |
