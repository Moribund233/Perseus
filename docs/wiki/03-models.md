# 03 · 数据模型层（models）

> ORM 基类、UUID7 主键、同步/异步双引擎、25+ 表一览。

---

## 目录

```
models/
├── __init__.py           # declarative_base + init_engine() + 所有模型导入
├── base.py               # TimestampMixin（UUID7 PK + created_at/updated_at）
├── uuid7.py              # RFC 9562 时间有序 UUID 生成器
├── async_db.py           # 异步引擎 + AsyncSession 工厂 + FastAPI 依赖
└── <business>.py         # 按业务域组织的 25 个模型文件
```

---

## 1. ORM 基类

### 1.1 `Base` 声明

```python
# models/__init__.py
Base: Any = declarative_base()
```

所有模型均继承自 `Base`（经 `TimestampMixin`）。

### 1.2 `TimestampMixin`

```python
# models/base.py
class TimestampMixin(Base):
    __abstract__ = True

    id = mapped_column(
        SAUuid(as_uuid=True),
        primary_key=True,
        index=True,
        default=generate_uuid7,   # UUID7 PK
    )
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True),
                               server_default=func.now(),
                               onupdate=func.now())
```

### 1.3 UUID7 生成器 `models/uuid7.py`

> RFC 9562 时间有序 UUID，避免传统 UUID 的 B-tree 索引碎片。

特性：
- 前 48 位 = Unix 毫秒时间戳（`time.time_ns() // 1_000_000`）
- 版本位 = `0111`（0x7）
- 变体位 = `10`
- 其余 74 位 = 随机（`os.urandom` + 首次模块加载缓存 2 bits 固定）

---

## 2. 数据库引擎（双引擎架构）

### 2.1 同步引擎 `models/__init__.py`

| 函数 | 说明 |
|------|------|
| `init_engine()` | 启动时创建，根据 `config.database.db_type` 选择 SQLite / PostgreSQL |
| `get_engine() -> Engine` | 获取已初始化的同步引擎 |
| `SessionLocal` | `sessionmaker(autocommit=False, autoflush=False, bind=_engine)` |

PostgreSQL 同步 URL 自动加 `+psycopg2` 驱动：`postgresql://user:pass@host/db` → `postgresql+psycopg2://user:pass@host/db`。

### 2.2 异步引擎 `models/async_db.py`

| 函数 | 说明 |
|------|------|
| `_get_async_url(sync_url)` | 自动把同步 URL 转异步（`sqlite+aiosqlite://` / `postgresql+asyncpg://`） |
| `get_async_engine() -> AsyncEngine` | 单例，内部调用 `_create_async_engine_with_config()` |
| `get_async_session_maker() -> async_sessionmaker` | `expire_on_commit=False, autocommit=False, autoflush=False` |
| `get_async_db() -> AsyncGenerator` | **FastAPI 依赖注入**，yield 一个 AsyncSession（自动 commit + rollback + close） |
| `get_async_db_context()` | 非 FastAPI 场景下的 `async with` 上下文管理器版本 |
| `close_async_engine()` | 关闭并清空全局单例（应用关闭时调用） |

### 2.3 引擎差异

| 引擎 | SQLite | PostgreSQL |
|------|--------|------------|
| 同步驱动 | 内置 | psycopg2 |
| 异步驱动 | aiosqlite | asyncpg |
| 同步 Pool | QueuePool | QueuePool |
| 异步 Pool | **NullPool**（SQLite 不支持连接池并发） | QueuePool |
| 连接池大小 | — | 20（生产）/ 30（压力测试） |
| `pool_pre_ping` | ❌ | ✅ |
| SQLite PRAGMA | WAL + NORMAL + MEMORY + 大缓存 | — |

---

## 3. 配置与引擎生命周期

### 3.1 创建链路

