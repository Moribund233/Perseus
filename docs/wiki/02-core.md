# 02 · 核心基础设施（core）

> 核心基础设施层：配置、初始化、生命周期、异常体系。所有业务模块的地基。

---

## 目录

```
core/
├── __init__.py
├── config.py           # Pydantic Settings + TOML + 环境变量合并 + 校验
├── constants.py        # 角色优先级 / 有效角色列表
├── exception.py        # 20+ 自定义异常类层次结构
├── i18n.py             # 错误消息国际化（Accept-Language → 消息）
├── init.py             # AppInitializer 分层初始化管线
├── lifespan.py         # FastAPI lifespan + 启动/关闭流程
├── sentry.py           # Sentry SDK 初始化 + 中间件
├── gunicorn.conf.py   # Gunicorn 生产配置
└── gunicorn_worker.py  # PerseusUvicornWorker（uvloop + ASGI）
```

---

## 1. 配置管理 `core/config.py`

### 1.1 架构

```
配置优先级（从低到高）：
  ① Pydantic Field 默认值
  ② config.toml 文件值（仅当没有对应环境变量时生效）
  ③ 环境变量（最高优先级）
```

### 1.2 关键类一览

| 类 | 环境变量前缀 | 说明 |
|----|-------------|------|
| `ServerSettings` | 无 | host / port / reload / log_level |
| `GunicornSettings` | 无 | workers / timeout / keepalive / max_requests … |
| `AppSettings` | `PERSEUS_APP_` | title / description / version / debug |
| `CORSSettings` | 无 | **声明型**，实际由 Nginx 处理 |
| `StorageSettings` | `PERSEUS_STORAGE_` | repo_root / max_repo_size / max_file_size |
| `SecuritySettings` | `PERSEUS_SECURITY_` | secret_key（**必需**）/ access_token_expire_minutes / refresh_token_expire_days / algorithm |
| `RedisSettings` | `PERSEUS_REDIS_` | url / namespace / reconnect_cooldown（可选，为空不启用） |
| `LoggingSettings` | 无 | audit_log_path / audit_log_max_size / audit_log_enabled |
| `DatabaseSettings` | `PERSEUS_DATABASE_` | url / pool_size / pg_ssl_mode / sqlite WAL |
| `ConcurrencySettings` | （派生） | 由压力测试模式自动生成 |
| `LFSSettings` | `PERSEUS_LFS_` | enabled / storage_backend / s3_* |
| `SearchSettings` | `PERSEUS_SEARCH_` | enabled / max_results / max_file_size |
| `SentrySettings` | `PERSEUS_SENTRY_` | dsn（空不启用）/ traces_sample_rate |
| `MetricsSettings` | `PERSEUS_METRICS_` | history_minutes / sample_interval_seconds / max_points |
| `OAuthSettings` | `PERSEUS_OAUTH_` | github_* / gitlab_* |
| **`Config`** | — | 聚合所有子模型的根类 |
| **`ConfigManager`** | — | 单例，负责 TOML + env 合并加载 |

### 1.3 关键函数

```python
def get_config(config_path: str = "config.toml") -> Config
    # 便捷函数，内部委托给 ConfigManager 单例

def reset_module_config_manager() -> None
    # 测试时重置单例

def validate_config(config=None, config_path="config.toml") -> ConfigValidationResult
    # 完整配置完整性校验（F-009），内部调用 5 个分域校验器
    # 返回 { errors: [...], warnings: [...] }
```

### 1.4 `DatabaseSettings` 特殊项

- `url` 通过 `field_validator` 优先读 **`DATABASE_URL`**（不是 `PERSEUS_DATABASE_URL`）
- `is_stress_test` 通过 **`PERSEUS_STRESS_TEST`** 读取
- 提供 `db_type` / `is_sqlite` / `is_postgresql` 属性
- 提供 `_mask_url(url)` 掩码工具（隐藏密码）

