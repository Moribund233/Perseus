from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from api.dependencies import get_current_user
from models.async_db import get_async_db
from models.repository import Repository
from models.user import User
from core.exception import NotFoundException
from services.build_service import BuildService
from models.build_status import VALID_STATUSES

router = APIRouter(prefix=get_route_prefix("builds"), tags=["builds"])


class CreateBuildRequest(BaseModel):
    branch: str = Field(..., min_length=1, max_length=255)
    commit_sha: str = Field(..., min_length=1, max_length=64)
    commit_message: Optional[str] = Field(None, max_length=1000)


class UpdateBuildRequest(BaseModel):
    status: str = Field(..., pattern="|".join(VALID_STATUSES))
    details_url: Optional[str] = Field(None, max_length=512)
    logs: Optional[str] = Field(None)


class BuildResponse(BaseModel):
    id: int
    repo_id: int
    branch: str
    commit_sha: str
    commit_message: Optional[str]
    status: str
    triggered_by: int
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    details_url: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


async def _get_repo(repo_id: int, db: AsyncSession) -> Repository:
    from sqlalchemy import select
    result = await db.execute(select(Repository).filter(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found")
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
    repo_id: int,
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
    repo_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await _get_repo(repo_id, db)
    builds = await BuildService.get_builds_for_repository(
        db=db, repo_id=repo_id, limit=limit, offset=offset
    )
    return [_build_to_response(b) for b in builds]


@router.get("/{repo_id}/builds/{build_id}")
async def get_build(
    repo_id: int,
    build_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await _get_repo(repo_id, db)
    build = await BuildService.get_build(db=db, build_id=build_id)
    if build.repo_id != repo_id:
        raise NotFoundException(detail="Build not found")
    return _build_to_response(build)


@router.patch("/{repo_id}/builds/{build_id}")
async def update_build(
    repo_id: int,
    build_id: int,
    data: UpdateBuildRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await _get_repo(repo_id, db)
    build = await BuildService.update_build_status(
        db=db,
        build_id=build_id,
        status=data.status,
        details_url=data.details_url,
        logs=data.logs,
    )
    return _build_to_response(build)


@router.get("/{repo_id}/builds/{build_id}/logs")
async def get_build_logs(
    repo_id: int,
    build_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取构建日志

    Args:
        repo_id: 仓库ID
        build_id: 构建ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        dict: 构建日志文本
    """
    await _get_repo(repo_id, db)
    build = await BuildService.get_build(db=db, build_id=build_id)
    if build.repo_id != repo_id:
        raise NotFoundException(detail="Build not found")
    return {"logs": build.logs or ""}
