# 09 · 部署与运行

> 从本地开发到生产多容器，完整启动方式。

---

## 一、前置要求

| 依赖 | 版本 |
|------|------|
| Python | 3.12（`<3.13`） |
| Docker | ≥ 20.10 |
| Docker Compose | ≥ v2 |
| pnpm | （前端） |
| UV | Python 包管理 |
| PostgreSQL | ≥ 14（生产） |
| Redis | ≥ 6（可选，生产推荐） |
| Node.js | ≥ 18（collab-gateway） |
| Go | ≥ 1.22（桌面端构建） |

---

## 二、本地开发（Docker Compose）

### 2.1 Windows PowerShell

```powershell
.\scripts\dev-start.ps1                # 启动所有服务
.\scripts\dev-start.ps1 build          # 强制重新构建镜像
.\scripts\dev-start.ps1 stop            # 停止服务
.\scripts\dev-start.ps1 logs            # 查看日志
.\scripts\dev-start.ps1 shell           # 进入后端容器
.\scripts\dev-start.ps1 clean           # 停止并清除所有数据
```

### 2.2 Linux / WSL

```bash
bash scripts/dev-start.sh               # 启动
bash scripts/dev-start.sh stop          # 停止
```

### 2.3 开发栈启动内容

| 容器 | 端口 | 说明 |
|------|------|------|
| FastAPI 后端 | `:8002` | 热重载 + Uvicorn |
| git-cgi | `:9001` | git-http-backend |
| collab-gateway | — | Yjs 网关 |
| PostgreSQL | `:5432` | 开发数据库 |
| Redis | `:6379` | 跨 worker 广播 |
| 前端（宿主机） | `:5173` | Vite dev server |

### 2.4 手动启动（不使用 Docker）

```bash
# 1. 安装依赖
uv sync

# 2. 复制配置
cp config.example.toml config.toml
export DATABASE_URL="postgresql://perseus:perseus@localhost:5432/perseus"
export PERSEUS_SECURITY_SECRET_KEY="your-strong-secret-here"

# 3. 启动（自动迁移 + 管理员引导）
python app.py

# 4. 前端（另一个终端）
cd client/web
pnpm install
pnpm dev
```

---

## 三、生产部署

### 3.1 Docker Compose 栈

```yaml
# docker-compose.yml （生产）
services:
  app:           # FastAPI（gunicorn × 4 workers）
  git-cgi:       # git-http-backend
  collab:        # collab-gateway
  nginx:         # Nginx 反向代理
  postgres:      # PostgreSQL
  redis:         # Redis（生产必需）

profiles:
  init:          # 一次性初始化任务
  monitoring:    # Prometheus + Grafana
```

### 3.2 首次部署

```bash
# 1. 准备生产环境变量
export DATABASE_URL="postgresql://user:pass@host:5432/perseus"
export PERSEUS_SECURITY_SECRET_KEY="<strong-secret>"
# 其他可选: PERSEUS_SENTRY_DSN, PERSEUS_REDIS_URL, PERSEUS_OAUTH_GITHUB_*

# 2. 初始化（schema 迁移 + 管理员引导，幂等）
docker compose --profile init run --rm init

# 3. 启动完整栈
docker compose up -d --build
```

> 生产多容器下，`app` 启动时只做 **只读就绪校验**（`PERSEUS_INIT_DATABASE=false`），schema 必须已由独立的 `init` 任务迁移到位。开发模式默认 `true`，启动时自动迁移。

### 3.3 Dockerfile（多阶段构建）

```dockerfile
# Stage 1: 依赖安装
FROM python:3.12-slim AS builder
RUN pip install uv && uv pip install --system --target=/app ...

# Stage 2: 运行时
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app /app
COPY . /app
EXPOSE 8000
CMD ["gunicorn", "-c", "core/gunicorn.conf.py", "app:app"]
```

---

## 四、Nginx 配置

### 4.1 生产

位置：`docker/nginx/nginx.conf`

核心路由：

