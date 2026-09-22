# 04 · 服务层（services）

> 业务逻辑汇聚点。Controller 层只做路由和参数解析，所有校验、权限、数据库操作、Git 操作、HTTP 调用都在 Service 层。

---

## 目录结构

```
services/
├── auth/
│   └── oauth.py                    # GitHub / GitLab OAuth Provider
├── realtime/
│   ├── __init__.py
│   ├── room_service.py             # 聊天室 CRUD
│   ├── chat_service.py             # 聊天消息收发
│   ├── event_service.py            # 事件广播（仓库/全局事件）
│   └── presence_service.py         # 在线状态 / 用户活跃度
├── token_service.py                # JWT 双令牌（access + refresh）
├── revocation_cache.py             # 注销 Token 的内存缓存 + Redis 持久化
├── oauth_service.py                # OAuth 完整流程 + state store（Redis）
├── user_service.py                 # 用户注册 / 查找 / dashboard 聚合
├── repository_service.py           # 仓库 CRUD + 物理仓缓存（30s TTL）
├── repository_browser_service.py   # pygit2 裸仓操作（tree / blob / diff / symlink / 语言检测）
├── repository_browser_service.py   # 代码搜索（Git 对象索引 + 主库 + pg_trgm GIN 回退）
├── branch_service.py               # 分支操作（创建 / 删除 / 合并）
├── commit_service.py               # 提交历史查询（批量拉取 / 分页）
├── pull_request_service.py         # PR 创建 / 合并 / 评论 / Draft / 冲突检测
├── issue_service.py                # Issue CRUD / 状态切换 / 批量操作 / 标签
├── star_service.py                 # Star / Unstar + 原子计数更新
├── watch_service.py                # Watch / Unwatch
├── fork_service.py                 # Fork 完整 clone + 父仓关系字段重写
├── label_service.py                # 仓库级标签 CRUD
├── pr_label_service.py             # PR 标签绑定
├── pr_activity_service.py          # PR 时间线活动记录
├── release_service.py              # Release CRUD + 附件 + 模板描述渲染
├── release_asset_service.py        # Release 附件文件系统读写
├── webhook_service.py              # WebHook CRUD + 投递任务（httpx + HMAC-SHA256 + 重试）
├── notification_service.py         # 通知双通道（DB 持久化 + WS 实时推送）+ 偏好
├── notification_preference_service.py # 通知偏好读写
├── key_service.py                  # SSH 密钥 CRUD + 指纹校验
├── lfs_service.py                  # Git LFS 锁 / 批量操作
├── lfs_storage.py                  # LFS 存储后端（local / S3）
├── search_service.py               # 代码搜索（主库索引 + pg_trgm + tree 回退 + 符号提取）
├── file_comment_service.py         # 行内评论 Discussions
├── collab_invite_service.py        # 协作邀请签发 / 撤销
├── collab_session_service.py        # 协作会话级权限覆盖
├── stats_service.py                # 仓库统计（Stars / Forks / 活跃度聚合）
├── dashboard_service.py             # 首页仪表盘（我创建的 PR / Issue / 仓库活跃度）
├── app_service.py                  # 应用运维：状态查询 / 重启触发 / 日志查看
├── config_service.py               # 配置热加载 / 校验
├── database_manager.py              # 数据库管理：健康 / 就绪校验 / schema 版本
├── grafana_service.py              # Grafana 管理面板集成
├── metrics_service.py               # 运行时指标（请求 / 进程时序存储）
├── monitoring_service.py            # Admin 控制台监控面板后端
├── process_metrics.py               # 进程指标采样器（psutil，15s 周期）
├── worker_registry.py              # Worker 心跳 + 注册表（Redis）
├── orchestration_service.py        # 启动顺序编排
├── attachment_service.py           # 通用附件（Issue / PR 评论内嵌）
├── language_service.py             # 代码语言识别
├── collab_invite_service.py        # 协作邀请签发/撤销（仅成员可签）
├── collab_session_service.py        # 协作会话级权限覆盖
├── stats_service.py                # 仓库统计聚合
├── redis_admin_service.py          # Redis 管理（INFO / KEYS / 内存 / 慢查询）
├── docker_write_service.py         # Docker Compose ACL / 写访问控制
├── monitoring_service.py           # Admin 监控后端
├── worker_registry.py              # Worker 注册表（Redis）
├── process_metrics.py              # 进程指标采样（psutil）
└── activity_service.py             # 审计活动（Activity 模型写入）
```

---

## 2. 关键类与入口函数速查