```
config.database.url
        │
        ├─ (DatabaseSettings.field_validator) 优先读 DATABASE_URL
        │
        └─ models/__init__.init_engine()
                │
                ├─ SQLite → _create_sqlite_engine() + QueuePool
                │             + @event "connect" PRAGMA WAL 等
                │
                └─ PostgreSQL → _create_postgresql_engine()
                               + SSL + connect_timeout
                               + QueuePool + pool_pre_ping

        models/async_db.get_async_engine()
                │
                └─ _create_async_engine_with_config()
                        ├─ SQLite → NullPool
                        └─ PostgreSQL → QueuePool + pool_pre_ping
```

### 3.2 连接池配置解析

```python
def _resolve_pool_config(db_config) -> dict:
    # 根据 is_stress_test 切换常规参数 / 压力测试参数
    # 返回 { pool_size, max_overflow, pool_timeout, pool_recycle, echo }
```

---

## 4. 全量表一览

### 4.1 核心实体

| 模型 | 表名 | 说明 |
|------|------|------|
| `User` | `users` | 用户名 / 邮箱 / 密码（bcrypt）/ is_admin / avatar_url / full_name |
| `SSHKey` | `ssh_keys` | user_id 外键 + 指纹 + 公钥 |
| `Repository` | `repositories` | name / path（唯一）/ owner_id / is_public / default_branch / forked_from_id / star_count / fork_count / watch_count / ci_secret |
| `RepositoryMember` | `repository_members` | repo_id + user_id + role（owner/admin/developer/readonly） |
| `Stargazer` | `stargazers` | repo_id + user_id（Star 关联） |
| `Watcher` | `watchers` | repo_id + user_id（Watch 关联） |

### 4.2 Git 域

| 模型 | 表名 | 说明 |
|------|------|------|
| `Branch` | `branches` | repo_id + name + commit_hash |
| `Commit` | `commits` | repo_id + hash + author_email + message + timestamp + parent_hash |

### 4.3 PR / Issue 域

| 模型 | 表名 | 说明 |
|------|------|------|
| `PullRequest` | `pull_requests` | repo_id + pr_number（repo 内自增）+ source_branch + target_branch + status(open/merged/closed) + is_draft + merged_by + merged_commit_hash |
| `PRComment` | `pr_comments` | pr_id + author_id + content + 可选 file_path / line_number / commit_hash / parent_id（支持回复） |
| `PRReview` | `pr_reviews` | pr_id + user_id + state（APPROVED/CHANGES_REQUESTED/COMMENTED） |
| `PRActivity` | `pr_activities` | PR 时间线活动（open/close/merge/reopen 等） |
| `PRLabel` | `pr_labels` + `pr_label_association` | PR 标签 |
| `Issue` | `issues` | repo_id + issue_number + title + description + status(open/closed) + priority(low/medium/high/critical) + assignee_id |
| `Label` | `labels` | repo_id + name + color + description |
| `IssueComment` | `issue_comments` | issue_id + author_id + content |
| `RepoLabel` | `repo_labels` + `repo_label_association` | 仓库级标签 |

### 4.4 Release / WebHook / Build

| 模型 | 表名 | 说明 |
|------|------|------|
| `Release` | `releases` | repo_id + tag + title + description + is_draft + is_prerelease |
| `ReleaseAsset` | `release_assets` | release_id + filename + size + content_type + download_url |
| `WebHook` | `webhooks` | repo_id + url + secret（HMAC）+ events（JSON 数组）+ is_active |
| `WebHookDelivery` | `webhook_deliveries` | webhook_id + status_code + response_body + request_headers（投递历史 + 重试） |
| `BuildStatus` | `build_statuses` | repo_id + sha + state + commit + started_at + finished_at |
| `BuildLogEntry` | `build_log_entries` | build_id + line + stream（stdout/stderr）+ order（日志流分片） |

### 4.5 实时协作域

