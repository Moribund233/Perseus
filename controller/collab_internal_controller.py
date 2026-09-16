"""
协作编辑内部回调控制器（Yjs 网关专用）

供 collab-gateway（Hocuspocus 哑管道容器）通过服务间调用回调 app：
- POST /collab/auth   连接鉴权: 校验用户 token + docKey 仓库读写权限
- GET  /collab/doc    文档加载: 从 Git 读取初始内容 (onLoadDocument)
- POST /collab/save   协作保存: 以提交者身份写入 Git commit (onStateless 触发)

安全模型:
- 网关在 onAuthenticate 阶段完成用户鉴权; 本控制器每次调用均要求
  内部共享密钥头 X-Collab-Internal-Secret == PERSEUS_COLLAB_INTERNAL_SECRET
- 密钥未配置时端点整体 503 (安全默认, 未部署协作网关即不可达)
- save 携带用户 access token, 每次保存实时校验写权限 (不缓存)

docKey 格式 (与旧 F-204 兼容): "{repository_id}:{branch}:{path}"
- git 引用名不允许含 ':', 因此 branch 为第二个 ':' 之前的字段
- path 允许含 ':' (极少见), 取第二个 ':' 之后的全部内容
"""
import asyncio
import logging
import os
from typing import Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exception import AuthorizationException, NotFoundException, ValidationException
from models import Repository, User
from models.async_db import get_async_db
from services.search_service import SearchService
from services.token_service import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["collab-internal"])

# 内部服务间共享密钥的请求头与环境变量名
INTERNAL_SECRET_HEADER = "X-Collab-Internal-Secret"
INTERNAL_SECRET_ENV = "PERSEUS_COLLAB_INTERNAL_SECRET"

# 读权限角色 (加入会话/加载文档), 与旧 F-204 保持一致
READ_ROLES = ["owner", "admin", "developer", "viewer"]
# 写权限角色 (保存提交)
WRITE_ROLES = ["owner", "admin", "developer"]

# 文档内容上限 (字符), 与旧 F-204 MAX_DOC_CHARS 一致
MAX_CONTENT_CHARS = 2_000_000


class CollabAuthRequest(BaseModel):
    token: str
    docKey: str


class CollabSaveRequest(BaseModel):
    token: str
    docKey: str
    content: str
    message: Optional[str] = None


def make_doc_key(repository_id: str, branch: str, path: str) -> str:
    """文档标识: 仓库:分支:路径"""
    return f"{repository_id}:{branch}:{path}"


def parse_doc_key(doc_key: str) -> Tuple[UUID, str, str]:
    """
    解析 docKey 为 (repository_id, branch, path)

    Raises:
        ValidationException: 格式非法
    """
    parts = str(doc_key or "").split(":")
    if len(parts) < 3 or not parts[0].strip() or not parts[1].strip():
        raise ValidationException(detail="docKey 格式非法, 应为 repository_id:branch:path", error_code="collab_invalid_dockey")
    try:
        repository_id = UUID(parts[0].strip())
    except (ValueError, AttributeError, TypeError):
        raise ValidationException(detail="docKey 中 repository_id 非法", error_code="collab_invalid_repository_id")
    branch = parts[1].strip()
    path = ":".join(parts[2:]).strip().lstrip("/")
    if not branch or not path:
        raise ValidationException(detail="docKey 中 branch/path 不能为空", error_code="collab_dockey_missing_parts")
    return repository_id, branch, path


