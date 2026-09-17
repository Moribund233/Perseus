"""
F-203 DM 私聊 — Service 层异步测试
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.repository import Repository
from services.realtime.room_service import RoomService
from services.realtime.chat_service import ChatService
from core.exception import ValidationException


@pytest.mark.asyncio
async def test_dm_room_creation(async_db: AsyncSession, async_test_user: User, async_test_user2: User):
    room = await RoomService.get_or_create_dm_room(async_db, async_test_user.id, async_test_user2.id)
    assert room is not None
    assert room.room_type == "dm"
    assert room.repository_id is None
    assert room.is_active is True

    members = await RoomService.get_members(async_db, room.id)
    assert len(members) == 2
    member_user_ids = {m["user_id"] for m in members}
    assert async_test_user.id in member_user_ids
    assert async_test_user2.id in member_user_ids


@pytest.mark.asyncio
async def test_dm_room_pair_is_reused_from_either_side(
    async_db: AsyncSession, async_test_user: User, async_test_user2: User
):
    room1 = await RoomService.get_or_create_dm_room(async_db, async_test_user.id, async_test_user2.id)
    room2 = await RoomService.get_or_create_dm_room(async_db, async_test_user2.id, async_test_user.id)
    assert room1.id == room2.id


@pytest.mark.asyncio
async def test_dm_room_not_in_repo_room_list(
    async_db: AsyncSession, async_test_user: User, async_test_user2: User
):
    await RoomService.get_or_create_dm_room(async_db, async_test_user.id, async_test_user2.id)
    rooms = await RoomService.list_rooms(async_db, async_test_user.id)
    assert rooms == []


@pytest.mark.asyncio
async def test_dm_self_chat_forbidden(async_db: AsyncSession, async_test_user: User):
    with pytest.raises(ValidationException):
        await RoomService.get_or_create_dm_room(async_db, async_test_user.id, async_test_user.id)


@pytest.mark.asyncio
async def test_dm_user_not_found(async_db: AsyncSession, async_test_user: User):
    import uuid
    with pytest.raises(ValidationException):
        await RoomService.get_or_create_dm_room(async_db, async_test_user.id, uuid.uuid4())


@pytest.mark.asyncio
async def test_dm_list_rooms_returns_peer(
    async_db: AsyncSession, async_test_user: User, async_test_user2: User, async_another_user: User
):
    await RoomService.get_or_create_dm_room(async_db, async_test_user.id, async_test_user2.id)
    await RoomService.get_or_create_dm_room(async_db, async_test_user.id, async_another_user.id)

    dms = await RoomService.list_dm_rooms(async_db, async_test_user.id)
    assert len(dms) == 2
    peer_ids = {dm["peer_user_id"] for dm in dms}
    assert async_test_user2.id in peer_ids
    assert async_another_user.id in peer_ids
    for dm in dms:
        assert dm["room_type"] == "dm"
        assert "peer_username" in dm

    # 对端视角同样只能看到自己参与的会话
    dms_peer = await RoomService.list_dm_rooms(async_db, async_test_user2.id)
    assert len(dms_peer) == 1
    assert dms_peer[0]["peer_user_id"] == async_test_user.id


@pytest.mark.asyncio
async def test_dm_send_and_fetch_message(
    async_db: AsyncSession, async_test_user: User, async_test_user2: User
):
    room = await RoomService.get_or_create_dm_room(async_db, async_test_user.id, async_test_user2.id)
    msg = await ChatService.send_message(async_db, room.id, async_test_user.id, "hi dm friend")
    assert msg["content"] == "hi dm friend"
    assert msg["sender_id"] == async_test_user.id

    result = await ChatService.get_messages(async_db, room.id, async_test_user2.id)
    assert len(result["messages"]) == 1
    assert result["messages"][0]["content"] == "hi dm friend"


@pytest.mark.asyncio
async def test_dm_non_member_cannot_participate(
    async_db: AsyncSession, async_test_user: User, async_test_user2: User, async_another_user: User
):
    room = await RoomService.get_or_create_dm_room(async_db, async_test_user.id, async_test_user2.id)
    with pytest.raises(ValidationException):
        await ChatService.send_message(async_db, room.id, async_another_user.id, "intrude")
    with pytest.raises(ValidationException):
        await ChatService.get_messages(async_db, room.id, async_another_user.id)


@pytest.mark.asyncio
async def test_dm_mark_read(
    async_db: AsyncSession, async_test_user: User, async_test_user2: User
):
    room = await RoomService.get_or_create_dm_room(async_db, async_test_user.id, async_test_user2.id)
    ok = await ChatService.mark_read(async_db, room.id, async_test_user.id)
    assert ok is True


@pytest.mark.asyncio
async def test_dm_unread_counts(
    async_db: AsyncSession, async_test_user: User, async_test_user2: User,
    async_test_repo: Repository
):
    room = await RoomService.get_or_create_dm_room(async_db, async_test_user.id, async_test_user2.id)
    unread = await ChatService.get_unread_counts(async_db, async_test_user2.id)
    room_ids = {u["room_id"] for u in unread}
    assert room.id in room_ids