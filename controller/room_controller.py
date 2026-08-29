from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models.user import User
from models.repository import Repository
from api.dependencies import get_current_user, get_current_admin_user
from services.realtime.room_service import RoomService
from services.repository_service import get_repository_by_id
from services.attachment_service import upload_attachment, get_attachment_file
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


@router.post("/api/v1/rooms/{room_id}/attachments")
async def upload_room_attachment(
    room_id: uuid.UUID,
    file: UploadFile = File(..., description="附件文件（最大 20MB）"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    上传聊天附件

    仅房间成员可上传；返回的 url 可直接作为 Markdown 链接/图片插入消息内容
    """
    room = await RoomService.get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    members = await RoomService.get_members(db, room_id)
    member_ids = {str(m["user_id"]) if isinstance(m, dict) else str(m.user_id) for m in members}
    if str(current_user.id) not in member_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this room")

    return await upload_attachment(room_id, file)


@router.get("/api/v1/attachments/{room_id}/{stored_name}")
async def download_room_attachment(
    room_id: uuid.UUID,
    stored_name: str,
    current_user: User = Depends(get_current_user),
):
    """下载聊天附件（需认证，文件名含随机 token 防遍历/猜测）"""
    file_path, content_type = await get_attachment_file(room_id, stored_name)
    return FileResponse(path=str(file_path), media_type=content_type, filename=stored_name.split("_", 1)[1])
