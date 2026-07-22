# Perseus

> 一个基于 Git 的本地化协作开发平台 — 轻量级自托管代码托管与协同开发系统。

Perseus 提供完整的代码仓库管理、Pull Request 工作流、Issue 跟踪、实时协作、WebHook 通知和代码搜索能力，旨在为团队或开发者提供一个可自部署的 Git 协作解决方案。

---

## 目录

- [技术栈](#技术栈)
- [架构概览](#架构概览)
- [功能特性](#功能特性)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
  - [开发环境](#开发环境)
  - [生产部署](#生产部署)
- [API 概览](#api-概览)
- [数据库支持](#数据库支持)
- [许可证](#许可证)

---

## 技术栈

### 后端

| 组件 | 技术 | 说明 |
|------|------|------|
| Web 框架 | **FastAPI** | 高性能异步 API 框架（Python 3.12+） |
| ASGI 服务器 | **Uvicorn** / **Gunicorn** | 开发 / 生产环境 |
| ORM | **SQLAlchemy 2.0** | 异步数据库操作 |
| 数据库迁移 | **Alembic** | 数据库版本管理 |
| Git 引擎 | **pygit2** (libgit2) | 原生 Git 操作（init, tree, blob, commit, merge, diff） |
| 认证 | **python-jose** | JWT 令牌认证（双令牌：access + refresh） |
| 密码加密 | **passlib + bcrypt** | 安全密码哈希 |
| 包管理 | **UV** | 高性能 Python 包管理器 |
| 实时通信 | **WebSocket** | 实时消息、通知推送、协作同步 |

### 前端

| 组件 | 技术 | 说明 |
|------|------|------|
| 框架 | **React 19 + TypeScript 6** | |
| 构建工具 | **Vite 8** | 快速构建，手动代码分割 |
| UI 组件 | **Ant Design 6** | 企业级 UI 组件库（GitHub 暗色主题） |
| 状态管理 | **Zustand 5** | 轻量响应式状态存储 |
| 路由 | **React Router v7** | SPA 路由管理（Layout Routes + Protected Routes） |
| 代码编辑器 | **CodeMirror 6** | 多语言代码高亮（Python, JS, CSS, HTML, JSON, Markdown, XML） |
| 表单 | **React Hook Form + Zod 4** | 类型安全表单验证 |
| 国际化 | **i18next** | 中英文双语支持 |
| 包管理 | **pnpm** | 快速、节省磁盘的包管理 |

### 基础设施

| 组件 | 技术 | 说明 |
|------|------|------|
| 反向代理 | **Nginx / OpenResty** | TLS 终止、Git Smart Protocol、WebSocket 代理、速率限制 |
| 容器化 | **Docker Compose** | 多环境容器编排（开发/生产） |
| 数据库 | **SQLite / PostgreSQL** | 双数据库支持，异步驱动自动适配 |
| 代码搜索 | **FTS5 + ripgrep** | SQLite 全文索引 + ripgrep 回退 |

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Nginx / OpenResty                            │
│        TLS · CORS · Rate Limit · Git Smart Protocol · WS Proxy     │
└────────┬────────────────────────────┬──────────────────────────────┘
         │                            │
    ┌────▼────────────────────┐  ┌───▼──────────────┐
    │   FastAPI Application   │  │   git-cgi (fcgi) │
    │     (Uvicorn 4 workers) │  │   git-http-backend│
    └────┬────────────────────┘  └──────────────────┘
         │
    ┌────▼─────────────────────────────────────────────┐
    │              Middleware Stack                     │
    │  Concurrency → RequestTimeLog → SecurityHeaders  │
    │  → AuditLogger → RequestStats                    │
    └────┬─────────────────────────────────────────────┘
         │
    ┌────▼─────────────────────────────────────────────┐
    │              27 API Controllers                   │
    │  Auth · Users · Repos · PRs · Issues             │
    │  Releases · Webhooks · Search · WebSocket        │
    │  OAuth · SSH Keys · LFS · Stats · Chat · Build   │
    └────┬─────────────────────────────────────────────┘
         │
    ┌────▼─────────────────────────────────────────────┐
    │              Service Layer                        │
    │  token · user · repo · pr · issue · search       │
    │  webhook · notification · oauth · git · lfs      │
    │  realtime (room/chat/event) · stats · build      │
    └────┬─────────────────────────────────────────────┘
         │
    ┌────▼─────────────────────────────────────────────┐
    │              Data Layer                           │
    │  SQLAlchemy ORM · 25+ tables                     │
    │  UUID7 PKs · SQLite (WAL) / PostgreSQL           │
    │  Sync + Async engines · Alembic migrations       │
    └──────────────────────────────────────────────────┘
```

### 中间件管线（注册顺序）

| 中间件 | 功能 |
|--------|------|
| `ConcurrencyMiddleware` | 限制并发请求数，超载时返回 503 |
| `RequestTimeLoggerMiddleware` | 记录超时慢请求（默认 30s 阈值） |
| `SecurityHeadersMiddleware` | 添加安全 HTTP 头，移除服务器指纹 |
| `AuditLoggerMiddleware` | 全量请求审计日志（IP、用户、路径、耗时） |
| `RequestStatsMiddleware` | 内存中的请求统计（QPS、成功率、平均延迟） |

---

## 功能特性

### 📦 代码仓库管理
- 创建、删除、归档/取消归档仓库
- 公开/私有仓库权限控制
- Fork 仓库（完整 clone + rewrite）
- 仓库星标（Star/Unstar）
- 仓库访问控制（Owner / Admin / Developer / Readonly 四级角色）
- 物理仓库缓存（30s TTL，减少磁盘 I/O）

### 🔀 Pull Request 工作流
- 创建 / 关闭 / 合并 PR（Source → Target Branch）
- Draft PR（草稿模式）
- PR 评论与 Review（代码审查工作流）
- PR 标签管理
- Merge 冲突检测
- PR 时间线活动记录

### 🐞 Issue 跟踪
- Issue 创建 / 关闭 / 重新打开
- Issue 优先级与标签
- 批量操作（批量关闭、批量更新、批量打标签）
- Issue 评论

### 🔍 代码搜索
- **FTS5 全文索引** — 增量构建、实时搜索
- **ripgrep 回退** — FTS5 未命中时自动降级
- 文件符号（Symbol）提取与语言识别

### 🔔 通知与 WebHook
- **双通道通知** — 数据库持久化 + WebSocket 实时推送 + 可选邮件
- 通知偏好设置
- **WebHook** — 支持 18 种事件类型，HMAC-SHA256 签名
- WebHook 投递历史与重试

### 🔐 认证与安全
- JWT 双令牌（Access + Refresh Token）
- OAuth 2.0 登录（GitHub / GitLab）
- SSH 密钥管理（指纹验证）
- Git HTTP Smart Protocol 认证（Nginx `auth_request`）
- 安全响应头（HSTS, CSP, XSS 保护等）
- 敏感数据过滤（日志脱敏）

### 💬 实时协作
- **WebSocket Hub** — 连接管理器（基于用户/仓库/房间三级路由）
- 实时聊天（仓库频道）
- 实时通知推送
- 仓库活动广播
- WebSocket 心跳检测

### 📤 发布管理
- Release 创建与标签管理
- Release 附件上传与下载
- Draft / Pre-release 模式

### 🏗️ CI 集成
- 构建状态追踪（pending / running / success / failure / error / cancelled）
- WebHook 驱动的 CI 触发

### 🎯 其他
- Git LFS 支持（本地存储或 S3）
- 仓库统计（Stars, Forks, 活跃度等）
- 审计日志（基于 Activity 模型的完整操作记录）
- 应用管理（状态、重启、日志查看/清理）
- 配置热加载与校验
- 压力测试模式
- SQLite WAL 模式优化

---

## 项目结构

```
perseus/
├── app.py                        # 应用入口（App Factory）
├── pyproject.toml                # Python 项目配置（UV）
├── config.example.toml           # 配置文件模板
│
├── core/                         # 基础设施层
│   ├── config.py                 # Pydantic 配置管理（TOML + 环境变量）
│   ├── constants.py              # 系统常量（角色优先级等）
│   ├── exception.py              # 异常层次结构（20+ 自定义异常）
│   ├── init.py                   # 应用初始化管线
│   ├── lifespan.py               # 应用生命周期（启动/关机）
│   ├── gunicorn.conf.py          # Gunicorn 生产配置
│   └── gunicorn_worker.py        # 自定义 Uvicorn Worker（uvloop）
│
├── models/                       # 数据库模型层
│   ├── base.py                   # 基类 + TimestampMixin（UUID7 PK）
│   ├── uuid7.py                  # RFC 9562 时间有序 UUID 生成器
│   ├── async_db.py               # 异步引擎工厂
│   ├── user.py                   # 用户模型
│   ├── repository.py             # 仓库模型
│   ├── repository_member.py      # 仓库成员模型
│   ├── branch.py / commit.py     # 分支与提交
│   ├── pull_request.py           # Pull Request 模型
│   ├── pr_activity.py            # PR 活动记录
│   ├── pr_label.py               # PR 标签
│   ├── issue.py                  # Issue 模型（含标签、评论）
│   ├── release.py                # Release 模型（含附件）
│   ├── webhook.py                # WebHook 模型（含投递记录）
│   ├── ssh_key.py                # SSH 密钥模型
│   ├── stargazer.py              # 星标模型
│   ├── repo_label.py             # 仓库级标签
│   ├── activity.py               # 审计活动模型
│   ├── notification.py           # 通知模型（含偏好设置）
│   ├── user_oauth.py             # OAuth 账号关联
│   ├── realtime_room.py          # 实时聊天室
│   ├── chat_message.py           # 聊天消息
│   └── build_status.py           # 构建状态
│
├── api/                          # API 路由层
│   ├── routes_config.py          # 中心路由注册器（27 个控制器）
│   ├── dependencies.py           # FastAPI 依赖注入（用户认证）
│   ├── error.py                  # 错误信息 API
│   └── websocket/                # WebSocket 子系统
│       ├── manager.py            # 连接管理器（用户/仓库/房间索引）
│       ├── router.py             # WS 端点（/ws, /ws/logs, /ws/notifications）
│       ├── auth.py               # WS 令牌认证
│       └── handlers/             # 消息处理器
│           ├── chat.py / room.py / notification.py
│           ├── sync.py / progress.py / log_handler.py
│
├── controller/                   # HTTP 路由处理器（27 个控制器）
│   ├── app_controller.py         # 应用管理（状态/重启/日志）
│   ├── auth_controller.py        # 登录/刷新
│   ├── git_auth_controller.py    # Git HTTP Smart Protocol 认证
│   ├── oauth_controller.py       # OAuth 登录（GitHub/GitLab）
│   ├── user_controller.py        # 用户管理
│   ├── repository_controller.py  # 仓库 CRUD
│   ├── repository_browser_controller.py  # 仓库浏览（树/文件/diff）
│   ├── repository_member_controller.py   # 成员管理
│   ├── branch_controller.py      # 分支操作
│   ├── commit_controller.py      # 提交历史
│   ├── pull_request_controller.py        # Pull Request
│   ├── pr_label_controller.py    # PR 标签
│   ├── release_controller.py     # Release
│   ├── issue_controller.py       # Issue
│   ├── label_controller.py       # 仓库标签
│   ├── fork_controller.py        # Fork
│   ├── star_controller.py        # Star/Unstar
│   ├── lfs_controller.py         # Git LFS
│   ├── key_controller.py         # SSH 密钥
│   ├── webhook_controller.py     # WebHook
│   ├── build_controller.py       # 构建状态
│   ├── stats_controller.py       # 仓库统计
│   ├── activity_controller.py    # 审计日志
│   ├── notification_controller.py # 通知
│   ├── search_controller.py      # 代码搜索
│   ├── room_controller.py        # 实时聊天室
│   ├── chat_controller.py        # 聊天消息
│   └── debug_controller.py       # 调试端点
│
├── services/                     # 业务逻辑层
│   ├── token_service.py          # JWT 令牌管理
│   ├── user_service.py           # 用户业务逻辑
│   ├── repository_service.py     # 仓库业务逻辑
│   ├── repository_browser_service.py  # 仓库浏览（pygit2 操作）
│   ├── issue_service.py          # Issue 业务逻辑
│   ├── pull_request_service.py   # PR 业务逻辑
│   ├── search_service.py         # 代码搜索（FTS5 + ripgrep）
│   ├── webhook_service.py        # WebHook 投递
│   ├── notification_service.py   # 通知管理
│   ├── oauth_service.py          # OAuth 流程
│   ├── auth/                     # OAuth 提供者
│   │   └── oauth.py              # GitHub / GitLab  Provider
│   ├── realtime/                 # 实时协作服务
│   │   ├── room_service.py       # 聊天室管理
│   │   ├── chat_service.py       # 聊天消息
│   │   └── event_service.py      # 事件广播
│   ├── dashboard_service.py      # 用户仪表盘
│   ├── fork_service.py           # Fork 仓库
│   ├── star_service.py           # 星标管理
│   ├── label_service.py          # 标签管理
│   ├── pr_label_service.py       # PR 标签管理
│   ├── pr_activity_service.py    # PR 活动
│   ├── build_service.py          # 构建状态
│   ├── stats_service.py          # 仓库统计
│   ├── branch_service.py         # 分支管理
│   ├── commit_service.py         # 提交查询
│   ├── release_service.py        # Release 管理
│   ├── key_service.py            # SSH 密钥管理
│   ├── member_service.py         # 成员角色管理
│   ├── activity_service.py       # 审计活动
│   ├── lfs_service.py            # Git LFS
│   ├── lfs_storage.py            # LFS 存储后端
│   ├── config_service.py         # 配置管理
│   ├── app_service.py            # 应用运维
│   ├── notification_preference_service.py  # 通知偏好
│   └── database_manager.py       # 数据库管理
│
├── middleware/                    # HTTP 中间件
│   ├── concurrency.py            # 并发限制
│   ├── timeout.py                # 慢请求日志
│   ├── security_headers.py       # 安全响应头
│   ├── audit_logger.py           # 审计日志
│   └── request_stats.py          # 请求统计
│
├── utils/                        # 工具模块
│   ├── git_utils.py              # pygit2 Git 操作封装
│   ├── ripgrep_utils.py          # ripgrep 代码搜索
│   ├── password_utils.py         # 密码哈希（bcrypt）
│   ├── security_utils.py         # 敏感数据过滤
│   ├── response_builder.py       # 统一 JSON 响应构建
│   ├── permission_utils.py       # 权限检查
│   ├── logging.py                # 日志系统（多文件 + WS 广播）
│   ├── exception_handler.py      # 全局异常处理器
│   ├── email_utils.py            # SMTP 邮件发送
│   ├── db_utils.py               # 数据库辅助（exists, paginate）
│   ├── db_validation.py          # 数据库配置验证
│   ├── init_database.py          # 数据库初始化 + 管理员引导
│   ├── config_utils.py           # 配置文件工具
│   ├── webhook_trigger.py        # WebHook HTTP 投递
│   └── lfs_utils.py              # LFS 工具
│
├── middleware/                    # HTTP 中间件
├── scripts/                      # 启动脚本
│   ├── dev-start.sh              # Linux / WSL 开发启动
│   └── dev-start.ps1             # Windows PowerShell 启动
│
├── client/                       # 前端应用
│   ├── web/                      # React + TypeScript
│   │   ├── src/
│   │   │   ├── app/              # 应用入口 + Router
│   │   │   ├── pages/            # 页面组件
│   │   │   ├── stores/           # Zustand 状态
│   │   │   ├── components/       # 通用组件
│   │   │   ├── locales/          # i18n 语言包（zh/en）
│   │   │   ├── api/              # API 客户端
│   │   │   └── styles/           # 样式
│   │   ├── vite.config.ts        # Vite 配置
│   │   └── package.json
│   └── prototype/                # 原型 HTML
│
├── docker/                       # Docker 配置
│   ├── nginx/                    # Nginx 配置（生产/开发/1Panel）
│   ├── dev/                      # 开发 Dockerfile
│   └── git-cgi/                  # Git HTTP Smart Protocol 容器
│
├── docker-compose.yml            # 生产 Docker Compose
├── docker-compose.dev.yml        # 开发 Docker Compose
├── Dockerfile                    # 生产 Dockerfile（多阶段构建）
│
├── tests/                        # 测试套件（80+ 测试文件）
│   ├── conftest.py               # 测试夹具
│   └── test_*.py                 # 按模块划分的测试
│
├── alembic/                      # 数据库迁移
│   ├── env.py                    # Alembic 环境配置
│   └── versions/                 # 迁移版本
│
└── .codegraph/                   # 代码图谱索引
```

---

## 快速开始

### 开发环境

**前置要求：** Python 3.12+, Docker, pnpm

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd perseus

# 2. 配置环境变量
cp config.example.toml config.toml
# 编辑 config.toml 或设置环境变量：
export DATABASE_URL="sqlite:///./perseus_dev.db"
export PERSEUS_SECURITY_SECRET_KEY="your-secret-key"

# 3. 使用 Docker Compose 启动开发环境
cd scripts && bash dev-start.sh
```

开发环境会启动：
- **FastAPI 后端** (`:8000`) — 带热重载
- **git-cgi 服务** (`:9000`) — Git HTTP Smart Protocol
- **测试容器** — 运行 `pytest`
- **前端** — 宿主机执行 `pnpm dev` (`:5173`)

### 生产部署

```bash
# 1. 配置生产环境变量
export DATABASE_URL="postgresql://user:pass@host:5432/perseus"
export PERSEUS_SECURITY_SECRET_KEY="<strong-secret>"

# 2. 启动生产栈
docker compose up -d --build
```

生产部署需要外部维护：
- **PostgreSQL** 数据库
- **Redis** 缓存（可选）
- **Nginx / OpenResty** 反向代理（提供 TLS、CORS、Git Smart Protocol、速率限制）

详细的 Nginx 配置见 `docker/nginx/`。

---

## API 概览

所有 API 端点以 `/api/v1/` 为前缀。认证采用 JWT Bearer Token。

| 模块 | 前缀 | 主要端点 |
|------|------|----------|
| **认证** | `/api/v1/auth` | `POST /login`, `/refresh`, OAuth (GitHub/GitLab) |
| **用户** | `/api/v1/users` | `GET /me`, `/me/dashboard`, `/me/pull-requests`, `/me/issues`, CRUD |
| **仓库** | `/api/v1/repositories` | CRUD, `/tree`, `/blob`, `/commits`, `/diff`, `/readme`, Fork, Star |
| **Pull Request** | `/api/v1/repositories/{id}` | `GET/POST /pull-requests`, `/merge`, `/comments`, `/reviews` |
| **Issue** | `/api/v1/repositories/{id}` | `GET/POST /issues`, `/close`, `/reopen`, `/batch/*` |
| **WebHook** | `/api/v1/repositories/{id}` | WebHook CRUD + 投递历史 |
| **Release** | `/api/v1/repositories/{id}` | Release + 附件管理 |
| **搜索** | `/api/v1/repositories/{id}` | `GET /search` 代码搜索 |
| **通知** | `/api/v1/notifications` | 通知 CRUD + 偏好设置 |
| **SSH密钥** | `/api/v1/keys` | SSH 密钥管理 |
| **实时协作** | `/api/v1/repositories/{id}` | 聊天室 + 消息 |
| **Git LFS** | `/api/v1/repositories/{id}` | LFS 锁/批量操作 |
| **构建** | `/api/v1/repositories/{id}` | 构建状态 |
| **WebSocket** | `/ws` | 主连接、日志流、通知、仓库频道 |
| **应用管理** | `/api/app` | 状态、重启、日志、配置 |

> 完整 API 文档在开发模式下访问 `/docs` (Swagger UI) 或 `/redoc` (ReDoc)。

---

## 数据库支持

### 支持的数据库

| 数据库 | 同步驱动 | 异步驱动 | 说明 |
|--------|----------|----------|------|
| **SQLite** | 内置 | `aiosqlite` | 开发/小规模部署（默认 WAL 模式） |
| **PostgreSQL** | `psycopg2` | `asyncpg` | 生产环境推荐 |

### 关键设计

- **UUID7 主键** — 时间有序 UUID（RFC 9562），避免传统 UUID 的索引碎片问题
- **双引擎** — 同步引擎（Alembic 迁移）+ 异步引擎（运行时查询）
- **SQLite 优化** — WAL 模式、NORMAL 同步、MEMORY 临时存储
- **URL 自动转换** — 异步驱动 URL 自动适配（`postgresql://` → `postgresql+asyncpg://`）

---

## 许可证

本项目基于 MIT 许可证开源。详见 [LICENSE](LICENSE) 文件。
