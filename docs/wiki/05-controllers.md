# 05 · 控制器与 API 路由

> Controller 层只做路由注册和参数解析，所有业务逻辑下沉到 Service。
> 34 个 Controller 注册顺序有讲究（`/{owner}/{repo}` 通配路由必须放最后）。

---

## 目录结构

```
api/
├── routes_prefix.py        # 前缀常量 + get_route_prefix()（打破循环导入）
├── routes_config.py        # create_api_router() —— 中心注册器
├── dependencies.py         # get_current_user / get_current_admin_user
├── error.py                # 错误端点
└── websocket/              # WebSocket 子系统（见 [06](06-websocket.md)）
controller/
├── app_controller.py
├── auth_controller.py
├── oauth_controller.py
├── git_auth_controller.py
├── user_controller.py
├── repository_controller.py
├── repository_browser_controller.py
├── repository_member_controller.py
├── branch_controller.py
├── commit_controller.py
├── pull_request_controller.py
├── pr_label_controller.py
├── release_controller.py
├── issue_controller.py
├── label_controller.py
├── fork_controller.py
├── star_controller.py
├── watch_controller.py
├── lfs_controller.py
├── key_controller.py
├── webhook_controller.py
├── stats_controller.py
├── activity_controller.py
├── notification_controller.py
├── search_controller.py
├── room_controller.py
├── chat_controller.py
├── dm_controller.py
├── file_comment_controller.py
├── collab_internal_controller.py
├── collab_invite_controller.py
├── collab_session_controller.py
├── build_controller.py
└── debug_controller.py
```

---

## 1. 统一模式

每个 Controller 文件：

```python
from fastapi import APIRouter, Depends, Query, Path
from models.async_db import get_async_db
from api.dependencies import get_current_user
from core.exception import NotFoundException, AuthorizationException
from services import some_service

router = APIRouter()                   # 大部分自己带 prefix

@router.post("/...")
async def do_something(
    body: SomePydanticModel,           # 请求体校验
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),  # 可选：部分端点不需要认证
):
    try:
        return await some_service.do_something(db, user, body)
    except XxxException: ...
```

---

## 2. 路由前缀

`api/routes_prefix.py` 维护常量 + 提供无副作用的 `get_route_prefix()`（打破循环导入）：

| 常量 | 值 |
|------|----|
| `API_V1_PREFIX` | `"/api/v1"` |
| 控制器 router 自带前缀 | 各文件内 `APIRouter(prefix="/api/v1/xxx")` |

Controller 直接 import `routes_prefix` 即可，不反向依赖 `routes_config`。

---

## 3. 路由注册顺序（重要！）

`api/routes_config.create_api_router()` 严格按以下顺序 include，因为 `repository_controller` 有 `/{owner}/{repo}` 通配路由，必须放最后：

| 顺序 | Controller | 路由前缀 | 备注 |
|------|-----------|---------|------|
| 1 | `app_controller` | `/` | **最先**（根路由 + 健康检查） |
| 2 | `repository_browser_controller` | `/api/v1/repositories/...` | 必须在 repository 之前注册 |
| 3 | `auth_controller` | `/api/v1/auth` | 登录 / 刷新 |
| 3a | `git_auth_controller` | `/api/v1/git/auth` | Nginx auth_request |
| 3a2 | `collab_internal_controller` | `/api/v1/collab-internal/*` | collab-gateway 内部回调 |
| 3b | `oauth_controller` | OAuth 端点 | GitHub / GitLab |
| 3c | `oauth_controller.account_router` | OAuth 账号管理 | |
| 4 | `user_controller` | `/api/v1/users` | 含 `/me` / `/me/pull-requests` / `/me/issues` |
| 6 | `repository_member_controller` | `/api/v1/repositories/{id}/members` | |
| 6b | `fork_controller` | `/api/v1/repositories/{id}/forks` | |
| 6c | `star_controller` | `/api/v1/repositories/{id}/star` | |
| 6c-bis | `watch_controller` | `/api/v1/repositories/{id}/watch` | |
| 6c-ter | `collab_invite_controller` | 协作邀请 | |
| 6c-quater | `collab_session_controller` | 协作会话权限覆盖 | |
| 6d | `label_controller` | 仓库标签 | |
| 6d-bis | `file_comment_controller` | 行内评论 | |
| 6e | `lfs_controller` | Git LFS | |
| 7 | `branch_controller` | 分支 | |
| 8 | `commit_controller` | 提交 | |
| 9 | `pull_request_controller` | PR | |
| 9c | `pr_label_controller` | PR 标签 | |
| 9b | `release_controller` | Release | |
| 10 | `issue_controller` | Issue | |
| 11 | `key_controller` | SSH Key | |
| 11b | `webhook_controller` | WebHook | |
| 11c | `stats_controller` | 仓库统计 | |
| 11d | `activity_controller` | 审计活动 | |
| 11e | `search_controller` | 代码搜索（仓库级） | |
| 11e2 | `search_controller.global_search_router` | 跨仓库全局搜索 | |
| 11f | `build_controller` | 构建状态 | |
| 11g | `room_controller` | 聊天室 | |
| 11g-bis | `dm_controller` | DM 私聊 | |
| 11h | `chat_controller` | 聊天消息 | |
| 11f | `notification_controller` | 通知 | |
| **5** | **`repository_controller`** | **`/{owner}/{repo}`** | **必须最后！通配路由** |
| 12 | `debug_controller` | 仅 debug 模式 | |
| 12 | `api/error` | 错误端点 | |
| 13 | `api.websocket` | `/ws` | WebSocket |