### 2.1 认证与 Token

**`token_service.py`**

| 函数 | 说明 |
|------|------|
| `class TokenData` | 数据类：user_id / username / token_type / exp / jti |
| `create_access_token(user, extra_claims) -> str` | 生成 access JWT（默认 30 min） |
| `create_refresh_token(user) -> str` | 生成 refresh JWT（默认 7 天） |
| `create_token_pair(user, extra_claims) -> dict` | 同时生成一对令牌 |
| `verify_token(token, token_type) -> Optional[TokenData]` | 校验签名 + 过期时间 |
| `verify_token_active(db, token, token_type) -> Optional[TokenData]` | 完整校验 = verify_token + revoked check + 类型校验 |

**`revocation_cache.py`**

- 注销 Token 缓存：Redis + 进程内 fallback
- TTL 与 Token 剩余有效期一致

**`oauth_service.py`**

| 类 | 说明 |
|----|------|
| `class OAuthStateStore` | 存储 OAuth `state` 参数（Redis，TTL 10 min）防止 CSRF |
| `class OAuthService` | 发起授权 + 回调换码 + 创建/关联 UserOAuthAccount |

### 2.2 用户与仓库

**`user_service.py`**

- `user_to_dict(user)` —— 用户字典序列化（安全移除 password）
- 用户注册（bcrypt 密码哈希 + 唯一性校验）
- 按 username / email 查找

**`repository_service.py`**

- 仓库 CRUD + is_public / is_archived / path 唯一性
- **物理仓缓存**：`ttl_cache(30)` 装饰器缓存 pygit2 打开的裸仓对象（减少磁盘 I/O）
- fork_count / star_count / watch_count 原子递增

**`repository_browser_service.py`**

- 核心：`pygit2.Repository` 操作封装
- 主要能力：`get_tree` / `get_blob` / `get_blob_content` / `get_diff` / `get_commit` / `list_commits` / `get_file_content`
- `detect_file_language(filename)` —— 基于扩展名 → 语言映射
- 处理：符号链接、submodule、大文件截断（> 10MB）

### 2.3 Git 域

**`branch_service.py`**

- 创建（从已有 commit 切分支）
- 删除（保护分支不允许删）
- 列出（分页 + 搜索）

**`commit_service.py`**

- 仓库提交历史（批量拉取，避免逐条查询）
- 提交详情 + parent 解析

### 2.4 PR / Issue

**`pull_request_service.py`**

- 创建 PR（source/target branch，diff 预计算）
- 合并（pygit2 merge + commit + update target branch）
- Draft 切换
- 冲突检测（尝试 merge 并捕获 `MergeConflictError`）
- 评论 + 回复 + 行内评论
- 审查状态变更（APPROVED / CHANGES_REQUESTED）

**`issue_service.py`**

- Issue CRUD / 状态切换 / 优先级
- 标签管理（多对多）
- **批量操作**：批量关闭 / 批量更新 / 批量打标签
- 评论

### 2.5 Release / WebHook / Build

**`release_service.py`**

- Release CRUD + Draft + Pre-release
- `build_release_response(release, include_assets)` —— 字典序列化
- `build_asset_response(asset)` —— 附件字典序列化

**`webhook_service.py`**

- WebHook CRUD
- **投递执行**（httpx 异步 + 超时 + HMAC-SHA256 签名 + 指数退避重试）
- 投递历史 + 状态追踪
- `generate_signature(payload, secret) -> str` —— `sha256(secret, payload)`

**`build_service.py`**

- 构建状态更新（6 种：pending / running / success / failure / error / cancelled）
- CI 回调（外部 runner 用 ci_secret 签名）

**`build_log_entry.py`**

- 构建日志条目（stdout/stderr 分片，支持流式 WebSocket 推送）

### 2.6 实时协作

**`services/realtime/room_service.py`** —— 聊天室 CRUD

**`services/realtime/chat_service.py`** —— 聊天消息收发 + 未读计数

**`services/realtime/event_service.py`** —— 事件广播（仓库级事件：push / pr_update / issue_create 等）

**`services/realtime/presence_service.py`**（`presence_store`）—— 在线状态存储，Redis + 进程内 fallback

**`services/collab_invite_service.py`** —— 协作邀请链接签发（仅仓库成员）

**`services/collab_session_service.py`** —— 协作会话级权限覆盖（踢人、改权限）

### 2.7 通知 / 审计 / 搜索

**`notification_service.py`**

- 创建通知（双写 DB + WS 实时推送）
- 标记已读 / 全部已读
- 偏好设置（email / websocket 开关）
- `build_notification_response(notif)` —— 字典序列化

