# Git HTTP 认证实现计划

**Goal:** 为 Git Smart HTTP 协议添加 JWT 认证，防止未经授权的 clone/push

**Architecture:** Nginx `auth_request` 在 Git 请求到达 git-cgi 前发送子请求到 FastAPI 端点验证 JWT 和仓库权限；支持 `Authorization: Bearer` 和 `Basic` 两种方案（Git 客户端可用 `http.extraHeader` 或 URL 嵌入 token）。

**Tech Stack:** FastAPI, Nginx/OpenResty, fcgiwrap, git-http-backend, PostgreSQL

---

### Task 1: 创建 git-auth FastAPI 端点

**Files:**
- Create: `controller/git_auth_controller.py`
- Modify: `api/routes_config.py`

- [ ] **Step 1: 创建 `controller/git_auth_controller.py`**

```python
"""
Git HTTP Smart Protocol 认证控制器

用于 Nginx auth_request 子请求验证。该端点接收 Git 请求的 URI 和
Authorization 头，返回 200（允许）或 401/403（拒绝），
不可由外部直接访问。
"""
import re
import logging
from fastapi import APIRouter, Request, Response, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Repository, User
from models.repository_member import RepositoryMember
from core.database import get_async_db
from services.token_service import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["git-auth"])

# Git URI 模式: /{owner}/{repo}.git/{action}
GIT_URI_PATTERN = re.compile(r"^/(?P<owner>[^/]+)/(?P<repo_name>[^/]+)\.git/")


@router.api_route("/git-auth", methods=["GET", "POST", "HEAD"])
async def git_auth(request: Request, db: AsyncSession = Depends(get_async_db)):
    """
    Nginx auth_request 子请求处理端点。

    验证 Git HTTP 请求的认证信息和仓库访问权限。
    返回 200 允许访问，401 要求认证，403 拒绝访问。

    支持两种认证方式:
    1. Authorization: Bearer <jwt>
    2. Authorization: Basic base64(x-access-token:<jwt>)
    """
    # 解析 URI 提取仓库信息
    uri = str(request.url.path)
    match = GIT_URI_PATTERN.match(uri)
    if not match:
        return Response(status_code=403, content="Invalid repository path")

    owner_name = match.group("owner")
    repo_name = match.group("repo_name")

    # 判断操作类型: receive-pack = push (写), 其余为读
    is_write = "git-receive-pack" in uri

    # 提取 JWT token
    token = _extract_token(request)
    if not token:
        # 无 token: 只有公开仓库的读操作允许
        return await _check_public_read_access(
            db, owner_name, repo_name, is_write
        )

    # 验证 JWT
    token_data = verify_token(token, "access")
    if token_data is None:
        return Response(status_code=401, content="Invalid or expired token")

    # 获取用户
    stmt = select(User).filter(
        User.id == token_data.user_id, User.is_active == True
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return Response(status_code=401, content="User not found")

    # 系统管理员拥有所有权限
    if user.is_admin:
        return Response(status_code=200)

    # 查找仓库
    repo_path = f"{owner_name}/{repo_name}"
    stmt = select(Repository).filter(Repository.path == repo_path)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()
    if not repo:
        return Response(status_code=404, content="Repository not found")

    # 公开仓库: 读操作允许任何人; 写操作需要成员权限
    if repo.is_public and not is_write:
        return Response(status_code=200)

    # 检查仓库成员权限
    stmt = select(RepositoryMember).filter(
        RepositoryMember.repository_id == repo.id,
        RepositoryMember.user_id == user.id,
        RepositoryMember.is_active == True,
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if not member:
        if repo.is_public:
            return Response(status_code=403, content="Write access denied")
        return Response(status_code=403, content="Access denied")

    # 读操作: readonly 及以上角色允许
    if not is_write:
        return Response(status_code=200)

    # 写操作: developer 及以上角色允许 (readonly 不能 push)
    from core.constants import ROLE_PRIORITY
    if ROLE_PRIORITY.get(member.role, 0) >= ROLE_PRIORITY.get("developer", 2):
        return Response(status_code=200)

    return Response(status_code=403, content="Write access denied")


def _extract_token(request: Request) -> str | None:
    """从 Authorization 头提取 JWT token"""
    auth = request.headers.get("Authorization")
    if not auth:
        return None

    # Bearer 方案
    if auth.startswith("Bearer "):
        return auth[7:]

    # Basic 方案: Git 客户端常用 x-access-token:<jwt> 或 x-oauth-basic:<jwt>
    if auth.startswith("Basic "):
        import base64
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
            # 格式: username:password, 取 password 部分
            _, _, password = decoded.partition(":")
            return password.strip()
        except Exception:
            return None

    return None


async def _check_public_read_access(
    db: AsyncSession, owner_name: str, repo_name: str, is_write: bool
) -> Response:
    """无 token 时的访问检查: 仅公开仓库的读操作允许"""
    if is_write:
        return Response(
            status_code=401,
            content="Authentication required",
            headers={"WWW-Authenticate": 'Bearer realm="perseus"'},
        )

    repo_path = f"{owner_name}/{repo_name}"
    stmt = select(Repository).filter(
        Repository.path == repo_path, Repository.is_public == True
    )
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()

    if repo:
        return Response(status_code=200)

    return Response(
        status_code=401,
        content="Authentication required",
        headers={"WWW-Authenticate": 'Bearer realm="perseus"'},
    )
```

