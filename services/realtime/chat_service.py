from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from models.chat_message import ChatMessage
from models.realtime_room import RealtimeRoom, RoomMember
from models.user import User
from core.exception import ValidationException, NotFoundException

MAX_CONTENT_LENGTH = 10000
MAX_PAGE_LIMIT = 100
DEFAULT_PAGE_LIMIT = 50


class ChatService:

    @staticmethod
    async def _get_room_or_raise(db: AsyncSession, room_id: int) -> RealtimeRoom:
        result = await db.execute(
            select(RealtimeRoom).filter(RealtimeRoom.id == room_id)
        )
        room = result.scalar_one_or_none()
        if not room:
            raise NotFoundException("房间不存在")
        if not room.is_active:
            raise ValidationException("房间已关闭")
        return room

    @staticmethod
    async def _check_membership(db: AsyncSession, room_id: int, user_id: int) -> None:
        result = await db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id
            )
        )
        if not result.scalar_one_or_none():
            raise ValidationException("你不是该房间的成员")

    @staticmethod
    async def send_message(
        db: AsyncSession,
        room_id: int,
        sender_id: int,
        content: str,
        message_type: str = "text",
        reply_to: Optional[int] = None
    ) -> Dict[str, Any]:
        if not content or not content.strip():
            raise ValidationException("消息内容不能为空")
        content = content.strip()[:MAX_CONTENT_LENGTH]

        await ChatService._get_room_or_raise(db, room_id)
        await ChatService._check_membership(db, room_id, sender_id)

        msg = ChatMessage(
            room_id=room_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            reply_to_id=reply_to,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)

        return await ChatService._format_message(db, msg)

    @staticmethod
    async def _format_message(db: AsyncSession, msg: ChatMessage) -> Dict[str, Any]:
        result = await db.execute(
            select(User).filter(User.id == msg.sender_id)
        )
        sender = result.scalar_one_or_none()
        return {
            "id": msg.id,
            "room_id": msg.room_id,
            "sender_id": msg.sender_id,
            "sender_username": sender.username if sender else "unknown",
            "message_type": msg.message_type,
            "content": msg.content,
            "reply_to": msg.reply_to_id,
            "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        room_id: int,
        user_id: int,
        before: Optional[int] = None,
        limit: int = DEFAULT_PAGE_LIMIT
    ) -> Dict[str, Any]:
        await ChatService._get_room_or_raise(db, room_id)
        await ChatService._check_membership(db, room_id, user_id)

        limit = min(limit, MAX_PAGE_LIMIT)

        query = (
            select(ChatMessage)
            .options(selectinload(ChatMessage.sender))
            .filter(ChatMessage.room_id == room_id)
            .order_by(desc(ChatMessage.created_at), desc(ChatMessage.id))
            .limit(limit + 1)
        )

        if before is not None:
            result = await db.execute(
                select(ChatMessage.created_at, ChatMessage.id).filter(ChatMessage.id == before)
            )
            row = result.one_or_none()
            if row:
                before_ts, before_id = row
                query = query.filter(
                    (ChatMessage.created_at < before_ts) |
                    ((ChatMessage.created_at == before_ts) & (ChatMessage.id < before_id))
                )

        result = await db.execute(query)
        rows = list(result.scalars().all())

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        messages = []
        for msg in rows:
            messages.append({
                "id": msg.id,
                "room_id": msg.room_id,
                "sender_id": msg.sender_id,
                "sender_username": msg.sender.username if msg.sender else "unknown",
                "message_type": msg.message_type,
                "content": msg.content,
                "reply_to": msg.reply_to_id,
                "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            })

        next_before = rows[-1].id if rows else None
        return {
            "messages": messages,
            "has_more": has_more,
            "next_before": next_before if has_more else None,
        }

    @staticmethod
    async def edit_message(
        db: AsyncSession,
        message_id: int,
        user_id: int,
        new_content: str
    ) -> Dict[str, Any]:
        result = await db.execute(
            select(ChatMessage).filter(ChatMessage.id == message_id)
        )
        msg = result.scalar_one_or_none()
        if not msg:
            raise NotFoundException("消息不存在")
        if msg.sender_id != user_id:
            raise ValidationException("只能编辑自己的消息")
        if not new_content or not new_content.strip():
            raise ValidationException("消息内容不能为空")

        msg.content = new_content.strip()[:MAX_CONTENT_LENGTH]
        msg.edited_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(msg)
        return await ChatService._format_message(db, msg)

    @staticmethod
    async def delete_message(
        db: AsyncSession,
        message_id: int,
        user_id: int
    ) -> bool:
        result = await db.execute(
            select(ChatMessage).filter(ChatMessage.id == message_id)
        )
        msg = result.scalar_one_or_none()
        if not msg:
            return False

        is_owner = msg.sender_id == user_id
        if not is_owner:
            member_result = await db.execute(
                select(RoomMember).filter(
                    RoomMember.room_id == msg.room_id,
                    RoomMember.user_id == user_id,
                    RoomMember.role == "admin"
                )
            )
            is_admin = member_result.scalar_one_or_none() is not None
            if not is_admin:
                raise ValidationException("没有权限删除此消息")

        msg.content = "[deleted]"
        msg.message_type = "system"
        await db.commit()
        return True