**`activity_service.py`** —— 审计活动（Activity 模型写入）

**`search_service.py`**

| 类 | 说明 |
|----|------|
| `class SearchResult` | 单条结果（repo_id + path + line + content） |
| `class SearchResponse` | 聚合响应（results + total + truncated） |
| `class SearchService` | 代码搜索核心 |

搜索优先级：
1. **主库索引**（`RepoSearchFile` 表，`pg_trgm` GIN 加速 `ILIKE '%q%'`）
2. **Git tree 回退**（指定非默认 ref 或索引未构建时，pygit2 进程内扫描）
3. **符号提取**（语言识别 → 提取类/函数/变量定义行）

### 2.8 运维

**`app_service.py`** —— 应用状态查询 / 日志查看 / 重启触发（调用 `core.lifespan.trigger_graceful_shutdown`）

**`config_service.py`** —— 配置热加载 + 校验

**`database_manager.py`** —— 数据库健康 / 就绪校验 / schema 版本查询

**`grafana_service.py`** —— Grafana 管理面板集成

**`metrics_service.py`** —— 运行时指标时序存储（请求分钟桶 + 进程指标）

**`monitoring_service.py`** —— Admin 控制台监控面板后端

**`process_metrics.py`**

| 类 | 说明 |
|----|------|
| `class ProcessMetrics` | psutil 采样器（内存 RSS / CPU % / 启动时间） |
| `get_process_metrics() -> ProcessMetrics` | 全局单例 |
| `reset_process_metrics() -> None` | 测试重置 |

**`worker_registry.py`**

| 类 | 说明 |
|----|------|
| `class WorkerRegistry` | Redis worker 注册表（心跳 20s） |

**`redis_admin_service.py`**

| 类 | 说明 |
|----|------|
| `class RedisAdminService` | Redis INFO / KEYS / 内存 / 慢查询 / CONFIG SET |
| `get_redis_admin_service() -> RedisAdminService` | 单例 |

### 2.9 其他

- **`star_service.py`** —— Star / Unstar + 原子计数
- **`watch_service.py`** —— Watch / Unwatch
- **`fork_service.py`** —— Fork 仓库（完整 clone + 重写路径）
- **`label_service.py`** / **`pr_label_service.py`** —— 标签
- **`member_service.py`** —— 成员角色读写
- **`key_service.py`** —— SSH Key CRUD + 指纹
- **`lfs_service.py`** + **`lfs_storage.py`** —— Git LFS
- **`stats_service.py`** —— 仓库统计聚合
- **`dashboard_service.py`** —— 首页仪表盘数据聚合
- **`file_comment_service.py`** —— 行内评论
- **`pr_activity_service.py`** —— PR 活动记录
- **`language_service.py`** —— 代码语言识别
- **`attachment_service.py`** —— Issue/PR 附件
- **`docker_write_service.py`** —— Docker ACL
- **`orchestration_service.py`** —— 启动顺序编排

---

## 3. 服务层统一模式

```python
# 每个 service 文件的常见形态
async def do_something(
    db: AsyncSession,                     # 1. 显式接收 AsyncSession（不在内部创建）
    user: User,                           # 2. 业务实体参数
    repo_id: uuid.UUID,
    ...
) -> SomeResult:
    # 3. 先权限校验（用 utils.permission_utils）
    # 4. 业务校验（查存在性、唯一性）
    # 5. 写库（SQLAlchemy 2.0 风格）
    # 6. 调用 pygit2（需要时）
    # 7. 触发 WebSocket / 通知（需要时）
    # 8. 返回（字典 / DTO / HTTPException）
```

---

## 4. 跨服务依赖图（典型）

```
pull_request_service
    ├──► repository_service (查仓库)
    ├──► repository_browser_service (查目标分支 commit)
    ├──► pr_activity_service (写 PR 时间线)
    ├──► notification_service (PR 更新通知)
    ├──► webhook_service (触发 pr_opened/updated/merged)
    └──► utils.git_utils (merge)

webhook_service
    ├──► httpx.AsyncClient (投递 HTTP 请求)
    └──► utils.webhook_trigger (包装投递上下文)

search_service
    ├──► repository_browser_service (Git tree 回退扫描)
    ├──► language_service (语言识别)
    └──► (pg_trgm / SQLite LIKE)

token_service
    └──► revocation_cache (查注销)
```

---

## 下一章

👉 [05 · 控制器与 API 路由](05-controllers.md)
