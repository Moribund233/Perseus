# 07 · 中间件与工具库（middleware + utils）

> HTTP 请求管线 + 19 个跨领域工具模块。

---

## 一、middleware/ —— 6 个中间件

### 注册顺序（`app.py`，最先添加 = 最外层）

```
请求进入 ──► ┌──────────────────────────────────────────────┐
             │ ConcurrencyMiddleware                        │ ① 并发限制
             │   ▼                                          │
             │ RequestTimeLoggerMiddleware                  │ ② 慢请求日志
             │   ▼                                          │
             │ SecurityHeadersMiddleware                    │ ③ 安全头
             │   ▼                                          │
             │ AuditLoggerMiddleware                        │ ④ 审计日志
             │   ▼                                          │
             │ RequestStatsMiddleware                       │ ⑤ 请求统计
             │   ▼                                          │
             │ PrometheusMetricsMiddleware                  │ ⑥ Prometheus
             │   ▼                                          │
             │ FastAPI handlers                             │
             └──────────────────────────────────────────────┘
响应返回 ◄─── (反方向)
```

### 1. `ConcurrencyMiddleware`（最外层保护）

- **作用**：限制并发请求数，超载返回 503
- **配置**：
  - `max_concurrent`（每 worker，默认 100，压力测试 200）
  - `global_max_concurrent`（跨 worker Redis 计数，0 = 关闭）
  - `max_wait_time`（等待秒数，默认 5）
- **实现**：AsyncIO `Semaphore` + 可选 Redis INCR/DECR
- **失败行为**：`HTTPException(503, "Service temporarily unavailable")`

### 2. `RequestTimeLoggerMiddleware`

- **作用**：记录慢请求日志（默认阈值 30s）
- **实现**：`time.monotonic()` 前后差，超阈值打 warning

### 3. `SecurityHeadersMiddleware`

- **作用**：添加安全响应头
- **典型响应头**：

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
X-XSS-Protection: 1; mode=block
Permissions-Policy: ...
Content-Security-Policy: default-src 'self' ...
```

- 生产（非 debug）额外加 `Strict-Transport-Security`（1 年）
- 移除服务器指纹（`Server` 头）

### 4. `AuditLoggerMiddleware`

- **作用**：全量请求审计日志
- **记录字段**：IP · 用户 · 路径 · 方法 · 状态码 · 耗时 · User-Agent · 请求体（脱敏）
- **存储**：`logs/audit.log`（10MB × 5 份轮转）
- **可选**：通过 WebSocket 实时广播到管理员控制台

### 5. `RequestStatsMiddleware`

- **作用**：内存中的请求统计（Admin 概览时序图数据源）
- **统计字段**：QPS · 成功率 · 平均延迟 · 500 数
- **采样**：按分钟桶存储，保留 `config.metrics.history_minutes`（默认 1440 = 24h）
- **排除路径**：`/health /docs /openapi.json /metrics`

### 6. `PrometheusMetricsMiddleware`

- **作用**：暴露 `/metrics` 端点
- **指标**：
  - `perseus_requests_total`（方法 × 路径 × 状态码）
  - `perseus_request_latency_seconds`（直方图）
  - `perseus_in_flight_requests`（Gauge）
  - `perseus_info`（版本信息 Gauge）
- **与 RequestStats 互补**：Prometheus 供外部 scrap；RequestStats 供 Admin 面板内时序

---

## 二、utils/ —— 19 个工具模块

| 文件 | 职责 | 关键导出 |
|------|------|---------|
| `logging.py` | 多文件日志 + WS 广播 | `init_logging()` · `get_logger(name)` |
| `git_utils.py` | pygit2 封装 + 仓库根目录 | `ensure_repository_root()` · 裸仓打开 · clone |
| `password_utils.py` | bcrypt 哈希 | `hash_password()` · `verify_password()` |
| `security_utils.py` | 敏感数据过滤 | 日志脱敏（password / token / secret） |
| `permission_utils.py` | 仓库成员权限检查 | 角色优先级比较 · 非成员 / 只读 拦截 |
| `response_builder.py` | 统一 JSON 响应 | `success(data, msg)` · `error(msg, code)` |
| `exception_handler.py` | 全局异常处理器 | `setup_exception_handlers(app)` |
| `email_utils.py` | SMTP 发送 | `send_email()`（aiosmtplib + Jinja2） |
| `db_utils.py` | 数据库辅助 | `exists()` · `paginate()` |
| `db_validation.py` | 数据库配置校验 | `validate_database_config()` |
| `init_database.py` | 数据库初始化 | `init_database()` · `verify_database_ready()` |
| `db_migrate.py` | Alembic 程序化入口 | `run_migrations()` · `get_head_revision()` |
| `config_utils.py` | 配置文件工具 | （config 热加载辅助） |
| `webhook_trigger.py` | WebHook HTTP 投递 | 重试 + 超时 + HMAC 签名包装 |
| `lfs_utils.py` | LFS 工具 | 锁 / OID / MIME |
| `realtime_bus.py` | Redis 跨 worker 广播 | `RealtimeBus` 单例 `bus` |
| `redis_client.py` | Redis 客户端 | `get_redis_client()` 单例 |
| `url_validation.py` | URL 校验 | 仓库 clone / webhook URL 合法性 |

---

## 三、关键工具详解

### 1. `utils/logging.py` —— 日志系统

```python
def init_logging(
    log_dir="logs",
    app_name="perseus",
    level="info",
    console_output=True,
    use_date_directory=True,    # logs/2026-09-21/app.log
    separate_error_log=True,    # error.log 单独
    websocket_output=True,      # WS 广播到 admin
) -> None

