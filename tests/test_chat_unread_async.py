"""
批次 D — 聊天未读数 — Service 层异步测试
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from models.user import User
from services.realtime.room_service import RoomService
from services.realtime.chat_service import ChatService
from core.exception import ValidationException


def _find_unread(result, room_id):
    return next((r for r in result if str(r["room_id"]) == str(room_id)), None)


@pytest.mark.asyncio
async def test_unread_counts_zero_when_no_messages(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    result = await ChatService.get_unread_counts(async_db, async_test_user.id)
    entry = _find_unread(result, room.id)
    assert entry is not None
    assert entry["unread_count"] == 0
    assert entry["room_id"] == room.id
    assert entry["repository_id"] == async_test_repo.id


@pytest.mark.asyncio
async def test_unread_counts_after_other_user_sends(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    for i in range(3):
        await ChatService.send_message(async_db, room.id, async_test_user2.id, f"hi {i}")

    result = await ChatService.get_unread_counts(async_db, async_test_user.id)
    assert _find_unread(result, room.id)["unread_count"] == 3

    # 发送者自己的未读为 0
    result2 = await ChatService.get_unread_counts(async_db, async_test_user2.id)
    assert _find_unread(result2, room.id)["unread_count"] == 0


@pytest.mark.asyncio
async def test_own_messages_not_counted(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    for i in range(5):
        await ChatService.send_message(async_db, room.id, async_test_user.id, f"self {i}")
    result = await ChatService.get_unread_counts(async_db, async_test_user.id)
    assert _find_unread(result, room.id)["unread_count"] == 0


@pytest.mark.asyncio
async def test_mark_read_resets_unread(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    await ChatService.send_message(async_db, room.id, async_test_user2.id, "first")

    await ChatService.mark_read(async_db, room.id, async_test_user.id)
    result = await ChatService.get_unread_counts(async_db, async_test_user.id)
    assert _find_unread(result, room.id)["unread_count"] == 0

    # 已读后新消息重新累计
    await ChatService.send_message(async_db, room.id, async_test_user2.id, "second")
    result = await ChatService.get_unread_counts(async_db, async_test_user.id)
    assert _find_unread(result, room.id)["unread_count"] == 1


@pytest.mark.asyncio
async def test_deleted_messages_not_counted(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    msg = await ChatService.send_message(async_db, room.id, async_test_user2.id, "spam")
    await ChatService.delete_message(async_db, msg["id"], async_test_user2.id)

    result = await ChatService.get_unread_counts(async_db, async_test_user.id)
    assert _find_unread(result, room.id)["unread_count"] == 0


@pytest.mark.asyncio
async def test_non_member_has_no_unread(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await ChatService.send_message(async_db, room.id, async_test_user.id, "private")
    result = await ChatService.get_unread_counts(async_db, async_test_user2.id)
    assert _find_unread(result, room.id) is None


@pytest.mark.asyncio
async def test_new_member_starts_with_zero_unread(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await ChatService.send_message(async_db, room.id, async_test_user.id, "before join")
    # user2 后加入 → 历史消息不计入其未读
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    result = await ChatService.get_unread_counts(async_db, async_test_user2.id)
    assert _find_unread(result, room.id)["unread_count"] == 0


@pytest.mark.asyncio
async def test_mark_read_non_member_private_raises(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    async_test_repo.is_public = False
    await async_db.commit()
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    with pytest.raises(ValidationException):
        await ChatService.mark_read(async_db, room.id, async_test_user2.id)