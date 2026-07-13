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
from core.constants import ROLE_PRIORITY

logger = logging.getLogger(__name__)

router = APIRouter(tags=["git-auth"])

GIT_URI_PATTERN = re.compile(r"^/(?P<owner>[^/]+)/(?P<repo_name>[^/]+)\.git/")


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    if auth.startswith("Bearer "):
        return auth[7:]
    if auth.startswith("Basic "):
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
            _, _, password = decoded.partition(":")
            return password.strip()
        except Exception:
            return None
    return None


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

    token = _extract_token(request)
    if not token:
        return await _check_public_access(db, owner_name, repo_name, is_write)

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

    if user.is_admin:
        return Response(status_code=200)

    repo_path = f"{owner_name}/{repo_name}"
    stmt = select(Repository).filter(Repository.path == repo_path)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()
    if not repo:
        return Response(status_code=404, content="Repository not found")

    if repo.is_public and not is_write:
        return Response(status_code=200)

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
