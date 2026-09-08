from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from models.async_db import get_async_db
from models.user import User
from api.dependencies import get_current_user
from services.realtime.chat_service import ChatService
from services.realtime.room_service import RoomService
from core.exception import NotFoundException, ValidationException
import uuid


router = APIRouter(tags=["chat"])


@router.get("/api/v1/rooms/unread")
async def get_unread_counts(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await ChatService.get_unread_counts(db, current_user.id)


@router.post("/api/v1/rooms/{room_id}/read")
async def mark_room_read(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    success = await ChatService.mark_read(db, room_id, current_user.id)
    return {"success": success}


@router.get("/api/v1/rooms/{room_id}/messages")
async def get_room_messages(
    room_id: uuid.UUID,
    before: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    room = await RoomService.get_room(db, room_id)
    if not room:
        raise NotFoundException("Room not found", error_code="room_not_found")
    return await ChatService.get_messages(db, room_id, current_user.id, before=before, limit=limit)


@router.delete("/api/v1/rooms/{room_id}/messages/{msg_id}")
async def delete_message(
    room_id: uuid.UUID,
    msg_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    success = await ChatService.delete_message(db, msg_id, current_user.id)
    if not success:
        raise NotFoundException("Message not found", error_code="message_not_found")
    return {"success": True}


@router.post("/api/v1/rooms/{room_id}/messages/{msg_id}/reactions")
async def add_message_reaction(
    room_id: uuid.UUID,
    msg_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    emoji: str = (payload or {}).get("emoji") or ""
    return await ChatService.add_reaction(db, msg_id, current_user.id, emoji)


@router.delete("/api/v1/rooms/{room_id}/messages/{msg_id}/reactions")
async def remove_message_reaction(
    room_id: uuid.UUID,
    msg_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    emoji: str = (payload or {}).get("emoji") or ""
    return await ChatService.remove_reaction(db, msg_id, current_user.id, emoji)
