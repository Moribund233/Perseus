# Perseus 部署文档

> **适用版本**: 0.1.0
> **更新日期**: 2026-09-15

本文档说明 Perseus 在开发与生产环境下的部署步骤、系统要求与运维要点。

## 1. 系统要求

| 组件 | 版本要求 | 说明 |
|------|---------|------|
| Docker | 20.10+（含 Compose V2） | 生产部署要求 Docker Compose v2 |
| Python | 3.12.x | 仅后端独立运行需要 |
| Node.js | 20+（pnpm 10+） | 仅前端构建需要（可选） |
| 内存 | 后端 2G / 数据库 1G | 生产推荐 8G+ |

## 2. 部署架构

```
                 ┌─────────────────────────────────┐
                 │        Nginx / OpenResty        │
                 │  TLS · CORS · WS 代理 · Git HTTP │  ← 唯一对外入口 (8000)
                 └───────────┬──────────┬──────────┘
                ┌────────────┘          └───────────┐
                ▼                                  ▼
        ┌────────────────┐                  ┌──────────────┐
        │  FastAPI 应用   │                  │    git-cgi   │  Git Smart Protocol
        │  (Uvicorn ×N)   │                  │ (git-http-   │
        │  + Sentry       │                  │  backend)    │
        └──────┬─────────┘                  └──────────────┘
               │
        ┌──────┼──────────────────────┐
        ▼      ▼                      ▼
   PostgreSQL   Redis           git/sshd (可选)
   (数据持久化)   (缓存/可选)
```

- **对外入口**：Nginx 仅暴露 8000 端口，统一处理 TLS、CORS 白名单、WebSocket 代理与 Git HTTP。
- **后端**：本机端口 8001（生产）或 8000（开发），不直接对外。
- **HTTPS 与 CORS 由 Nginx 收敛**，应用层不配置 CORS。

## 3. 开发环境部署

### 3.1 前置准备

```bash
# 1. 生成环境变量（生成 .env 与 JWT/协作密钥）
python scripts/generate_env.py        # 或 cp .env.example .env 后手动修改

#   .env 必须配置:
#   PERSEUS_SECURITY_SECRET_KEY   JWT 签名密钥（至少 32 字符）
#   PERSEUS_ADMIN_PASSWORD        初始管理员密码
#   PERSEUS_COLLAB_INTERNAL_SECRET 协作服务内部密钥
#   POSTGRES_PASSWORD             数据库密码（生产）
```

### 3.2 启动开发环境

```bash
docker compose -f docker-compose.dev.yml up -d
```

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 Vite | http://localhost:5173 | 由外部 Nginx 转发至此（可选） |
| API（直连） | http://localhost:8000 | `/docs` Swagger、`/redoc` Redoc |
| API（统一入口） | http://localhost:8080/api | 经 dev 网关 |
| Git HTTP | http://localhost:8080/{user}/{repo}.git | 经网关 |
| WebSocket | ws://localhost:8080/ws | 协作 / 通知 |

### 3.3 运行测试

```bash
docker compose -f docker-compose.dev.yml exec app sh -c "cd /app && python -m pytest"
# 指定用例:
docker compose -f docker-compose.dev.yml exec app sh -c "cd /app && python -m pytest tests/test_i18n.py -q"
```

> 注意：测试容器内置 `.env` 变量与 SQLite 库，`.venv` 直接运行通常会因缺少环境变量而失败。

## 4. 生产环境部署

### 4.1 配置生产环境变量

```bash
python scripts/generate_env.py --prod     # 生成高强度随机密钥
# 核对 .env：POSTGRES_PASSWORD / PERSEUS_SECURITY_SECRET_KEY /
#           PERSEUS_COLLAB_INTERNAL_SECRET / PERSEUS_APP_DEBUG=false
```

### 4.2 一键部署

```bash
docker compose up -d --build
```

服务清单（`docker-compose.yml`）：

| 服务 | 端口 | 说明 |
|------|------|------|
| postgres | 内网 | PostgreSQL 16，数据卷 `postgres-data` |
| redis | 内网 | Redis 7，LRU 上限 256MB |
| app | 127.0.0.1:8001 | FastAPI 主服务，健康检查 `/health` |
| collab | 内网 | 协作 Yjs/Hocuspocus 网关 |
| git-cgi | 127.0.0.1:9000 | Git HTTP Smart Protocol |
| gateway | 8000 | OpenResty 统一入口 |
| sshd | 127.0.0.1:2222 | Git over SSH（可选） |
| init | 一次性 | 数据库初始化任务（Alembic 迁移 + 管理员引导，profile: init） |