```nginx
server {
    listen 443 ssl;

    # TLS + CORS + HSTS（CORS 完全由 Nginx 处理）

    # Git HTTP Smart Protocol
    location ~ ^/.+\.git/(info/refs|git-upload-pack|git-receive-pack) {
        auth_request /git-auth;          # → FastAPI 鉴权
        proxy_pass http://git-cgi;
    }
    location /git-auth {
        internal;
        proxy_pass http://app/api/v1/git/auth;  # auth_request 子请求
    }

    # API
    location /api/ {
        proxy_pass http://app;
    }

    # WebSocket（多 worker 广播）
    location /ws {
        proxy_pass http://app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 静态文件（前端构建产物）
    location / {
        root /var/www/perseus-web;
        try_files $uri $uri/ /index.html;
    }
}
```

### 4.2 开发

位置：`docker/nginx/perseus_dev_proxy.conf` —— 反向代理到开发容器（FastAPI + git-cgi + 前端 dev server）。

### 4.3 Docker Write ACL

位置：`docker/docker-write-proxy/` —— 用于限制外部 runner 的 Git 写操作（Lua 校验 ACL）。

---

## 五、Gunicorn 配置

`core/gunicorn.conf.py` + `core/gunicorn_worker.py`

```python
workers = 4
worker_class = "gunicorn_worker.PerseusUvicornWorker"  # uvloop + ASGI
worker_connections = 1000
backlog = 2048
timeout = 30
keepalive = 2
max_requests = 10000          # 防内存泄漏（周期重启）
max_requests_jitter = 1000
enable_reuse_port = True      # Linux 多核优化（SO_REUSEPORT）
```

`PerseusUvicornWorker`：uvloop 事件循环 + ASGI 协议 + Gunicorn 信号处理。

---

## 六、数据库管理

### 6.1 迁移

```bash
# 自动模式（开发）
python app.py            # 启动时自动 alembic upgrade head

# 手动（生产 / CLI 工具）
alembic upgrade head
alembic current
alembic revision -m "add_xxx"
alembic downgrade -1

# 程序化入口
python scripts/init_db.py              # 迁移 + 管理员引导
python scripts/generate_env.py          # 环境变量模板
python scripts/reset_admin.py           # 重置 admin 密码
python scripts/db_migrate.py            # 迁移查询
```

### 6.2 SQLite 测试优化

WAL 模式 + NORMAL 同步 + MEMORY 临时表 + 大缓存：

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
PRAGMA temp_store=MEMORY;
```

### 6.3 PostgreSQL 连接池

```yaml
pool_size: 20
max_overflow: 40
pool_timeout: 10s
pool_recycle: 1800s   # 30min 回收（防负载均衡器 drop）
pool_pre_ping: true
```

---

## 七、健康检查

### 7.1 端点

| 端点 | 说明 |
|------|------|
| `GET /` | 欢迎页（含版本信息） |
| `GET /health` | 健康检查（DB connect OK → 200） |
| `GET /api/app/status` | 完整应用状态（worker 数 / 版本 / 运行时长） |
| `GET /metrics` | Prometheus 指标 |

### 7.2 Docker HEALTHCHECK

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/health || exit 1
```

---

## 八、测试

### 8.1 运行

```bash
# 全量
pytest tests/

# 按模块
pytest tests/test_auth_controller.py
pytest tests/ -k "pull_request"

# 带 coverage
pytest --cov=services --cov=controller --cov-report=html

# 异步自动模式
pytest-asyncio auto（pyproject.toml 已配置）
```

### 8.2 测试夹具（`tests/conftest.py`）

```python
@pytest.fixture(scope="session")
def db_url(): ...           # 测试容器 SQLite URL

@pytest.fixture(scope="session")
def async_engine(db_url): ... # 异步引擎

@pytest.fixture
def db_session(...): ...     # 每次测试独立 session + transaction rollback

@pytest.fixture
def admin_user(...): ...     # admin@example.com 种子用户

@pytest.fixture
def client(...): ...         # httpx AsyncClient（ASGI transport）
```

### 8.3 测试统计

80+ 测试文件，覆盖：
- 按模块（每个 service / controller 一个或多个测试文件）
- 异步测试（`*_async.py`）
- WS 处理器测试（`test_chat_ws_handlers.py`）
- API 契约测试（`api/test_api_contract.py`）
- 集成（smoke_test.py）
- 压力测试（stress_test.py）
- 安全审计（test_security_audit.py）
- 回归（test_bug_regression.py）