---

## 4. 依赖注入

### 4.1 `api/dependencies.py`

```python
security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    # 校验 JWT → 查 User → 检查 is_active

async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    # 强制 is_admin
```

典型用法：

```python
@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return user_to_dict(user)
```

### 4.2 `get_async_db`

每个需要数据库操作的端点都显式注入：

```python
@router.post("/")
async def create_repo(body: RepoCreate,
                      db: AsyncSession = Depends(get_async_db),
                      user: User = Depends(get_current_user)):
    return await repository_service.create(db, user, body)
```

Service 不自己创建 session，保持可测试性（测试可传入 mock session）。

---

## 5. Controller 清单（按功能域）

### 5.1 认证域

| Controller | 端点 | 说明 |
|-----------|------|------|
| `auth_controller` | `POST /api/v1/auth/login` | 用户名/邮箱 + 密码 → 双令牌 |
| | `POST /api/v1/auth/refresh` | refresh_token → 新 access_token |
| | `POST /api/v1/auth/logout` | 注销（写 RevokedToken） |
| | `GET /api/v1/auth/me` | 无需 Token 的健康检查 |
| `oauth_controller` | `GET /api/v1/auth/oauth/{provider}` | 重定向到 GitHub/GitLab |
| | `GET /api/v1/auth/oauth/{provider}/callback` | 换码 → 关联/创建账号 → 发令牌 |
| | account_router `/api/v1/user/oauth-accounts/*` | OAuth 账号绑定管理 |
| `git_auth_controller` | `/api/v1/git/auth` | Nginx auth_request，Git HTTP Smart Protocol 鉴权 |

### 5.2 用户域

| Controller | 端点 | 说明 |
|-----------|------|------|
| `user_controller` | `GET/POST /api/v1/users` | 用户列表 / 注册 |
| | `GET /api/v1/users/{id}` | 用户详情 |
| | `GET /api/v1/users/me` | 当前用户 |
| | `PUT /api/v1/users/me` | 更新个人信息 |
| | `GET /api/v1/users/me/dashboard` | 仪表盘聚合数据 |
| | `GET /api/v1/users/me/pull-requests` / `issues` | "我的工作" |

### 5.3 仓库域

| Controller | 端点 | 说明 |
|-----------|------|------|
| `repository_controller` | `GET/POST /api/v1/repositories` | 列表 / 创建 |
| | `GET /{owner}/{repo}` | 详情 |
| | `PUT/DELETE /{owner}/{repo}` | 更新 / 删除 |
| | `POST /{owner}/{repo}/fork` | Fork |
| | `POST /{owner}/{repo}/star` / `DELETE` | Star / Unstar |
| | `POST /{owner}/{repo}/watch` / `DELETE` | Watch / Unwatch |
| | `POST /{owner}/{repo}/archive` | 归档 |
| `repository_browser_controller` | `GET /{id}/tree/{path}` | 树 |
| | `GET /{id}/blob/{path}` | 文件内容 |
| | `GET /{id}/commits/{path}` | 提交历史 |
| | `GET /{id}/diff/{path}` | 文件 diff |
| | `GET /{id}/readme` | README |
| `repository_member_controller` | `/api/v1/repositories/{id}/members/*` | 成员 / 角色 |
| `label_controller` | `/api/v1/repositories/{id}/labels/*` | 仓库级标签 |

### 5.4 Git 域

| Controller | 端点 | 说明 |
|-----------|------|------|
| `branch_controller` | `GET/POST /{id}/branches` | 分支列表 / 创建 |
| | `DELETE /{id}/branches/{name}` | 删除 |
| | `GET /{id}/branches/{name}` | 详情 |
| `commit_controller` | `GET /{id}/commits` | 提交历史（分页） |
| | `GET /{id}/commits/{hash}` | 提交详情 |

### 5.5 PR / Issue

