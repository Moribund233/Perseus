"""
协作会话级角色覆盖控制器

供会话发起人（仓库 owner/admin）管理某协作文档的成员权限：
- POST /{repo_id}/collab/sessions/permission  改权限 / 清空覆盖
- POST /{repo_id}/collab/sessions/kick        踢出会话

覆盖层由 collab_internal_controller 在 /collab/auth 与 /collab/save 强制执行，
因此改权限/踢出在成员下一次鉴权或保存时即时生效（配合网关对 403 的断连）。
"""
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user
from api.routes_prefix import get_route_prefix
from core.exception import (
    AuthorizationException,
    NotFoundException,
    ValidationException,
)
from controller.collab_internal_controller import parse_doc_key
from models import Repository, User
from models.async_db import get_async_db
from services.collab_session_service import kick as kick_member
from services.collab_session_service import set_permission
from utils.permission_utils import check_repository_owner_or_admin

router = APIRouter(prefix=get_route_prefix("repositories"), tags=["collab-sessions"])


class SetPermissionRequest(BaseModel):
    """会话成员权限覆盖请求体"""

    doc_key: str = Field(..., min_length=1, description="文档标识 repository_id:branch:path")
    user_id: uuid.UUID = Field(..., description="被覆盖的成员用户ID")
    scope: Optional[Literal["read", "write"]] = Field(
        None, description="覆盖档位; null 表示清空覆盖回落到仓库角色"
    )


class KickRequest(BaseModel):
    """踢出会话成员请求体"""

    doc_key: str = Field(..., min_length=1, description="文档标识 repository_id:branch:path")
    user_id: uuid.UUID = Field(..., description="被踢出的成员用户ID")


def _serialize(override) -> dict:
    return {
        "doc_key": override.doc_key,
        "user_id": str(override.user_id),
        "scope": override.scope,
        "is_kicked": override.is_kicked,
    }


async def _load_repo_or_404(db: AsyncSession, repo_id: uuid.UUID) -> Repository:
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")
    return repo


async def _require_host(db: AsyncSession, repo_id: uuid.UUID, user: User) -> None:
    """仅仓库所有者/管理员（会话发起人）可管理会话权限。"""
    if not await check_repository_owner_or_admin(db, repo_id, user.id):
        raise AuthorizationException(
            detail="仅仓库所有者/管理员可管理协作会话权限",
            error_code="collab_session_forbidden",
        )


def _require_doc_in_repo(doc_key: str, repo_id: uuid.UUID) -> None:
    parsed_repo_id, _branch, _path = parse_doc_key(doc_key)
    if parsed_repo_id != repo_id:
        raise ValidationException(
            detail="doc_key 不属于该仓库",
            error_code="collab_session_dockey_mismatch",
        )


@router.post("/{repo_id}/collab/sessions/permission")
async def set_session_permission(
    repo_id: uuid.UUID,
    data: SetPermissionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """改成员权限 / 清空覆盖（scope=null）。"""
    await _load_repo_or_404(db, repo_id)
    await _require_host(db, repo_id, current_user)
    _require_doc_in_repo(data.doc_key, repo_id)

    override = await set_permission(
        db, data.doc_key, data.user_id, data.scope, current_user.id
    )
    return _serialize(override)


@router.post("/{repo_id}/collab/sessions/kick")
async def kick_session_member(
    repo_id: uuid.UUID,
    data: KickRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """踢出成员：即时拒绝其后续鉴权与保存。"""
    await _load_repo_or_404(db, repo_id)
    await _require_host(db, repo_id, current_user)
    _require_doc_in_repo(data.doc_key, repo_id)

    override = await kick_member(db, data.doc_key, data.user_id, current_user.id)
    return _serialize(override)