### 8.4 安全与验证脚本

```bash
python scripts/security_audit.py         # 安全审计
python scripts/verify_api_contract.py    # API 契约检查
python scripts/smoke_test.py             # 冒烟测试
python scripts/smoke_collab.py           # 协作冒烟
```

---

## 九、监控

### 9.1 Prometheus

- 端点：`/metrics`（Prometheus 中间件）
- 配置：`docker/prometheus/prometheus.yml`（抓取 `app:8000/metrics`，15s 间隔）
- 告警：`docker/prometheus/alerts.yml`（500 rate / 实例存活）

### 9.2 Grafana

- 数据源：`docker/grafana/provisioning/datasources/datasource.yml`（Prometheus）
- Dashboard：Admin 控制台内嵌（非必需独立 Grafana）

### 9.3 Admin 控制台 `/api/app/*`

功能：

| 能力 | 后端模块 |
|------|---------|
| 应用状态 / 版本 / 运行时长 | `app_service` |
| 重启触发 | `core.lifespan.trigger_graceful_shutdown` |
| 配置热加载 | `config_service` |
| 日志查看 | `app_service.get_logs` |
| Prometheus 时序 | `prometheus_metrics` |
| 请求统计时序 | `metrics_service` |
| 进程指标（RSS / CPU） | `process_metrics` |
| Worker 注册表 | `worker_registry` |
| Redis 管理 | `redis_admin_service` |
| 健康 / Ready / Config schema | `database_manager` |
| 组件状态 | `monitoring_service` |

### 9.4 Sentry

- 通过 `PERSEUS_SENTRY_DSN` 启用
- 未设置时 Sentry SDK 完全不初始化（零开销）
- FastAPI 集成：`sentry-sdk[fastapi]` + ASGI middleware（最外层包裹）

---

## 十、备份与恢复

### 10.1 数据库

```bash
pg_dump -h host -U perseus perseus > backup.sql
psql -h host -U perseus perseus < backup.sql
```

### 10.2 仓库（裸仓）

```bash
tar czf repos-backup.tar.gz ./repositories/
```

### 10.3 LFS 文件

```bash
tar czf lfs-backup.tar.gz /data/lfs/
```

---

## 十一、常见问题

| 问题 | 排查 |
|------|------|
| 应用启动报 `PERSEUS_SECURITY_SECRET_KEY 未设置` | 设置环境变量 |
| 数据库就绪校验失败（生产模式） | 先执行一次 `docker compose --profile init run init` |
| SQLite 并发写 lock | 生产用 PostgreSQL；测试 WAL 模式已缓解 |
| Redis 连接失败（启动慢） | 非阻塞，自动退化为进程内广播 |
| WS 连接数为 0 | Admin `/api/app/status` 查看 worker 心跳；Redis 注册表 |
| Prometheus metrics 404 | 检查是否启了 Prometheus 中间件（默认都启） |
| Worker 频繁重启 | 看 `max_requests` 触发的周期重启（默认 10000，正常） |
| `/{owner}/{repo}` 路由吞了子路径 | Controller 注册顺序（repository 必须最后） |

---

## 全文档索引

| 章节 | 链接 |
|------|------|
| 📐 总览与架构 | [01-overview.md](01-overview.md) |
| ⚙️ 核心基础设施 | [02-core.md](02-core.md) |
| 🗄️ 数据模型层 | [03-models.md](03-models.md) |
| 🔌 服务层 | [04-services.md](04-services.md) |
| 🛣️ 控制器与 API 路由 | [05-controllers.md](05-controllers.md) |
| 📡 WebSocket 子系统 | [06-websocket.md](06-websocket.md) |
| 🛡️ 中间件与工具库 | [07-middleware-utils.md](07-middleware-utils.md) |
| 🧱 协同网关与客户端 | [08-collab-client.md](08-collab-client.md) |
| 🚀 部署与运行 | [09-deployment.md](09-deployment.md) |