| Controller | 端点 | 说明 |
|-----------|------|------|
| `pull_request_controller` | `GET/POST /{id}/pull-requests` | PR 列表 / 创建 |
| | `GET /{id}/pull-requests/{num}` | PR 详情 |
| | `POST /{id}/pull-requests/{num}/merge` | 合并 |
| | `POST /{id}/pull-requests/{num}/comments` | 评论（含行级） |
| | `POST /{id}/pull-requests/{num}/reviews` | 审查 |
| | `POST /{id}/pull-requests/{num}/draft` | Draft 切换 |
| `pr_label_controller` | `POST /{id}/pull-requests/{num}/labels` | 绑定标签 |
| `issue_controller` | `GET/POST /{id}/issues` | Issue 列表 / 创建 |
| | `GET /{id}/issues/{num}` | Issue 详情 |
| | `POST /{id}/issues/{num}/close` / `reopen` | 状态切换 |
| | `POST /{id}/issues/batch/*` | 批量操作 |
| `file_comment_controller` | `GET/POST /{id}/file-comments` | 行内评论 Discussions |

### 5.6 Release / WebHook / Build

| Controller | 端点 | 说明 |
|-----------|------|------|
| `release_controller` | `/api/v1/repositories/{id}/releases/*` | Release + 附件 |
| `webhook_controller` | `/api/v1/repositories/{id}/webhooks/*` | WebHook + 投递历史 |
| `build_controller` | `/api/v1/repositories/{id}/builds/*` | 构建状态 + 日志流 |

### 5.7 协作编辑

| Controller | 端点 | 说明 |
|-----------|------|------|
| `collab_internal_controller` | `/api/v1/collab-internal/*` | collab-gateway ←→ Python 内部回调（HMAC） |
| `collab_invite_controller` | `/api/v1/repositories/{id}/collab-invites` | 协作邀请签发 / 撤销 |
| `collab_session_controller` | `/api/v1/collab-sessions/*` | 会话级权限覆盖（踢人 / 改权限） |

### 5.8 实时 / 通知

| Controller | 端点 | 说明 |
|-----------|------|------|
| `room_controller` | `/api/v1/rooms/*` | 聊天室 CRUD |
| `dm_controller` | `/api/v1/dm/*` | DM 会话 |
| `chat_controller` | `/api/v1/rooms/{id}/messages` | 聊天消息 |
| `notification_controller` | `/api/v1/notifications/*` | 通知 + 偏好设置 |

### 5.9 搜索 / 统计 / 审计

| Controller | 端点 | 说明 |
|-----------|------|------|
| `search_controller` | `GET /{id}/search?q=...` | 仓库内搜索 |
| | `GET /api/v1/search?q=...` | 跨仓库全局搜索 |
| `stats_controller` | `GET /{id}/stats` | 仓库统计聚合 |
| `activity_controller` | `GET /api/v1/activity` | 审计日志 |

### 5.10 SSH Key / LFS

| Controller | 端点 | 说明 |
|-----------|------|------|
| `key_controller` | `/api/v1/keys/*` | SSH Key 管理 |
| `lfs_controller` | `/api/v1/repositories/{id}/lfs/*` | Git LFS |

### 5.11 应用管理（Admin）

| Controller | 端点 | 说明 |
|-----------|------|------|
| `app_controller` | `GET /` | 欢迎 |
| | `GET /health` | 健康检查 |
| | `GET /api/app/status` | 应用状态 |
| | `POST /api/app/restart` | 触发优雅关闭 |
| | `GET /api/app/logs` | 日志查看 |
| | `/api/app/config` | 配置热加载 |
| `debug_controller` | debug 模式启用 | 调试端点 |

---

## 6. 错误处理

### 6.1 Controller 异常抛出

Controller 层不做 try/except 包裹，让异常冒泡到全局处理器：

```python
# 好的做法
raise NotFoundException(detail="Repository not found", error_code="repo_not_found")
```

### 6.2 `utils/exception_handler.py`

```python
def setup_exception_handlers(app: FastAPI) -> None:
    # 注册：
    #   - BaseException → 返回结构化错误 + 国际化
    #   - HTTPException  → 默认
    #   - Exception      → 500 + Sentry + 安全脱敏
```

### 6.3 统一响应构建

```python
# utils/response_builder.py
def success(data=None, message="OK") -> dict    # {"success": True, "data": ..., "message": ...}
def error(message, code=None, status=400) -> dict
```

---

## 7. Swagger / ReDoc

开发模式下自动启用，访问：

- `http://host:8000/docs` —— Swagger UI
- `http://host:8000/redoc` —— ReDoc

---

## 下一章

👉 [06 · WebSocket 子系统](06-websocket.md)
