# LanGit 重构路线图

## 概览

本路线图将项目从"过度兼容的烂尾状态"重构为"聚焦核心功能的 Git 协作平台"。
核心思路是**砍掉无差异化的兼容层，回归产品本质**。

| 阶段 | 内容 | 状态 |
|---|---|---|
| Phase 0 | 确立架构基线，清理依赖 | ✅ 已完成 |
| Phase 1 | 砍掉 Git HTTP 自研层 | ✅ 已完成 |
| Phase 2 | Docker 化，删除 Windows 兼容 | ✅ 已完成 |
| Phase 3 | 简化数据库层 | ✅ 已完成 |
| Phase 5 | 配置系统反转 | ✅ 已完成 |
| Security | 移除 Tauri 本地认证后门 | ✅ 已完成 |
| Phase 4 | 核心功能开发 | ⏳ 待开始 |

---

## Phase 0 — 确立架构基线 ✅

**目标：** 在多数据库支持上做减法，明确 PostgreSQL 为主力数据库。

### 完成情况

- 从 `pyproject.toml` 移除 `pymysql`、`aiomysql`、`pg8000`
- 移除 `psycopg2` 的平台标记
- 删除 `utils/migration/dialect.py`、`connection.py`、`schema.py` 中所有 MySQL 逻辑
- 删除 `core/config.py` `DatabaseSettings` 中所有 `mysql_*` 属性
- 删除 `models/__init__.py` 中 `_create_mysql_engine()` 及相关函数
- 删除 `models/async_db.py` 中 MySQL URL 转换分支
- 清理 `utils/db_validation.py`、`services/config_service.py`、`controller/debug_controller.py` 等
- 同步驱动从 `pg8000` 迁移到 `psycopg2`

---

## Phase 1 — 砍掉 Git HTTP 自研层 ✅

**目标：** 用 Nginx + `git-http-backend` CGI 替代 Python 层自建的 Git HTTP 协议实现。

### 完成情况

- 删除 `controller/git_http_controller.py`（590 行）
- 删除 `services/git_http_service.py`（539 行）
- 从 `app.py` 移除 `git_http_router` 注册
- 编写 `docker/nginx/nginx.conf`，含 git-http-backend 的 location 块
- 更新 `api/api_v1.py` 注释

---

## Phase 2 — Docker 化 + 删除 Windows 兼容 + 精简生命周期 ✅

### 完成情况

- 新建 `Dockerfile`（多阶段构建）
- 新建 `docker-compose.yml`（Nginx + FastAPI + PostgreSQL）
- 新建 `.dockerignore`
- 删除 `utils/ipc_manager.py`（393 行）
- 删除 `utils/port_utils.py`（260 行）
- 删除 `tests/test_lifecycle_gunicorn.py`（475 行）
- `core/lifespan.py`：移除 IPC/Master/Worker，精简为单进程
- `core/gunicorn_worker.py`：移除平台判断和 IPC 集成
- `core/gunicorn.conf.py`：移除 IPC 钩子
- `core/init.py`：移除 `port_utils` 引用
- `app.py` `start_server()`：移除 `is_windows`、PID 文件
- `services/app_service.py`：移除 `os.name` 分支
- `core/config.py`：移除 Windows 编码处理

---

## Phase 3 — 简化数据库层 ✅

### 完成情况

- 初始化 Alembic 迁移框架（`alembic/` 目录）
- 配置 `alembic/env.py` 从 `DATABASE_URL` 环境变量读取连接
- 生成初始迁移 `1143975a9442_initial.py`（16 张表）

---

## Phase 5 — 配置系统反转 ✅

**目标：** 配置源从代码 `Field(default=...)` 转移到 `config.example.toml`。

### 完成情况

- 编写 `config.example.toml`（带注释的配置模板）
- 删除 `generate_default_config()` 函数
- `core/init.py`：config.toml 不存在时报错提示从模板复制
- `services/config_service.py`：reset_config 改为从 `config.example.toml` 读取
- 清理 `utils/config_utils.py` 中无用导入

---

## Security — 移除 Tauri 本地认证后门 ✅

**背景：** 原 Tauri Client 通过 `LANGIT_LOCAL_TOKEN` + `X-LanGit-Local: 1` 请求头实现本地认证绕过 JWT。

### 完成情况

| 风险点 | 严重性 | 处理 |
|---|---|---|
| `api/local_auth.py` — 整个本地认证模块 | **严重** | 删除文件 |
| `api/dependencies.py` — 本地认证覆盖 JWT | **高** | 改为纯 JWT |
| `controller/app_controller.py` — 独立注入本地用户 | **高** | 改为纯 JWT |
| `controller/debug_controller.py` — 调试端点无 debug mode 检查 | **严重** | 添加 `require_debug_mode` |
| `api/websocket/auth.py` — WebSocket 本地令牌验证 | **中** | 移除 |

### 附带 Bug 修复

- `RateLimitConfig` 的 `@classmethod @property` 与 Python 3.13 不兼容 → 修复
- `slowapi` 0.1.9 与 Python 3.13 不兼容 → 移除，限流改由 Nginx 处理

---

## Phase 4 — 核心功能开发 ⏳

**目标：** 在简化的架构上专注开发 Git 协作平台的差异化功能。

### P0 — 基础设施

- SSH 访问（`git-shell`）
- HTTPS 支持（Let's Encrypt）

### P1 — 核心协作功能

- **Pull Request 工作流** — 创建、审查、合并、冲突检测
- **Issue 系统** — 创建、分配、标签、里程碑、看板
- **仓库权限模型** — 角色（Owner/Maintainer/Developer/Reader）、分支保护

### P2 — 提效功能

- **WebHook** — 事件触发 + CI/CD 集成
- **Release 管理** — Tag / Release / Asset
- **文件浏览** — 目录树、Diff、Blame

---

## 代码清理汇总

| 阶段 | 删除行数 | 修改行数 | 新增行数 |
|---|---|---|---|
| Phase 0 | ~200 | ~50 | 0 |
| Phase 1 | ~500 | ~30 | ~80 |
| Phase 2 | ~600 | ~200 | ~60 |
| Phase 3 | ~800 | ~300 | ~100 |
| Phase 5 | ~60 | ~100 | ~150 |
| Security | ~150 | ~400 | ~50 |
| **合计** | **~2310** | **~1080** | **~440** |

---

## 项目当前结构

```
lan-git/
├── api/                    # FastAPI 路由（纯 JWT 认证）
├── controller/             # 控制器层
├── core/                   # 配置 / 初始化 / 生命周期
├── docker/                 # Docker 编排（含 git-http-backend）
├── models/                 # SQLAlchemy ORM 模型
├── services/               # 业务逻辑层
├── utils/                  # 工具模块
├── alembic/                # 数据库迁移
├── config.example.toml     # 配置模板
├── Dockerfile              # 多阶段构建
├── docker-compose.yml      # Nginx + FastAPI + PostgreSQL
└── ROADMAP.md              # 本文件
```
