"""
协作邀请链接控制器

POST /{repo_id}/collab/invites — 由仓库成员签发短时邀请 token
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_prefix import get_route_prefix
from api.dependencies import get_current_user
from models.async_db import get_async_db
from models import Repository, User
from core.exception import AuthorizationException, NotFoundException, ValidationException
from controller.collab_internal_controller import READ_ROLES, parse_doc_key
from services.collab_invite_service import (
    MAX_TTL_MINUTES,
    create_invite_token,
)
from utils.permission_utils import check_repository_permission

router = APIRouter(prefix=get_route_prefix("repositories"), tags=["collab-invites"])


class IssueInviteRequest(BaseModel):
    """邀请链接签发请求体"""
    doc_key: str = Field(..., min_length=1, description="文档标识 repository_id:branch:path")
    scope: str = Field("read", pattern="read|write", description="权限档位")
    ttl_minutes: Optional[int] = Field(None, ge=1, le=MAX_TTL_MINUTES, description="有效期(分钟)")


@router.post("/{repo_id}/collab/invites", status_code=201)
async def issue_collab_invite(
    repo_id: uuid.UUID,
    data: IssueInviteRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    签发协作会话邀请链接 (仅仓库成员)

    被邀请人凭 token 获得会话级临时权限 (绑定 docKey + read/write 档位 + 过期时间)。
    """
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")

    if not await check_repository_permission(db, repo_id, current_user.id, READ_ROLES):
        raise AuthorizationException(
            detail="仅仓库成员可生成协作邀请链接",
            error_code="collab_invite_forbidden",
        )

    parsed_repo_id, _branch, _path = parse_doc_key(data.doc_key)
    if parsed_repo_id != repo_id:
        raise ValidationException(
            detail="doc_key 不属于该仓库",
            error_code="collab_invite_dockey_mismatch",
        )

    issued = create_invite_token(
        doc_key=data.doc_key,
        scope=data.scope,
        issued_by=current_user.id,
        username=current_user.username,
        ttl_minutes=data.ttl_minutes,
    )
    issued["url"] = f"/collab/{issued['token']}"
    return issued
