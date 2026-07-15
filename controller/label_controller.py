from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models.user import User
from api.dependencies import get_current_user
from services import label_service
from utils.permission_utils import require_repository_owner_or_admin
import uuid

router = APIRouter(prefix=get_route_prefix("repositories"), tags=["repo-labels"])


@router.get("/{repo_id}/labels")
async def get_labels(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await label_service.get_labels(repo_id, db)


@router.post("/{repo_id}/labels", status_code=201)
async def create_label(
    repo_id: uuid.UUID,
    label_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await require_repository_owner_or_admin(db, repo_id, current_user.id, "create labels")
    return await label_service.create_label(repo_id, label_data, db)


@router.put("/{repo_id}/labels/{label_id}")
async def update_label(
    repo_id: uuid.UUID,
    label_id: uuid.UUID,
    label_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await require_repository_owner_or_admin(db, repo_id, current_user.id, "update labels")
    return await label_service.update_label(repo_id, label_id, label_data, db)


@router.delete("/{repo_id}/labels/{label_id}")
async def delete_label(
    repo_id: uuid.UUID,
    label_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await require_repository_owner_or_admin(db, repo_id, current_user.id, "delete labels")
    return await label_service.delete_label(repo_id, label_id, db)


@router.post("/{repo_id}/labels/{label_id}/add")
async def add_label_to_repository(
    repo_id: uuid.UUID,
    label_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await require_repository_owner_or_admin(db, repo_id, current_user.id, "manage labels")
    return await label_service.add_label_to_repository(repo_id, label_id, db)


@router.post("/{repo_id}/labels/{label_id}/remove")
async def remove_label_from_repository(
    repo_id: uuid.UUID,
    label_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    await require_repository_owner_or_admin(db, repo_id, current_user.id, "manage labels")
    return await label_service.remove_label_from_repository(repo_id, label_id, db)