def _require_internal_secret(request: Request) -> None:
    """校验内部共享密钥; 未配置时端点整体不可用 (安全默认)"""
    expected = os.environ.get(INTERNAL_SECRET_ENV, "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="协作内部 API 未启用")
    provided = request.headers.get(INTERNAL_SECRET_HEADER, "")
    if provided != expected:
        raise AuthorizationException(detail="内部密钥校验失败", error_code="collab_invalid_internal_secret")


async def _load_user_by_token(db: AsyncSession, token: str) -> User:
    token_data = verify_token(token, "access")
    if token_data is None:
        raise HTTPException(status_code=401, detail="无效或过期的 token")
    result = await db.execute(select(User).filter(User.id == token_data.user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


async def _get_repo_or_404(db: AsyncSession, repository_id: UUID) -> Repository:
    result = await db.execute(select(Repository).filter(Repository.id == repository_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")
    return repo


async def _has_role(db: AsyncSession, repository_id: UUID, user_id: UUID, roles: list) -> bool:
    from utils.permission_utils import check_repository_permission

    return await check_repository_permission(db, repository_id, user_id, roles)


@router.post("/collab/auth")
async def collab_auth(
    body: CollabAuthRequest, request: Request, db: AsyncSession = Depends(get_async_db)
):
    """
    连接鉴权 (网关 onAuthenticate 回调)

    Returns:
        user_id, username, can_write, repository_id, branch, path
    """
    _require_internal_secret(request)
    user = await _load_user_by_token(db, body.token)
    repository_id, branch, path = parse_doc_key(body.docKey)

    repo = await _get_repo_or_404(db, repository_id)

    if not await _has_role(db, repository_id, user.id, READ_ROLES):
        raise AuthorizationException(detail="没有该仓库的访问权限", error_code="collab_repository_access_denied")

    can_write = await _has_role(db, repository_id, user.id, WRITE_ROLES)

    return {
        "user_id": str(user.id),
        "username": user.username,
        "can_write": can_write,
        "repository_id": str(repository_id),
        "branch": branch,
        "path": path,
        "repo_path": repo.path,
    }


@router.get("/collab/doc")
async def collab_doc(
    request: Request,
    docKey: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    文档加载 (网关 onLoadDocument 回调)

    Returns:
        {content, branch, path}; 二进制文件 415; 文件不存在 404
    """
    _require_internal_secret(request)
    repository_id, branch, path = parse_doc_key(docKey)
    repo = await _get_repo_or_404(db, repository_id)

    from services.repository_browser_service import get_blob_content
    from utils.git_utils import get_repository_storage_path

    repo_path = get_repository_storage_path(repo.path)
    blob = await get_blob_content(repo_path, ref=branch, path=path)
    if blob.get("is_binary"):
        raise HTTPException(status_code=415, detail="不支持协作编辑二进制文件")

    return {"content": blob.get("content", "") or "", "branch": branch, "path": path}


@router.post("/collab/save")
async def collab_save(
    body: CollabSaveRequest, request: Request, db: AsyncSession = Depends(get_async_db)
):
    """
    协作保存 (网关 onStateless 触发): 以提交者身份写入 Git commit

    每次保存实时校验写权限, 返回 commit_id 供网关向会话广播。
    """
    _require_internal_secret(request)
    if len(body.content) > MAX_CONTENT_CHARS:
        raise HTTPException(status_code=413, detail="文档内容超出上限")

    user = await _load_user_by_token(db, body.token)
    repository_id, branch, path = parse_doc_key(body.docKey)
    repo = await _get_repo_or_404(db, repository_id)

    if not await _has_role(db, repository_id, user.id, WRITE_ROLES):
        raise AuthorizationException(detail="没有该仓库的写入权限", error_code="collab_repository_write_denied")

    from services.repository_browser_service import commit_file
    from utils.git_utils import get_repository_storage_path

    repo_path = get_repository_storage_path(repo.path)
    commit_message = (body.message or "").strip() or f"Update {path}"
    commit = await commit_file(
        repo_path,
        branch,
        path,
        body.content,
        user.full_name or user.username,
        user.email,
        commit_message,
    )

    # F-039: 协作保存后增量更新搜索索引 (单文件, 放线程池避免阻塞事件循环)
    try:
        await asyncio.to_thread(SearchService.update_files, repo_path, [path])
    except Exception as index_err:
        logger.warning("Search index update failed after collab save: %s", index_err)

    return {
        "commit_id": str(commit.get("commit_id", "")),
        "branch": branch,
        "path": path,
        "saved_by": user.username,
        "message": commit_message,
    }