- [ ] **Step 2: 注册路由到 `api/routes_config.py`**

  在 `create_api_router()` 函数中（约第 240 行 `return api_router` 之前），添加:
  ```python
  from controller.git_auth_controller import router as git_auth_router
  api_router.include_router(git_auth_router, prefix=API_V1_PREFIX)
  ```

- [ ] **Step 3: 验证路由注册**

  启动应用后确认:
  ```bash
  curl -s http://127.0.0.1:8001/api/v1/git-auth  # 应返回 403 (无 repo path)
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add controller/git_auth_controller.py api/routes_config.py
  git commit -m "feat: add git-auth endpoint for Nginx auth_request validation"
  ```

---

### Task 2: 更新 OpenResty dev proxy 配置

**Files:**
- Modify: `docker/nginx/perseus_dev_proxy.conf` (source)
- Modify: running OpenResty container config

- [ ] **Step 1: 在 Git location 外层添加 auth_request**

  在 `docker/nginx/perseus_dev_proxy.conf` 的 Git location block（第 50 行 `location ~ ^/...\.git`）中，在最外层（嵌套 location 之前）添加:

  ```nginx
  location ~ ^/[a-zA-Z0-9_-]+/[a-zA-Z0-9_\-\.]+\.git(/.*)?$ {
      # -- Git HTTP 认证 --
      # 子请求验证 JWT + 仓库权限，200=允许 401/403=拒绝
      auth_request /api/v1/git-auth;

      gzip off;
      ...
  ```

- [ ] **Step 2: 同步更新到运行中的 OpenResty 容器**

  ```bash
  docker exec 185c0034fb6e sh -c "sed -i '/^location ~ .*\\\.git/a\    auth_request /api/v1/git-auth;' /www/sites/perseus_dev/proxy/perseus.conf && nginx -t && nginx -s reload"
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add docker/nginx/perseus_dev_proxy.conf
  git commit -m "feat(nginx): add auth_request to Git proxy for JWT auth"
  ```

---

### Task 3: 更新生产 Nginx 配置

**Files:**
- Modify: `docker/nginx/nginx.conf`
- Modify: `docker/dev/nginx.dev.conf`

- [ ] **Step 1: 生产 nginx.conf 添加 auth_request**

  在 `docker/nginx/nginx.conf` 第 103 行 `location ~ ^/(...)/` 块中，嵌套 locations 之前添加:
  ```nginx
  location ~ ^/(?<username>[^/]+)/(?<reponame>[^/]+)\.git/ {
      # Git HTTP 认证
      auth_request /api/v1/git-auth;

      gzip off;
      ...
  ```

- [ ] **Step 2: 开发 nginx.dev.conf 添加 auth_request**

  在 `docker/dev/nginx.dev.conf` 第 176 行的 `location ~ ^/(...)/` 块中添加同样的 `auth_request /api/v1/git-auth;`。

- [ ] **Step 3: Commit**

  ```bash
  git add docker/nginx/nginx.conf docker/dev/nginx.dev.conf
  git commit -m "feat(nginx): add auth_request to production and dev nginx configs"
  ```

---

### Task 4: 验证端到端认证

- [ ] **Step 1: 无 token 访问公开仓库应允许**

  ```bash
  # 确保已有一个公开仓库
  curl -sI http://127.0.0.1:8001/admin/verify-fix.git/info/refs?service=git-upload-pack
  # 应返回 200
  ```

- [ ] **Step 2: 无 token push 应拒绝**

  ```bash
  curl -sI http://127.0.0.1:8001/admin/verify-fix.git/info/refs?service=git-receive-pack
  # 应返回 401
  ```

- [ ] **Step 3: 带有效 token push 应允许**

  ```bash
  TOKEN=<valid_token>
  curl -sI -H "Authorization: Bearer $TOKEN" \
    http://127.0.0.1:8001/admin/verify-fix.git/info/refs?service=git-receive-pack
  # 应返回 200
  ```

- [ ] **Step 4: 私有仓库无 token 应拒绝**

  创建一个私有仓库并测试 clone:
  ```bash
  curl -sI http://127.0.0.1:8001/admin/private-repo.git/info/refs?service=git-upload-pack
  # 应返回 401
  ```
