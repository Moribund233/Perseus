import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.realtime_room import RealtimeRoom, RoomMember, DirectMessage
from models.user import User
from core.exception import ValidationException


VALID_ROLES = {"member", "admin"}


class RoomService:

    @staticmethod
    async def create_room(
        db: AsyncSession,
        repository_id: uuid.UUID,
        name: str,
        created_by_user_id: uuid.UUID
    ) -> RealtimeRoom:
        existing = await RoomService.get_repository_room(db, repository_id)
        if existing:
            raise ValidationException(f"仓库 {repository_id} 已有关联房间", error_code="room_already_exists")

        room = RealtimeRoom(
            repository_id=repository_id,
            name=name,
            is_active=True
        )
        db.add(room)
        await db.commit()
        await db.refresh(room)

        member = RoomMember(
            room_id=room.id,
            user_id=created_by_user_id,
            role="admin",
            joined_at=datetime.now(timezone.utc),
            last_read_at=datetime.now(timezone.utc),
        )
        db.add(member)
        await db.commit()

        return room

    @staticmethod
    async def get_room(db: AsyncSession, room_id: uuid.UUID) -> Optional[RealtimeRoom]:
        result = await db.execute(
            select(RealtimeRoom).filter(RealtimeRoom.id == room_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_repository_room(db: AsyncSession, repository_id: uuid.UUID) -> Optional[RealtimeRoom]:
        result = await db.execute(
            select(RealtimeRoom).filter(
                RealtimeRoom.repository_id == repository_id,
                RealtimeRoom.is_active.is_(True)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_rooms(db: AsyncSession, user_id: uuid.UUID) -> List[RealtimeRoom]:
        result = await db.execute(
            select(RealtimeRoom)
            .join(RoomMember, RoomMember.room_id == RealtimeRoom.id)
            .filter(
                RoomMember.user_id == user_id,
                RealtimeRoom.is_active.is_(True),
                RealtimeRoom.room_type == "repository",
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_or_create_dm_room(
        db: AsyncSession,
        user_a_id: uuid.UUID,
        user_b_id: uuid.UUID
    ) -> RealtimeRoom:
        """获取或创建两个用户之间的私聊会话（幂等，任一发起方向命中同一会话）."""
        if user_a_id == user_b_id:
            raise ValidationException("不能与自己建立私聊会话", error_code="dm_self_chat_forbidden")

        result = await db.execute(
            select(User).filter(User.id.in_([user_a_id, user_b_id]))
        )
        users = result.scalars().all()
        if len(users) != 2:
            raise ValidationException("私聊用户不存在", error_code="dm_user_not_found")
        user_map = {u.id: u for u in users}

        a, b = sorted([user_a_id, user_b_id], key=str)
        dm_result = await db.execute(
            select(DirectMessage)
            .options(selectinload(DirectMessage.room))
            .filter(
                DirectMessage.user_a_id == a,
                DirectMessage.user_b_id == b,
            )
        )
        existing = dm_result.scalar_one_or_none()
        if existing and existing.room and existing.room.is_active:
            return existing.room

        room = RealtimeRoom(
            repository_id=None,
            name=f"{user_map[user_a_id].username} & {user_map[user_b_id].username}",
            is_active=True,
            room_type="dm",
        )
        db.add(room)
        await db.flush()

        dm = DirectMessage(
            room_id=room.id,
            user_a_id=a,
            user_b_id=b,
        )
        db.add(dm)

        now = datetime.now(timezone.utc)
        db.add(RoomMember(
            room_id=room.id,
            user_id=user_a_id,
            role="member",
            joined_at=now,
            last_read_at=now,
        ))
        db.add(RoomMember(
            room_id=room.id,
            user_id=user_b_id,
            role="member",
            joined_at=now,
            last_read_at=now,
        ))
        await db.commit()
        await db.refresh(room)
        return room

    @staticmethod
    async def list_dm_rooms(db: AsyncSession, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """列出当前用户参与的私聊会话（含对方信息）."""
        result = await db.execute(
            select(DirectMessage)
            .options(
                selectinload(DirectMessage.room),
                selectinload(DirectMessage.user_a),
                selectinload(DirectMessage.user_b),
            )
            .filter(
                (DirectMessage.user_a_id == user_id) | (DirectMessage.user_b_id == user_id)
            )
            .order_by(DirectMessage.created_at.desc())
        )
        rows = result.scalars().all()

        items = []
        for dm in rows:
            room = dm.room
            if not room or not room.is_active:
                continue
            peer = dm.user_b if dm.user_a_id == user_id else dm.user_a
            items.append({
                "room_id": room.id,
                "room_name": room.name,
                "room_type": room.room_type,
                "peer_user_id": peer.id,
                "peer_username": peer.username,
                "created_at": room.created_at.isoformat() if room.created_at else None,
            })
        return items

    @staticmethod
    async def join_room(db: AsyncSession, room_id: uuid.UUID, user_id: uuid.UUID) -> RoomMember:
        result = await db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        member = RoomMember(
            room_id=room_id,
            user_id=user_id,
            role="member",
            joined_at=datetime.now(timezone.utc),
            last_read_at=datetime.now(timezone.utc),
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return member

    @staticmethod
    async def leave_room(db: AsyncSession, room_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return False
        await db.delete(member)
        await db.commit()
        return True

    @staticmethod
    async def get_members(db: AsyncSession, room_id: uuid.UUID) -> List[Dict[str, Any]]:
        result = await db.execute(
            select(RoomMember)
            .options(selectinload(RoomMember.user))
            .filter(RoomMember.room_id == room_id)
        )
        members = result.scalars().all()
        return [
            {
                "id": m.id,
                "room_id": m.room_id,
                "user_id": m.user_id,
                "username": m.user.username,
                "role": m.role,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
                "is_muted": m.is_muted,
            }
            for m in members
        ]

    @staticmethod
    async def update_member_role(
        db: AsyncSession,
        room_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str
    ) -> RoomMember:
        if role not in VALID_ROLES:
            raise ValidationException(f"无效的角色: {role}，有效值: {', '.join(sorted(VALID_ROLES))}", error_code="room_invalid_role")

        result = await db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValidationException("成员不存在", error_code="room_member_not_found")

        member.role = role
        await db.commit()
        await db.refresh(member)
        return member

    @staticmethod
    async def remove_member(db: AsyncSession, room_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return False
        await db.delete(member)
        await db.commit()
        return True

    @staticmethod
    async def delete_room(db: AsyncSession, room_id: uuid.UUID) -> bool:
        result = await db.execute(
            select(RealtimeRoom).filter(RealtimeRoom.id == room_id)
        )
        room = result.scalar_one_or_none()
        if not room:
            return False
        room.is_active = False
        await db.commit()
        return True
