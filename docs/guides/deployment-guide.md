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

### 4.1 一键安装（推荐）

```bash
# 交互式安装：启动后 5 秒内按 Enter 进入自定义配置，否则自动使用默认部署
bash scripts/install.sh

# 默认部署（非交互，使用 .env 默认值；等价 5 秒无输入）
bash scripts/install.sh -d

# 其他常用选项
bash scripts/install.sh --tag v0.1.0          # 指定镜像 tag
bash scripts/install.sh --with-monitoring     # 部署后启用监控栈
bash scripts/install.sh --no-cli              # 不安装全局 perseus 命令
bash scripts/install.sh --no-build            # 复用本机已有镜像
```

交互式配置项（直接回车取方括号默认值）：

| 配置项 | 默认值 | 写入 |
|--------|--------|------|
| 网关对外端口 | 8000 | `PERSEUS_GATEWAY_PORT` |
| 管理员用户名 | admin | `PERSEUS_ADMIN_USERNAME` |
| 管理员邮箱 | admin@perseus.local | `PERSEUS_ADMIN_EMAIL` |
| 镜像 tag | latest | `PERSEUS_IMAGE_TAG` |
| 启用监控栈 | 否 | 部署后拉起 `docker-compose.monitoring.yml` |
| 安装全局 `perseus` 命令 | 是 | 软链到 `/usr/local/bin/perseus`（无权限则 `~/.local/bin`） |

`install.sh` 内部状态机（失败即中断）：

```
preflight → 交互判定 → .env 引导(随机密钥) → 镜像准备 → PostgreSQL/Redis 就绪
→ 一次性 init(Alembic 迁移+管理员引导) → 业务层启动 → 网关健康
→（可选）监控栈 →（可选）全局命令 → 打印凭据
```

安装完成后终端会打印一次管理员账号与密码，请妥善保存。
部署后推荐统一使用 `perseus` 命令运维（见第 6 节）。

### 4.2 分步部署（等价手工流程）

```bash
# 1. 生成环境变量（生产模式：重新生成全部密钥）
python3 scripts/generate_env.py --prod --show

# 2. 启动基础设施层（PostgreSQL / Redis）
docker compose up -d postgres redis

# 3. 一次性数据库初始化任务（Alembic 迁移 + 管理员引导，幂等）
docker compose --profile init run --rm init

# 4. 启动业务层
docker compose up -d
```

服务清单（`docker-compose.base.yml` 基础设施层 + `docker-compose.yml` 业务层）：

| 服务 | 端口 | 层 | 说明 |
|------|------|----|------|
| postgres | 内网 | 基础设施 | PostgreSQL 16，数据卷 `postgres-data` |
| redis | 内网 | 基础设施 | Redis 7，LRU 上限 256MB |
| app | 127.0.0.1:8001 | 业务 | FastAPI 主服务，健康检查 `/health` |
| collab | 内网 | 业务 | 协作 Yjs/Hocuspocus 网关 |
| git-cgi | 127.0.0.1:9000 | 业务 | Git HTTP Smart Protocol |
| gateway | 8000 | 业务 | OpenResty 统一入口 |
| sshd | 127.0.0.1:2222 | 业务 | Git over SSH（可选） |
| init | 一次性 profile | 业务 | 数据库初始化任务（迁移 + 管理员引导） |

版本控制：`PERSEUS_IMAGE_TAG`（默认 `latest`）贯穿全部业务镜像；推送私有仓库时设置
`PERSEUS_IMAGE_PREFIX=registry.example.com/perseus`，`install.sh`/`mgt.sh` 将改用
`docker compose pull`。

> **初始化与运行解耦**：schema 迁移/管理员引导由一次性 `init` 任务负责，
> `app` 启动时仅做只读就绪校验（`PERSEUS_INIT_DATABASE=false`），schema 未就绪会拒绝启动
> 并通过健康检查暴露，网关在其他服务健康前不对外服务。

### 4.3 监控与告警（F-053 / F-057）

```bash
# 监控栈（Prometheus v3 + Grafana 11）独立编排
docker compose -f docker-compose.monitoring.yml up -d
# 默认加入生产网络 perseus-network；面向开发 compose 时设置
# PERSEUS_NETWORK_NAME=perseus-dev-network
```