| 模型 | 表名 | 说明 |
|------|------|------|
| `RealtimeRoom` | `realtime_rooms` | repo_id + name + type（repo/dm/group） |
| `RoomMember` | `room_members` | room_id + user_id + is_muted |
| `DirectMessage` | `direct_messages` | sender_id + receiver_id + content |
| `ChatMessage` | `chat_messages` | room_id / dm_id + author_id + content + type(text/system) |
| `FileComment` | `file_comments` | repo_id + file_path + line_number + author_id + content + commit_hash（行内讨论） |

### 4.6 认证 / 审计 / 配置扩展

| 模型 | 表名 | 说明 |
|------|------|------|
| `UserOAuthAccount` | `user_oauth_accounts` | user_id + provider（github/gitlab）+ provider_user_id + access_token（加密） |
| `RevokedToken` | `revoked_tokens` | jti + revoked_at + expires_at（注销 Token） |
| `Activity` | `activities` | user_id + target_type + target_id + action + metadata（审计日志） |
| `Notification` | `notifications` | user_id + type + content + actor_id + target_type + target_id + is_read |
| `NotificationPreference` | `notification_preferences` | user_id + email_enabled + websocket_enabled |
| `CollabInviteRevocation` | `collab_invite_revocations` | 协作邀请撤销记录 |
| `CollabSessionOverride` | `collab_session_overrides` | 协作会话级权限覆盖（踢人/改权限） |
| `RepoSearchFile` | `repo_search_files` | 代码搜索索引文件条目（repo_id + path + content 摘要） |
| `RepoSearchState` | `repo_search_states` | 搜索索引构建状态（head_commit + built_at + status） |

---

## 5. 关系设计要点

### 5.1 PR / Issue 编号（repo 内自增）

- `PullRequest.pr_number` / `Issue.issue_number` 在同一仓库内唯一，由 Service 层 INSERT 时查询当前最大编号 + 1
- 前端使用 `{owner}/{repo}/pull/{pr_number}` 风格路由

### 5.2 多对多关联表

显式 `Table(...)` 声明（非 association_proxy）：
- `issue_labels`（Issue ↔ Label）
- `repo_label_association`（Repository ↔ RepoLabel）
- `pr_label_association`（PullRequest ↔ PRLabel）

### 5.3 Fork 关系

```python
class Repository:
    forked_from_id = ForeignKey("repositories.id")  # 指向父仓库
    forks = relationship(..., remote_side="Repository.id")  # 反向
```

Service 层（`fork_service`）负责完整 clone + 重写 fork 关系字段。

---

## 6. Alembic 迁移

```
alembic/
├── env.py                 # 环境配置（同步引擎 + async 元数据）
├── script.py.mako         # 迁移模板
├── README
└── versions/
    ├── a58c8a7aeb0a_initial_uuid_schema.py
    ├── a7b8c9d0e1f2_add_collab_invite_revocations.py
    ├── b2c3d4e5f6a7_add_repository_ci_secret.py
    ├── b8c9d0e1f2a3_add_revoked_tokens.py
    ├── c3d4e5f6a7b8_add_watchers_and_watch_count.py
    ├── c9d0e1f2a3b4_add_repo_search.py
    ├── d4e5f6a7b8c9_add_dm_rooms_and_file_comments.py
    ├── e5f6a7b8c9d0_add_build_log_entries_streaming.py
    └── f6a7b8c9d0e1_add_collab_session_overrides.py
```

迁移按字母序执行（`a58c...` → `f6a7...`）。

### 6.1 迁移程序化入口

```python
# utils/db_migrate.py
def get_head_revision() -> str    # 获取当前 head
def get_current_revision() -> str # 获取已应用的版本
def run_migrations() -> None     # 程序化执行 upgrade head

# utils/init_database.py
def init_database() -> bool      # upgrade head + 管理员引导
def verify_database_ready() -> (bool, dict)  # 生产就绪校验
```

---

## 下一章

👉 [04 · 服务层（services）](04-services.md)
