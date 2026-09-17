from typing import List, Literal, Optional
import uuid
import hmac
from fastapi import APIRouter, Depends, Query, Request, status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_prefix import get_route_prefix
from api.dependencies import get_current_user, security
from models.async_db import get_async_db
from models.repository import Repository
from models.user import User
from core.exception import NotFoundException
from services.build_service import BuildService
from services.webhook_service import generate_signature
from models.build_status import VALID_STATUSES
import uuid

router = APIRouter(prefix=get_route_prefix("builds"), tags=["builds"])


class CreateBuildRequest(BaseModel):
    branch: str = Field(..., min_length=1, max_length=255)
    commit_sha: str = Field(..., min_length=1, max_length=64)
    commit_message: Optional[str] = Field(None, max_length=1000)


class LogEntryIn(BaseModel):
    stream: Literal["stdout", "stderr"] = "stdout"
    line: str = Field(..., min_length=1, max_length=8000)


class UpdateBuildRequest(BaseModel):
    status: str = Field(..., pattern="|".join(VALID_STATUSES))
    details_url: Optional[str] = Field(None, max_length=512)
    logs: Optional[str] = Field(None)
    log_entries: Optional[List[LogEntryIn]] = Field(None, description="增量日志行，seq 按 build 自增")


class BuildResponse(BaseModel):
    id: uuid.UUID
    repo_id: uuid.UUID
    branch: str
    commit_sha: str
    commit_message: Optional[str]
    status: str
    triggered_by: uuid.UUID
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    details_url: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


async def _get_repo(repo_id: uuid.UUID, db: AsyncSession) -> Repository:
    from sqlalchemy import select
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found", error_code="repository_not_found")
    return repo


def _build_to_response(build) -> BuildResponse:
    return BuildResponse(
        id=build.id,
        repo_id=build.repo_id,
        branch=build.branch,
        commit_sha=build.commit_sha,
        commit_message=build.commit_message,
        status=build.status,
        triggered_by=build.triggered_by,
        started_at=build.started_at.isoformat() if build.started_at else None,
        finished_at=build.finished_at.isoformat() if build.finished_at else None,
        details_url=build.details_url,
        created_at=build.created_at.isoformat() if build.created_at else "",
    )


@router.post("/{repo_id}/builds", status_code=status.HTTP_201_CREATED)
async def create_build(
    repo_id: uuid.UUID,
    data: CreateBuildRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await _get_repo(repo_id, db)
    build = await BuildService.create_build(
        db=db,
        repo_id=repo_id,
        branch=data.branch,
        commit_sha=data.commit_sha,
        commit_message=data.commit_message,
        triggered_by=current_user.id,
    )
    return _build_to_response(build)


@router.get("/{repo_id}/builds")
async def list_builds(
    repo_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    branch: Optional[str] = Query(default=None, description="按分支过滤（PR 详情关联构建场景）"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="按状态过滤"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await _get_repo(repo_id, db)
    builds = await BuildService.get_builds_for_repository(
        db=db, repo_id=repo_id, limit=limit, offset=offset,
        branch=branch, status=status_filter,
    )
    return [_build_to_response(b) for b in builds]


@router.get("/{repo_id}/builds/{build_id}")
async def get_build(
    repo_id: uuid.UUID,
    build_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await _get_repo(repo_id, db)
    build = await BuildService.get_build(db=db, build_id=build_id)
    if build.repo_id != repo_id:
        raise NotFoundException(detail="Build not found", error_code="build_not_found")
    return _build_to_response(build)


@router.patch("/{repo_id}/builds/{build_id}")
async def update_build(
    repo_id: uuid.UUID,
    build_id: uuid.UUID,
    data: UpdateBuildRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    更新构建状态。

    外部 CI runner 无需用户 token: 通过 X-Perseus-Signature 头携带
    HMAC-SHA256 签名 (https://docs.github.com/webhooks/using-webhooks/validating-webhook-deliveries)
    回调; 否则回落到用户 token 鉴权 (F-046)。
    """
    repo = await _get_repo(repo_id, db)
    signature_header = request.headers.get("X-Perseus-Signature")
    if signature_header:
        if not repo.ci_secret:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CI callback signature not configured for repository",
            )
        raw_body = await request.body()
        expected = generate_signature(raw_body.decode("utf-8"), repo.ci_secret)
        if not hmac.compare_digest(signature_header, expected):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CI callback signature",
            )
    else:
        # 无签名头: 回落到用户 token 鉴权 (原行为)
        await get_current_user(credentials, db)

    build = await BuildService.update_build_status(
        db=db,
        build_id=build_id,
        status=data.status,
        details_url=data.details_url,
        logs=data.logs,
        log_entries=data.log_entries,
    )
    return _build_to_response(build)


@router.get("/{repo_id}/builds/{build_id}/logs")
async def get_build_logs(
    repo_id: uuid.UUID,
    build_id: uuid.UUID,
    after_seq: int = Query(default=0, ge=0, description="增量边界: 只返回 seq>after_seq 的日志行"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取构建日志

    - 兼容: 不带 after_seq 时返回整串 `logs`（旧行为），并附增量契约字段；
    - 增量: 带 `after_seq` 时按 build_log_entries 子表只回 `seq>after_seq` 的
      entries（逐条 seq/stream/line/logged_at），next_seq 为增量光标。

    Args:
        repo_id: 仓库ID
        build_id: 构建ID
        after_seq: 增量边界（只回大于该 seq 的条目，默认 0=全部）
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: {"logs": 整串兼容, "entries": [逐条], "next_seq": 增量光标}
    """
    await _get_repo(repo_id, db)
    build = await BuildService.get_build(db=db, build_id=build_id)
    if build.repo_id != repo_id:
        raise NotFoundException(detail="Build not found", error_code="build_not_found")

    # 增量契约: 从 build_log_entries 子表拉 seq>after_seq 的行（一次性或增量）
    entries, next_seq = await BuildService.get_build_log_entries_after_seq(
        db=db, build_id=build_id, after_seq=after_seq
    )
    # 兼容整串: 既有 build.logs 仍是权威整串快照（签名回调可能整串更新）
    return {
        "logs": build.logs or "",
        "entries": entries,
        "next_seq": next_seq,
    }
