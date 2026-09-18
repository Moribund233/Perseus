"""
批次 G — 会话静音 — Service 层异步测试

静音本人某会话后, 该会话不再累计未读; 取消静音恢复累计。
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from models.user import User
from services.realtime.room_service import RoomService
from services.realtime.chat_service import ChatService
from core.exception import NotFoundException


def _find_unread(result, room_id):
    return next((r for r in result if str(r["room_id"]) == str(room_id)), None)


@pytest.mark.asyncio
async def test_set_member_muted_success(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User
):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    result = await RoomService.set_member_muted(async_db, room.id, async_test_user.id, True)
    assert result["is_muted"] is True
    assert str(result["room_id"]) == str(room.id)
    assert str(result["user_id"]) == str(async_test_user.id)

    # 取消静音
    result = await RoomService.set_member_muted(async_db, room.id, async_test_user.id, False)
    assert result["is_muted"] is False


@pytest.mark.asyncio
async def test_set_member_muted_non_member_raises(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User
):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    with pytest.raises(NotFoundException):
        await RoomService.set_member_muted(async_db, room.id, async_test_user2.id, True)


@pytest.mark.asyncio
async def test_unread_excludes_muted_room(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User
):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    for i in range(3):
        await ChatService.send_message(async_db, room.id, async_test_user2.id, f"hi {i}")

    # 静音前: 未读 3
    result = await ChatService.get_unread_counts(async_db, async_test_user.id)
    assert _find_unread(result, room.id)["unread_count"] == 3

    # 静音后: 不再累计未读 (条目保留但计数为 0)
    await RoomService.set_member_muted(async_db, room.id, async_test_user.id, True)
    result = await ChatService.get_unread_counts(async_db, async_test_user.id)
    assert _find_unread(result, room.id)["unread_count"] == 0

    # 静音期间新消息也不计
    await ChatService.send_message(async_db, room.id, async_test_user2.id, "muted msg")
    result = await ChatService.get_unread_counts(async_db, async_test_user.id)
    assert _find_unread(result, room.id)["unread_count"] == 0

    # 取消静音后恢复累计 (含静音期间的新消息)
    await RoomService.set_member_muted(async_db, room.id, async_test_user.id, False)
    result = await ChatService.get_unread_counts(async_db, async_test_user.id)
    assert _find_unread(result, room.id)["unread_count"] == 4


@pytest.mark.asyncio
async def test_mute_does_not_affect_other_members(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User
):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    # user1 静音自己, user2 保持未静音
    await RoomService.set_member_muted(async_db, room.id, async_test_user.id, True)
    await ChatService.send_message(async_db, room.id, async_test_user2.id, "ping")

    # user1 静音 → 0
    result = await ChatService.get_unread_counts(async_db, async_test_user.id)
    assert _find_unread(result, room.id)["unread_count"] == 0
    # user2 仍在会话发送者视角: 未读 0 (自己的消息不计)
    result2 = await ChatService.get_unread_counts(async_db, async_test_user2.id)
    assert _find_unread(result2, room.id)["unread_count"] == 0