def get_logger(name: str) -> logging.Logger
```

特性：
- 每个 logger 都带 `websocket_output` handler（发 admin WS）
- `utils.security_utils` 提供敏感信息脱敏 filter（password / token / secret）
- 审计日志走独立 handler（按大小轮转）

### 2. `utils/git_utils.py` —— 仓库操作

```python
def ensure_repository_root() -> Path     # 创建 ./repositories 目录
def open_bare_repo(path: str) -> pygit2.Repository
def clone_bare(source: str, dest: str) -> None
def ...
```

所有仓库操作都在磁盘裸仓上进行（pygit2）。`repository_service` 用 `@ttl_cache(30)` 缓存打开的 Repository 对象减少磁盘 I/O。

### 3. `utils/realtime_bus.py` —— 跨 worker 广播

```python
class RealtimeBus:
    async def start() -> bool            # 连接 Redis 并订阅所有 channel 前缀
    async def stop() -> None
    async def publish(channel: str, message: dict) -> None
    def bind(manager: ConnectionManager) -> None

bus: RealtimeBus = RealtimeBus()        # 单例
```

Service 层调用统一：`await bus.publish("repo:<id>", {"type": "event", "event": "pr_opened", ...})`

### 4. `utils/exception_handler.py`

全局注册三层处理器：

1. `core.exception.BaseException` → 返回结构化 JSON（含 error_code + i18n 消息）
2. `HTTPException` → 默认 FastAPI 行为
3. 兜底 `Exception` → 500 + Sentry 上报 + 安全脱敏 detail

```python
def setup_exception_handlers(app: FastAPI) -> None
```

### 5. `utils/init_database.py` + `utils/db_migrate.py`

- `init_database()` —— Alembic upgrade head + 管理员引导（幂等，已存在 admin 跳过）
- `verify_database_ready()` —— 生产就绪校验（schema 版本对齐）
- `get_head_revision()` / `get_current_revision()`

### 6. `utils/email_utils.py`

- `send_email(to, subject, html, ...)` 基于 aiosmtplib
- 使用 Jinja2 模板渲染通知邮件（密码重置 / PR 更新等）

### 7. `utils/webhook_trigger.py`

WebHook 投递底层：
- httpx 异步（超时 10s）
- HMAC-SHA256 签名（`sha256(secret, payload)`）
- 指数退避重试（3 次，间隔 1s / 2s / 4s）
- 投递历史 + 状态追踪写库

---

## 四、安全工具

`utils/security_utils.py`

- 日志脱敏 filter（过滤 password / token / secret）
- 所有写入 audit.log 的字段自动经过 filter

`utils/password_utils.py`

```python
from passlib.context import CryptContext
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def hash_password(plain: str) -> str
def verify_password(plain: str, hashed: str) -> bool
```

---

## 下一章

👉 [08 · 协同网关与客户端（collab-gateway + client）](08-collab-client.md)
