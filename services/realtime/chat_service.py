import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
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
    async def _get_room_or_raise(db: AsyncSession, room_id: uuid.UUID) -> RealtimeRoom:
        result = await db.execute(
            select(RealtimeRoom).filter(RealtimeRoom.id == room_id)
        )
        room = result.scalar_one_or_none()
        if not room:
            raise NotFoundException("房间不存在", error_code="room_not_found")
        if not room.is_active:
            raise ValidationException("房间已关闭", error_code="room_closed")
        return room

    @staticmethod
    async def _check_membership(db: AsyncSession, room_id: uuid.UUID, user_id: uuid.UUID) -> None:
        result = await db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id
            )
        )
        if not result.scalar_one_or_none():
            raise ValidationException("你不是该房间的成员", error_code="room_not_member")

    @staticmethod
    async def _ensure_membership(db: AsyncSession, room_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        校验房间访问权限, 已是成员直接放行; 否则按仓库访问权限自动加入房间.

        REST 层没有加入房间的端点, 若仅按 RoomMember 硬性校验,
        仓库可见的用户永远无法进入房间; 房间归属仓库, 因此以仓库
        访问权限 (公开 / 所有者 / 仓库成员) 作为自动加入的依据.
        """
        from models.repository import Repository
        from models.repository_member import RepositoryMember

        existing = await db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id
            )
        )
        if existing.scalar_one_or_none():
            return

        room = await ChatService._get_room_or_raise(db, room_id)
        if room.repository_id is None:
            # 私聊房间无仓库访问判定, 仅允许显式加入的 DM 成员
            raise ValidationException("你不是该房间的成员", error_code="room_not_member")

        repo_result = await db.execute(
            select(Repository).filter(Repository.id == room.repository_id)
        )
        repo = repo_result.scalar_one_or_none()
        if repo is None:
            raise NotFoundException("房间不存在", error_code="room_not_found")

        has_access = repo.is_public or repo.owner_id == user_id
        if not has_access:
            member_result = await db.execute(
                select(RepositoryMember).filter(
                    RepositoryMember.repository_id == repo.id,
                    RepositoryMember.user_id == user_id,
                    RepositoryMember.is_active.is_(True)
                )
            )
            has_access = member_result.scalar_one_or_none() is not None
        if not has_access:
            raise ValidationException("你不是该房间的成员", error_code="room_not_member")

        db.add(RoomMember(
            room_id=room_id,
            user_id=user_id,
            role="member",
            joined_at=datetime.now(timezone.utc),
        ))
        await db.commit()

    @staticmethod
    async def send_message(
        db: AsyncSession,
        room_id: uuid.UUID,
        sender_id: uuid.UUID,
        content: str,
        message_type: str = "text",
        reply_to: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        if not content or not content.strip():
            raise ValidationException("消息内容不能为空", error_code="message_content_required")
        content = content.strip()[:MAX_CONTENT_LENGTH]

        await ChatService._get_room_or_raise(db, room_id)
        await ChatService._ensure_membership(db, room_id, sender_id)

        msg = ChatMessage(
            room_id=room_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            reply_to_id=reply_to,
            created_at=datetime.now(timezone.utc),
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)

        return await ChatService._format_message(db, msg, sender_id)

    @staticmethod
    async def get_unread_counts(db: AsyncSession, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        返回用户所在所有房间的未读计数列表.

        未读 = 房间内 created_at > 本人 last_read_at 且非本人发送、非已删除的消息数.
        新成员 (last_read_at 为空) 视为已读, 历史消息不计入未读.
        """
        member_result = await db.execute(
            select(RealtimeRoom)
            .join(RoomMember, RoomMember.room_id == RealtimeRoom.id)
            .filter(
                RoomMember.user_id == user_id,
                RealtimeRoom.is_active.is_(True),
            )
        )
        rooms = member_result.scalars().all()

        unread_query = (
            select(
                ChatMessage.room_id.label("room_id"),
                func.count(ChatMessage.id).label("unread_count"),
            )
            .join(RoomMember, RoomMember.room_id == ChatMessage.room_id)
            .filter(
                RoomMember.user_id == user_id,
                RoomMember.is_muted.is_(False),
                ChatMessage.sender_id != user_id,
                ChatMessage.message_type != "system",
                RoomMember.last_read_at.isnot(None),
                ChatMessage.created_at > RoomMember.last_read_at,
            )
            .group_by(ChatMessage.room_id)
        )
        unread_result = await db.execute(unread_query)
        unread_map = {str(row.room_id): row.unread_count for row in unread_result.all()}

        return [
            {
                "room_id": room.id,
                "repository_id": room.repository_id,
                "room_name": room.name,
                "unread_count": unread_map.get(str(room.id), 0),
            }
            for room in rooms
        ]

    @staticmethod
    async def mark_read(db: AsyncSession, room_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """将某房间在本人视角标记为已读 (水位 = 当前时间)."""
        await ChatService._ensure_membership(db, room_id, user_id)
        result = await db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise NotFoundException("你不是该房间的成员", error_code="message_room_membership")
        member.last_read_at = datetime.now(timezone.utc)
        await db.commit()
        return True

    @staticmethod
    async def _format_message(db: AsyncSession, msg: ChatMessage, current_user: Optional[uuid.UUID] = None) -> Dict[str, Any]:
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
            "reactions": ChatService._format_reactions(msg, current_user),
        }

    @staticmethod
    def _reaction_map(msg: ChatMessage) -> Dict[str, list]:
        meta = msg.metadata_ or {}
        reactions = meta.get("reactions")
        if not isinstance(reactions, dict):
            return {}
        return reactions

    @staticmethod
    def _format_reactions(msg: ChatMessage, current_user: Optional[uuid.UUID] = None) -> List[Dict[str, Any]]:
        """将 metadata_.reactions 原始映射整理为前端渲染结构."""
        reactions = ChatService._reaction_map(msg)
        return [
            {
                "emoji": emoji,
                "count": len(user_ids),
                "active": current_user is not None and str(current_user) in {str(u) for u in user_ids},
            }
            for emoji, user_ids in reactions.items()
            if user_ids
        ]

    @staticmethod
    async def add_reaction(
        db: AsyncSession,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        emoji: str
    ) -> Dict[str, Any]:
        emoji = (emoji or "").strip()
        if not emoji or len(emoji) > 8:
            raise ValidationException("表情不合法", error_code="invalid_emoji")

        result = await db.execute(
            select(ChatMessage).filter(ChatMessage.id == message_id)
        )
        msg = result.scalar_one_or_none()
        if not msg:
            raise NotFoundException("消息不存在", error_code="message_not_found")

        meta = dict(msg.metadata_ or {})
        reactions = meta.get("reactions")
        if not isinstance(reactions, dict):
            reactions = {}
        user_ids = reactions.setdefault(emoji, [])
        current = str(user_id)
        if current in {str(u) for u in user_ids}:
            raise ValidationException("你已回应过该表情", error_code="reaction_duplicate")
        user_ids.append(current)
        meta["reactions"] = reactions
        msg.metadata_ = meta
        await db.commit()
        await db.refresh(msg)
        return await ChatService._format_message(db, msg, user_id)

    @staticmethod
    async def remove_reaction(
        db: AsyncSession,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        emoji: str
    ) -> Dict[str, Any]:
        result = await db.execute(
            select(ChatMessage).filter(ChatMessage.id == message_id)
        )
        msg = result.scalar_one_or_none()
        if not msg:
            raise NotFoundException("消息不存在", error_code="message_not_found")

        meta = dict(msg.metadata_ or {})
        reactions = meta.get("reactions")
        if not isinstance(reactions, dict):
            return await ChatService._format_message(db, msg, user_id)

        user_ids = reactions.get(emoji, [])
        current = str(user_id)
        if current not in {str(u) for u in user_ids}:
            return await ChatService._format_message(db, msg, user_id)

        reactions[emoji] = [u for u in user_ids if str(u) != current]
        if not reactions[emoji]:
            del reactions[emoji]
        meta["reactions"] = reactions
        msg.metadata_ = meta
        await db.commit()
        await db.refresh(msg)
        return await ChatService._format_message(db, msg, user_id)

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        room_id: uuid.UUID,
        user_id: uuid.UUID,
        before: Optional[uuid.UUID] = None,
        limit: int = DEFAULT_PAGE_LIMIT,
        q: Optional[str] = None
    ) -> Dict[str, Any]:
        await ChatService._get_room_or_raise(db, room_id)
        await ChatService._ensure_membership(db, room_id, user_id)

        limit = min(limit, MAX_PAGE_LIMIT)

        query = (
            select(ChatMessage)
            .options(selectinload(ChatMessage.sender))
            .filter(ChatMessage.room_id == room_id)
            .order_by(desc(ChatMessage.created_at), desc(ChatMessage.id))
            .limit(limit + 1)
        )

        if q and q.strip():
            query = query.filter(ChatMessage.content.ilike(f"%{q.strip()}%"))

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
                "reactions": ChatService._format_reactions(msg, user_id),
            })

        next_before = rows[-1].id if rows else None
        return {
            "messages": messages,
            "has_more": has_more,
            "next_before": next_before if has_more else None,
        }

    @staticmethod
    async def search_messages(
        db: AsyncSession,
        user_id: uuid.UUID,
        q: str,
        limit: int = DEFAULT_PAGE_LIMIT
    ) -> Dict[str, Any]:
        """跨会话消息检索：仅搜索当前用户已加入且处于活跃状态的房间."""
        q = (q or "").strip()
        if not q:
            raise ValidationException("搜索关键词不能为空", error_code="search_query_required")
        limit = min(limit, MAX_PAGE_LIMIT)

        query = (
            select(
                ChatMessage,
                RealtimeRoom.id.label("room_id_value"),
                RealtimeRoom.name.label("room_name"),
                RealtimeRoom.room_type.label("room_type"),
                RealtimeRoom.repository_id.label("repository_id"),
            )
            .join(RoomMember, RoomMember.room_id == ChatMessage.room_id)
            .join(RealtimeRoom, RealtimeRoom.id == RoomMember.room_id)
            .options(selectinload(ChatMessage.sender))
            .filter(
                RoomMember.user_id == user_id,
                RealtimeRoom.is_active.is_(True),
                ChatMessage.message_type != "system",
                ChatMessage.content.ilike(f"%{q}%"),
            )
            .order_by(desc(ChatMessage.created_at), desc(ChatMessage.id))
            .limit(limit)
        )

        result = await db.execute(query)
        rows = result.all()

        messages = []
        for msg, room_id_value, room_name, room_type, repo_id in rows:
            messages.append({
                "id": msg.id,
                "room_id": room_id_value,
                "room_name": room_name,
                "room_type": room_type,
                "repository_id": repo_id,
                "sender_id": msg.sender_id,
                "sender_username": msg.sender.username if msg.sender else "unknown",
                "message_type": msg.message_type,
                "content": msg.content,
                "reply_to": msg.reply_to_id,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "reactions": ChatService._format_reactions(msg, user_id),
            })

        return {"messages": messages}

    @staticmethod
    async def edit_message(
        db: AsyncSession,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        new_content: str
    ) -> Dict[str, Any]:
        result = await db.execute(
            select(ChatMessage).filter(ChatMessage.id == message_id)
        )
        msg = result.scalar_one_or_none()
        if not msg:
            raise NotFoundException("消息不存在", error_code="message_not_found")
        if msg.sender_id != user_id:
            raise ValidationException("只能编辑自己的消息", error_code="message_edit_own_only")
        if not new_content or not new_content.strip():
            raise ValidationException("消息内容不能为空", error_code="message_content_required")

        msg.content = new_content.strip()[:MAX_CONTENT_LENGTH]
        msg.edited_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(msg)
        return await ChatService._format_message(db, msg, user_id)

    @staticmethod
    async def delete_message(
        db: AsyncSession,
        message_id: uuid.UUID,
        user_id: uuid.UUID
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
                raise ValidationException("没有权限删除此消息", error_code="message_delete_forbidden")

        msg.content = "[deleted]"
        msg.message_type = "system"
        await db.commit()
        return True
