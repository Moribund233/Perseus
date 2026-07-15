import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.realtime_room import RealtimeRoom, RoomMember
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
            raise ValidationException(f"仓库 {repository_id} 已有关联房间")

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
                RealtimeRoom.is_active.is_(True)
            )
        )
        return list(result.scalars().all())

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
            raise ValidationException(f"无效的角色: {role}，有效值: {', '.join(sorted(VALID_ROLES))}")

        result = await db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValidationException("成员不存在")

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
