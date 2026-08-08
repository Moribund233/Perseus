"""
Git HTTP Smart Protocol 认证控制器

用于 Nginx auth_request 子请求验证。该端点接收 Git 请求的 URI 和
Authorization 头，返回 200（允许）或 401/403（拒绝）。
"""
import re
import base64
import logging
from fastapi import APIRouter, Request, Response, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Repository, User
from models.repository_member import RepositoryMember
from models.async_db import get_async_db
from services.token_service import verify_token
from utils.password_utils import verify_password
from core.constants import ROLE_PRIORITY

logger = logging.getLogger(__name__)

router = APIRouter(tags=["git-auth"])

GIT_URI_PATTERN = re.compile(r"^/(?P<owner>[^/]+)/(?P<repo_name>[^/]+)\.git/")


def _extract_token(request: Request) -> str | None:
    """提取 Bearer token（不处理 Basic auth，Basic 由 _auth_basic 处理）"""
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def _auth_basic(request: Request, db: AsyncSession) -> Response | None:
    """Basic auth 用户名密码认证。
    
    返回 Response 表示认证结果（授权通过/拒绝），
    返回 None 表示无 Authorization 头需要走公开访问逻辑。
    """
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Basic "):
        return None

    try:
        decoded = base64.b64decode(auth[6:]).decode("utf-8")
        username, _, password = decoded.partition(":")
        username = username.strip()
        password = password.strip()
    except Exception:
        return Response(
            status_code=401,
            content="Invalid Basic auth format",
            headers={"WWW-Authenticate": 'Basic realm="perseus", Bearer realm="perseus"'},
        )

    if not username or not password:
        return Response(
            status_code=401,
            content="Missing username or password",
            headers={"WWW-Authenticate": 'Basic realm="perseus", Bearer realm="perseus"'},
        )

    # 查用户
    stmt = select(User).filter(
        User.username == username, User.is_active == True
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return Response(
            status_code=401,
            content="Invalid username or password",
            headers={"WWW-Authenticate": 'Basic realm="perseus", Bearer realm="perseus"'},
        )

    # 验证密码
    if not verify_password(password, user.password):
        return Response(
            status_code=401,
            content="Invalid username or password",
            headers={"WWW-Authenticate": 'Basic realm="perseus", Bearer realm="perseus"'},
        )

    # 认证通过，返回用户供后续权限检查
    return user


async def _check_public_access(
    db: AsyncSession, owner_name: str, repo_name: str, is_write: bool
) -> Response:
    repo_path = f"{owner_name}/{repo_name}"
    stmt = select(Repository).filter(
        Repository.path == repo_path, Repository.is_public == True
    )
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()

    if repo and not is_write:
        return Response(status_code=200)

    return Response(
        status_code=401,
        content="Authentication required",
        headers={"WWW-Authenticate": 'Basic realm="perseus", Bearer realm="perseus"'},
    )


async def _check_user_access(
    user: User, db: AsyncSession, owner_name: str, repo_name: str, is_write: bool
) -> Response:
    """检查认证用户对仓库的访问权限"""
    # 管理员完全放行
    if user.is_admin:
        return Response(status_code=200)

    repo_path = f"{owner_name}/{repo_name}"
    stmt = select(Repository).filter(Repository.path == repo_path)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()
    if not repo:
        return Response(status_code=404, content="Repository not found")

    # 公开仓库读放行
    if repo.is_public and not is_write:
        return Response(status_code=200)

    # 检查仓库成员
    stmt = select(RepositoryMember).filter(
        RepositoryMember.repository_id == repo.id,
        RepositoryMember.user_id == user.id,
        RepositoryMember.is_active == True,
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if not member:
        return Response(status_code=403, content="Access denied")

    if not is_write:
        return Response(status_code=200)

    if ROLE_PRIORITY.get(member.role, 0) >= ROLE_PRIORITY.get("developer", 2):
        return Response(status_code=200)

    return Response(status_code=403, content="Write access denied")


@router.api_route("/git-auth", methods=["GET", "POST", "HEAD"])
async def git_auth(request: Request, db: AsyncSession = Depends(get_async_db)):
    # Nginx 通过 X-Git-Request-URI 头传递原始 Git 请求 URI
    uri = request.headers.get("X-Git-Request-URI") or str(request.url.path)
    match = GIT_URI_PATTERN.match(uri)
    if not match:
        return Response(status_code=403, content="Invalid repository path")

    owner_name = match.group("owner")
    repo_name = match.group("repo_name")
    is_write = "git-receive-pack" in uri

    # 认证方式 1: Bearer token
    token = _extract_token(request)
    if token:
        token_data = verify_token(token, "access")
        if token_data is None:
            return Response(
                status_code=401,
                content="Invalid or expired token",
                headers={"WWW-Authenticate": 'Basic realm="perseus", Bearer realm="perseus"'},
            )
        stmt = select(User).filter(
            User.id == token_data.user_id, User.is_active == True
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            return Response(
                status_code=401,
                content="User not found",
                headers={"WWW-Authenticate": 'Basic realm="perseus", Bearer realm="perseus"'},
            )
        return await _check_user_access(user, db, owner_name, repo_name, is_write)

    # 认证方式 2: Basic auth（用户名/密码）
    basic_result = await _auth_basic(request, db)
    if isinstance(basic_result, User):
        return await _check_user_access(basic_result, db, owner_name, repo_name, is_write)
    elif isinstance(basic_result, Response):
        return basic_result

    # 认证方式 3: 无认证 → 公开访问
    return await _check_public_access(db, owner_name, repo_name, is_write)
