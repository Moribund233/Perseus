"""
DM 私聊控制器

私聊会话(room_type="dm")的获取/创建与列表, 消息收发复用既有房间接口
(`GET /rooms/{room_id}/messages`、`POST /rooms/{room_id}/messages/...`)。
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from api.routes_prefix import API_V1_PREFIX
from models.async_db import get_async_db
from models.user import User
from api.dependencies import get_current_user
from services.realtime.room_service import RoomService
from services.realtime.chat_service import ChatService

router = APIRouter(prefix=f"{API_V1_PREFIX}/dm", tags=["dm"])


class DMCreateRequest(BaseModel):
    """创建/获取私聊会话请求体"""
    peer_user_id: uuid.UUID = Field(..., description="私聊对象用户ID")


def _room_to_dict(room):
    return {
        "id": room.id,
        "repository_id": room.repository_id,
        "name": room.name,
        "topic": room.topic,
        "room_type": room.room_type,
        "is_active": room.is_active,
        "created_at": room.created_at.isoformat() if room.created_at else None,
    }


@router.post("", status_code=201)
async def get_or_create_dm(
    data: DMCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取或创建当前用户与 peer_user_id 的私聊会话（幂等）"""
    room = await RoomService.get_or_create_dm_room(db, current_user.id, data.peer_user_id)
    return _room_to_dict(room)


@router.get("")
async def list_dms(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """列出当前用户的私聊会话（含对方信息与未读数）"""
    dms = await RoomService.list_dm_rooms(db, current_user.id)
    unread = await ChatService.get_unread_counts(db, current_user.id)
    unread_map = {str(u["room_id"]): u["unread_count"] for u in unread}
    for dm in dms:
        dm["unread_count"] = unread_map.get(str(dm["room_id"]), 0)
    return dms