### 1.5 TOML 合并逻辑

`ConfigManager._load_config()` 的合并策略：

```python
for section, section_data in toml_config.items():
    for key, value in section_data.items():
        env_name = f"{env_prefix}{key.upper()}"  # 如 PERSEUS_APP_DEBUG
        extra_env = self._get_extra_env_checks(section)  # 特殊项如 DATABASE_URL
        if os.environ.get(env_name) is not None: continue
        if extra_env[key] 且 os.environ.get(extra_env[key]) is not None: continue
        toml_updates[key] = value
    sub_model.model_copy(update=toml_updates)  # 不可变更新
```

### 1.6 必需环境变量（启动硬检查）

| 变量 | 用途 | 模式 |
|------|------|------|
| `PERSEUS_SECURITY_SECRET_KEY` | JWT 签名密钥 | **必需** |
| `DATABASE_URL` | 数据库连接 | **必需** |
| `PERSEUS_APP_DEBUG` | true/false | 可选（默认 false） |
| `PERSEUS_INIT_DATABASE` | true/false | 可选（默认 true） |
| `PERSEUS_STRESS_TEST` | true/false | 可选 |
| `PERSEUS_REDIS_URL` / `REDIS_URL` | Redis | 可选 |
| `PERSEUS_SENTRY_DSN` | Sentry | 可选（空不启用） |

---

## 2. 应用初始化 `core/init.py`

### 2.1 初始化管线

`AppInitializer.initialize()` 严格按如下顺序执行，任何阶段失败立即中断：

| 阶段 | 内容 | 失败行为 |
|------|------|----------|
| 0 | **加载 `.env`**（延迟，pytest 进程跳过） | — |
| 1 | **检查必需环境变量** | 打印错误报告并返回 False |
| 2 | **延迟导入依赖**（core.config / utils.logging） | 返回 False |
| 3 | **加载 config.toml** | 返回 False（提示从模板复制） |
| 4 | **validate_config** 完整性校验 | 返回 False（errors 存在） |
| 5 | **初始化日志系统** | 返回 False |
| 6 | **检查 SECRET_KEY** | 返回 False |
| 7 | **数据库初始化**（pytest 进程跳过） | 返回 False |
| 8 | **创建仓库根目录** | 返回 False |

### 2.2 数据库初始化双模式

由 `PERSEUS_INIT_DATABASE` 控制：

| 模式 | 触发条件 | 行为 |
|------|---------|------|
| 自动模式（开发） | `true`（默认） | `utils.init_database.init_database()` — Alembic 迁移 + 管理员引导 |
| 就绪校验（生产） | `false` | 只读 `utils.init_database.verify_database_ready()` — schema 未就绪拒绝启动 |

多容器生产环境中，schema 迁移由独立的 `init` 任务完成（`docker compose --profile init run init`）。

### 2.3 关键类 / 函数

```python
class AppInitializer:
    def initialize(self, init_db=True) -> bool   # 完整管线
    def reset_config(self) -> None                # 从 config.example.toml 重置
    def update_config(self, new_config: dict)     # 更新并写回 TOML

class EnvVarChecker:
    @staticmethod
    def check_layer(layer: InitLayer) -> (bool, List[str])

def init_app(init_db=True) -> bool               # 便捷入口
def get_required_env_vars() -> List[str]
def print_env_var_guide() -> None
```

### 2.4 防意外导入

模块顶部的延迟导入模式值得注意：
- `app.py` 中 `logger` / `config` 等延迟到 `create_app()` 内部导入
- `init.py` 中 `.env` 加载延迟到 `AppInitializer.initialize()`，pytest 进程完全跳过
- `_in_pytest()` 通过检查 `sys.modules` 和 `PYTEST_CURRENT_TEST` 环境变量判断

---

## 3. 生命周期管理 `core/lifespan.py`

### 3.1 FastAPI lifespan

