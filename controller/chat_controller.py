from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from models.async_db import get_async_db
from models.user import User
from api.dependencies import get_current_user
from services.realtime.chat_service import ChatService
from services.realtime.room_service import RoomService
from core.exception import NotFoundException, ValidationException


router = APIRouter(tags=["chat"])


@router.get("/api/v1/rooms/{room_id}/messages")
async def get_room_messages(
    room_id: int,
    before: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    room = await RoomService.get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    try:
        result = await ChatService.get_messages(db, room_id, current_user.id, before=before, limit=limit)
        return result
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)


@router.delete("/api/v1/rooms/{room_id}/messages/{msg_id}")
async def delete_message(
    room_id: int,
    msg_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    try:
        success = await ChatService.delete_message(db, msg_id, current_user.id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        return {"success": True}
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)