- 指标端点：应用 `/metrics`（Prometheus 抓取）。
- Grafana 登录密码由 `.env` 的 `GRAFANA_ADMIN_PASSWORD` 指定（`generate_env.py` 自动生成）。
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

### 6.1 统一命令 `perseus`（推荐）

安装时自动软链为全局命令（`/usr/local/bin/perseus`，无权限回退 `~/.local/bin/perseus`），
也可直接调用 `bash scripts/perseus.sh`：

```bash
perseus update                            # 升级（自动备份 → 构建 → 迁移 → 重启）
perseus doctor                            # 环境体检
perseus uninstall                         # 彻底卸载（删除数据卷，二次确认）

perseus start | stop | restart            # 生命周期
perseus status                            # 容器状态与健康
perseus logs app                          # 跟踪日志
perseus init [--check-only]               # 数据库迁移 / 只读就绪校验
perseus backup [--with-data]              # 备份数据库+配置
perseus restore <文件> [--with-data]      # 恢复（破坏性，需确认）
perseus rollback                          # 回滚到最近一次备份
perseus reset-admin '新密码'              # 重设管理员密码
perseus install                           # 透传 install.sh（安装/升级）
perseus help                              # 帮助
```

> 未安装全局命令时可用 `perseus install` 之外的等价形式：
> `sudo ln -sf "$PWD/scripts/perseus.sh" /usr/local/bin/perseus`

### 6.2 底层入口 `scripts/mgt.sh`

统一入口 `scripts/mgt.sh`（`perseus` 命令即对其封装）：

```bash
bash scripts/mgt.sh start                 # 启动全部服务（schema 缺失时自动初始化）
bash scripts/mgt.sh stop                  # 停止（保留数据卷）
bash scripts/mgt.sh status                # 容器状态与健康
bash scripts/mgt.sh logs app              # 跟踪日志
bash scripts/mgt.sh doctor                # 环境体检（依赖/配置/schema/磁盘）

bash scripts/mgt.sh init                  # 手动执行迁移+管理员引导（幂等）
bash scripts/mgt.sh init --check-only     # 只读校验 schema 是否就绪

# 备份：数据库 + config.toml + .env 快照（--with-data 追加 Git 仓库数据卷）
bash scripts/mgt.sh backup                # backups/perseus-backup-<时间戳>.tar.gz
bash scripts/mgt.sh backup --with-data /mnt/nfs
# 恢复（破坏性，需确认；默认保留当前 .env 凭据，--restore-env 才恢复密钥快照）
bash scripts/mgt.sh restore backups/perseus-backup-20260915-120000.tar.gz --with-data

# 升级：自动备份 → 构建/拉取 → 增量迁移 → 重启；失败可用 rollback 回滚
bash scripts/mgt.sh upgrade --tag v0.2.0
bash scripts/mgt.sh rollback              # 恢复最近一次备份并重启

bash scripts/mgt.sh reset-admin '新密码'   # 重设管理员密码

bash scripts/mgt.sh uninstall             # 彻底卸载（删除数据卷，二次确认）
```

底层命令（不依赖配套脚本时）：

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
```

> `init` 任务执行 Alembic 迁移：已有 `alembic_version` 则增量升级；
> 历史库（create_all 时代、无版本表但有业务表）自动 `stamp` 认领；
> 全新库全量建表。schema 版本可在 `GET /api/app/status` 的 `schema_state` 字段查看。

## 7. 常见问题

- **`chown: changing ownership of '/app/config.toml': Read-only file system`**
  测试 profile 的 config.toml 为只读挂载，属预期现象；改用开发容器执行测试。
- **514 端口冲突**：开发与生产同时运行时网关端口（8000）冲突，先 `down` 其一。
- **Sentry 未生效**：检查是否配置了 `PERSEUS_SENTRY_DSN`；未配置时接入层自动跳过。
- **初始化管理员密码遗忘**：`bash scripts/mgt.sh reset-admin '新密码'` 直接重设；
  或重建容器时通过 `PERSEUS_ADMIN_PASSWORD` 重新指定（仅首启无管理员时生效）。