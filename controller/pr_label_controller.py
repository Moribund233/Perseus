"""Pull Request 标签控制器"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models.user import User
from api.dependencies import get_current_user
from services import pr_label_service
from utils.permission_utils import require_repository_owner_or_admin
import uuid

router = APIRouter(prefix=get_route_prefix("repositories"), tags=["pr-labels"])


@router.get("/{repo_id}/pr-labels")
async def get_labels(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await pr_label_service.get_labels(repo_id, db)


@router.post("/{repo_id}/pr-labels", status_code=201)
async def create_label(
    repo_id: uuid.UUID,
    data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await require_repository_owner_or_admin(db, repo_id, current_user.id, "create PR labels")
    return await pr_label_service.create_label(repo_id, data, db)


@router.put("/{repo_id}/pr-labels/{label_id}")
async def update_label(
    repo_id: uuid.UUID,
    label_id: uuid.UUID,
    data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await require_repository_owner_or_admin(db, repo_id, current_user.id, "update PR labels")
    return await pr_label_service.update_label(repo_id, label_id, data, db)


@router.delete("/{repo_id}/pr-labels/{label_id}")
async def delete_label(
    repo_id: uuid.UUID,
    label_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await require_repository_owner_or_admin(db, repo_id, current_user.id, "delete PR labels")
    return await pr_label_service.delete_label(repo_id, label_id, db)


@router.post("/pull-requests/{pr_id}/labels/{label_id}")
async def add_label_to_pr(
    pr_id: uuid.UUID,
    label_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await pr_label_service.add_label_to_pr(pr_id, label_id, db)


@router.delete("/pull-requests/{pr_id}/labels/{label_id}")
async def remove_label_from_pr(
    pr_id: uuid.UUID,
    label_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await pr_label_service.remove_label_from_pr(pr_id, label_id, db)


@router.get("/pr-labels/{label_id}/pull-requests")
async def get_prs_by_label(
    label_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await pr_label_service.get_prs_by_label(label_id, db)