> **初始化与运行解耦**：schema 迁移/管理员引导由一次性 `init` 任务负责，
> `app` 启动时仅做只读就绪校验（`PERSEUS_INIT_DATABASE=false`）。

### 4.3 首次初始化

1. 先执行一次数据库初始化任务（幂等、可重复运行）：
   ```bash
   docker compose --profile init run --rm init
   ```
2. 再启动全部服务（跳过 `init` profile）：
   ```bash
   docker compose up -d --build
   ```
3. 等待网关健康：`docker compose ps` 全部 healthy。
4. 访问 http://localhost:8000/docs 验证 API 与 Swagger。
5. 初始化任务自动创建数据库 schema 与初始管理员账号
   （`PERSEUS_ADMIN_USERNAME` / `PERSEUS_ADMIN_PASSWORD`）。

> `init` 任务执行 Alembic 迁移：已有 `alembic_version` 则增量升级；
> 历史库（create_all 时代、无版本表但有业务表）自动 `stamp` 认领；
> 全新库全量建表。schema 版本可在 `GET /api/app/status` 的 `schema_state` 字段查看。

### 4.4 监控与告警（F-053 / F-057）

```bash
# 监控栈（Prometheus v3 + Grafana 11）独立编排
docker compose -f docker-compose.monitoring.yml up -d
```

- 指标端点：应用 `/metrics`（Prometheus 抓取）。
- 告警规则已内置（`docker/prometheus/alerts.yml`）：
  - `PerseusErrorRateHigh`：错误率 > 1% 持续 5 分钟。
  - `PerseusRequestLatencyHigh`：P95 > 2s 持续 10 分钟。
- 错误追踪：配置 `PERSEUS_SENTRY_DSN` 环境变量后，`SentryAsgiMiddleware`
  自动捕获未处理异常；未配置 DSN 时零开销跳过。

## 5. 配置参考

| 配置节 | 前缀 | 关键项 |
|--------|------|--------|
| `[database]` | `PERSEUS_DATABASE_` | url、pool_size、pool_recycle |
| `[security]` | `PERSEUS_SECURITY_` | secret_key、access_token_expire_minutes |
| `[sentry]` | `PERSEUS_SENTRY_` | dsn、traces_sample_rate、environment、release |
| `[app]` | `PERSEUS_APP_` | debug、title、version |
| `[storage]` | `PERSEUS_STORAGE_` | repo_root（仓库根目录） |
| `[cors]` | — | allow_origins（生产由 Nginx 白名单收敛） |

生产安全注意事项：
- 生产环境必须 `PERSEUS_APP_DEBUG=false`。
- JWT 密钥禁止使用默认值；通过 `PERSEUS_SECURITY_SECRET_KEY` 注入。
- CORS 通配符 `*` 仅限开发，生产以 Nginx `map` 校验 `Origin` 后透传。
- WebHook URL 创建时已启用 SSRF 防护（`utils/url_validation.py`），
  禁止指向内网/回环/保留地址。

## 6. 运维命令

```bash
# 查看日志
docker compose logs -f app
# 进入容器
docker compose exec app bash
# 数据库迁移/管理员引导（升级/重建镜像后执行，幂等）
docker compose --profile init run --rm init
# 只读校验 schema 是否就绪（不改动任何数据）
docker compose --profile init run --rm init --check-only
# 数据库备份（PostgreSQL）
docker compose exec postgres pg_dump -U perseus perseus > backup.sql
# 更新并重建
docker compose pull && docker compose up -d --build
git pull
docker compose restart
```

## 7. 常见问题

- **`chown: changing ownership of '/app/config.toml': Read-only file system`**
  测试 profile 的 config.toml 为只读挂载，属预期现象；改用开发容器执行测试。
- **514 端口冲突**：开发与生产同时运行时网关端口（8000）冲突，先 `down` 其一。
- **Sentry 未生效**：检查是否配置了 `PERSEUS_SENTRY_DSN`；未配置时接入层自动跳过。
- **初始化管理员密码遗忘**：重建容器时通过 `PERSEUS_ADMIN_PASSWORD` 重新指定，或登录数据库手工重置。