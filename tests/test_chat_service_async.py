"""
F-202 团队聊天 — Service 层异步测试
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from models.user import User
from services.realtime.room_service import RoomService
from services.realtime.chat_service import ChatService
from core.exception import ValidationException, NotFoundException


@pytest.mark.asyncio
async def test_send_message_success(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    msg = await ChatService.send_message(async_db, room.id, async_test_user.id, "hello world")
    assert msg["content"] == "hello world"
    assert msg["sender_id"] == async_test_user.id
    assert msg["room_id"] == room.id
    assert msg["message_type"] == "text"
    assert msg["sender_username"] == "async_testuser"
    assert "created_at" in msg
    assert msg["reply_to"] is None


@pytest.mark.asyncio
async def test_send_message_invalid_room(async_db: AsyncSession, async_test_user: User):
    with pytest.raises(NotFoundException):
        await ChatService.send_message(async_db, 9999, async_test_user.id, "hello")


@pytest.mark.asyncio
async def test_send_message_inactive_room(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await RoomService.delete_room(async_db, room.id)
    with pytest.raises(ValidationException):
        await ChatService.send_message(async_db, room.id, async_test_user.id, "hello")


@pytest.mark.asyncio
async def test_send_message_not_member(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    with pytest.raises(ValidationException):
        await ChatService.send_message(async_db, room.id, async_test_user2.id, "hello")


@pytest.mark.asyncio
async def test_get_messages_empty(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    result = await ChatService.get_messages(async_db, room.id, async_test_user.id)
    assert result["messages"] == []
    assert result["has_more"] is False
    assert result["next_before"] is None


@pytest.mark.asyncio
async def test_get_messages_pagination(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    for i in range(60):
        await ChatService.send_message(async_db, room.id, async_test_user.id, f"msg_{i}")
    result = await ChatService.get_messages(async_db, room.id, async_test_user.id, limit=50)
    assert len(result["messages"]) == 50
    assert result["has_more"] is True
    assert result["next_before"] is not None


@pytest.mark.asyncio
async def test_get_messages_with_before(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    for i in range(10):
        await ChatService.send_message(async_db, room.id, async_test_user.id, f"msg_{i}")
    all_result = await ChatService.get_messages(async_db, room.id, async_test_user.id, limit=10)
    second_page = await ChatService.get_messages(async_db, room.id, async_test_user.id, before=all_result["next_before"], limit=10)
    assert len(second_page["messages"]) >= 1


@pytest.mark.asyncio
async def test_edit_own_message(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    msg = await ChatService.send_message(async_db, room.id, async_test_user.id, "original")
    updated = await ChatService.edit_message(async_db, msg["id"], async_test_user.id, "edited")
    assert updated["content"] == "edited"
    assert updated["edited_at"] is not None


@pytest.mark.asyncio
async def test_edit_others_message_forbidden(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    msg = await ChatService.send_message(async_db, room.id, async_test_user.id, "original")
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    with pytest.raises(ValidationException):
        await ChatService.edit_message(async_db, msg["id"], async_test_user2.id, "hacked")


@pytest.mark.asyncio
async def test_delete_own_message(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    msg = await ChatService.send_message(async_db, room.id, async_test_user.id, "delete me")
    result = await ChatService.delete_message(async_db, msg["id"], async_test_user.id)
    assert result is True


@pytest.mark.asyncio
async def test_delete_message_as_admin(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    msg = await ChatService.send_message(async_db, room.id, async_test_user2.id, "bad msg")
    result = await ChatService.delete_message(async_db, msg["id"], async_test_user.id)
    assert result is True


@pytest.mark.asyncio
async def test_send_message_with_reply(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    msg1 = await ChatService.send_message(async_db, room.id, async_test_user.id, "original")
    msg2 = await ChatService.send_message(async_db, room.id, async_test_user.id, "reply", reply_to=msg1["id"])
    assert msg2["reply_to"] == msg1["id"]


@pytest.mark.asyncio
async def test_get_messages_sender_info(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    await ChatService.send_message(async_db, room.id, async_test_user.id, "from user1")
    await ChatService.send_message(async_db, room.id, async_test_user2.id, "from user2")
    result = await ChatService.get_messages(async_db, room.id, async_test_user.id)
    usernames = {m["sender_username"] for m in result["messages"]}
    assert "async_testuser" in usernames
    assert "async_testuser2" in usernames


@pytest.mark.asyncio
async def test_send_message_validation_empty_content(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    with pytest.raises(ValidationException):
        await ChatService.send_message(async_db, room.id, async_test_user.id, "")


@pytest.mark.asyncio
async def test_send_message_clips_long_content(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    long_msg = "x" * 20000
    msg = await ChatService.send_message(async_db, room.id, async_test_user.id, long_msg)
    assert len(msg["content"]) == 10000


@pytest.mark.asyncio
async def test_delete_message_not_found(async_db: AsyncSession):
    result = await ChatService.delete_message(async_db, 9999, 1)
    assert result is False


@pytest.mark.asyncio
async def test_delete_others_message_not_admin(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    msg = await ChatService.send_message(async_db, room.id, async_test_user.id, "owner msg")
    with pytest.raises(ValidationException):
        await ChatService.delete_message(async_db, msg["id"], async_test_user2.id)