```python
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    manager = get_lifecycle_manager()
    await manager.startup()
    yield {"lifecycle_manager": manager}
    await manager.shutdown()
```

### 3.2 `AppLifecycleManager.startup()`

| 步骤 | 内容 | 致命 |
|------|------|------|
| 1 | `get_async_engine()` + `SELECT 1` 验证 | ✅ 是 |
| 2 | WebSocket heartbeat_checker 协程 | ❌ 否 |
| 3 | `realtime_bus.start()`（Redis 可用则启用跨 worker 广播） | ❌ 否 |
| 4 | worker 心跳（`worker_registry.heartbeat`，20s 循环） | ❌ 否 |
| 5 | 进程指标采样（内存/CPU） | ❌ 否 |

### 3.3 `AppLifecycleManager.shutdown()`

严格逆序：
1. 取消 worker 心跳
2. 停止进程指标采样
3. 停止 realtime_bus
4. 广播 `{"type":"system","event":"shutdown","message":"..."}` 到所有 WebSocket，等 0.5s，然后 `code=1001` 逐个关闭
5. `close_async_engine()` dispose

### 3.4 其他导出

```python
def get_lifecycle_manager() -> AppLifecycleManager
def reset_lifecycle_manager() -> None             # 测试用
def trigger_graceful_shutdown(reason="manual")    # 外部触发关闭（SIGTERM 自殺）
def is_shutdown_requested() -> bool
```

---

## 4. 异常体系 `core/exception.py`

### 4.1 层次结构

```
HTTPException (FastAPI)
    └── BaseException
            ├── ValidationException           (400)
            ├── AuthenticationException       (401, WWW-Authenticate: Bearer)
            ├── AuthorizationException        (403)
            ├── NotFoundException             (404)
            ├── RepositoryNotFoundException  (404)
            ├── PathNotFoundException        (404)
            ├── InvalidPathException         (400)
            ├── ConflictException             (409)
            ├── RepositoryBrowserException    (500)
            ├── DatabaseException             (500)
            ├── FileException                 (500)
            └── AppServiceException           (500, 可自定义 status_code)
                    └── ConfigValidationException (400)
```

### 4.2 `error_code` 国际化钩子

每个异常支持可选 `error_code: str | None`（稳定错误码，如 `"room_not_found"`）。
配合 `core/i18n.py` 可实现按 `Accept-Language` 返回国际化错误消息。未传时沿用 `detail`，完全向后兼容。

### 4.3 全局异常处理器注册

```python
# utils/exception_handler.py
def setup_exception_handlers(app: FastAPI) -> None:
    # 注册 BaseException / HTTPException / 通用 Exception 处理器
```

---

## 5. 常量 `core/constants.py`

```python
ROLE_PRIORITY = {
    "owner":      4,
    "admin":      3,
    "developer":  2,
    "readonly":   1,
}
VALID_ROLES = list(ROLE_PRIORITY.keys())
```

使用位置：`utils/permission_utils`（比较权限等级）。

---

## 6. Sentry `core/sentry.py`

```python
def init_sentry(config: Config) -> None
    # DSN 为空或 production 但未配置 → 零开销跳过
    # 配置 traces_sample_rate / environment / release

def sentry_middleware(app: FastAPI) -> FastAPI
    # 返回 Sentry ASGI 中间件包装后的 app
```

---

## 7. Gunicorn 配置

[ gunicorn.conf.py ](file:///d:/Projects/Python/perseus/core/gunicorn.conf.py) 和 [ gunicorn_worker.py ](file:///d:/Projects/Python/perseus/core/gunicorn_worker.py) 提供生产级 Gunicorn：

- Worker 类 = `PerseusUvicornWorker`（uvloop + ASGI）
- 默认 4 workers，max_requests=10000 + jitter=1000 防内存泄漏
- 支持 `SO_REUSEPORT`（Linux 多核优化）

---

## 下一章

👉 [03 · 数据模型层（models）](03-models.md)
