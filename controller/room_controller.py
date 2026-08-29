from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models.user import User
from models.repository import Repository
from api.dependencies import get_current_user, get_current_admin_user
from services.realtime.room_service import RoomService
from services.repository_service import get_repository_by_id
from core.exception import ValidationException
import uuid


router = APIRouter(tags=["rooms"])


@router.get("/api/v1/repositories/{repo_id}/room")
async def get_repository_room(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    room = await RoomService.get_repository_room(db, repo_id)
    if not room:
        # Fork/历史数据等路径不会创建房间, 按需补建保证仓库始终有频道
        repo = await get_repository_by_id(repo_id, db)
        if not repo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
        try:
            room = await RoomService.create_room(db, repo_id, repo["name"], current_user.id)
        except ValidationException:
            # 并发请求已创建
            room = await RoomService.get_repository_room(db, repo_id)
            if not room:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return {
        "id": room.id,
        "repository_id": room.repository_id,
        "name": room.name,
        "topic": room.topic,
        "is_active": room.is_active,
        "created_at": room.created_at.isoformat() if room.created_at else None,
    }


@router.get("/api/v1/rooms/{room_id}/members")
async def get_room_members(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    room = await RoomService.get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    members = await RoomService.get_members(db, room_id)
    return members


@router.delete("/api/v1/rooms/{room_id}")
async def delete_room(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_admin_user)
):
    room = await RoomService.get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    success = await RoomService.delete_room(db, room_id)
    return {"success": success}
