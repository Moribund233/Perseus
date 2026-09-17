"""
消息检索 — Service 层异步测试
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.repository import Repository
from services.realtime.room_service import RoomService
from services.realtime.chat_service import ChatService
from tests.test_helpers import async_create_test_repo
from core.exception import ValidationException


@pytest.mark.asyncio
async def test_get_messages_filter_by_keyword(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User
):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await ChatService.send_message(async_db, room.id, async_test_user.id, "hello world")
    await ChatService.send_message(async_db, room.id, async_test_user.id, "deployment config")

    result = await ChatService.get_messages(async_db, room.id, async_test_user.id, q="hello")
    assert len(result["messages"]) == 1
    assert result["messages"][0]["content"] == "hello world"


@pytest.mark.asyncio
async def test_search_messages_across_rooms(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User,
    async_test_user2: User
):
    repo2 = await async_create_test_repo(async_db, name="async-test-repo2", owner_id=async_test_user2.id)
    room1 = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    room2 = await RoomService.create_room(async_db, repo2.id, "general", async_test_user2.id)
    await RoomService.join_room(async_db, room2.id, async_test_user.id)

    await ChatService.send_message(async_db, room1.id, async_test_user.id, "search me alpha")
    await ChatService.send_message(async_db, room2.id, async_test_user.id, "search me beta")

    result = await ChatService.search_messages(async_db, async_test_user.id, q="search", limit=50)
    assert len(result["messages"]) == 2
    room_ids = {m["room_id"] for m in result["messages"]}
    assert room1.id in room_ids
    assert room2.id in room_ids
    target = next(m for m in result["messages"] if m["room_id"] == room1.id)
    assert target["room_name"] == "general"
    assert target["room_type"] == "repository"


@pytest.mark.asyncio
async def test_search_messages_only_joined_rooms(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User,
    async_test_user2: User
):
    repo2 = await async_create_test_repo(async_db, name="async-test-repo2", owner_id=async_test_user2.id)
    room_own = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    # 第二人创建的房间, 当前用户未加入, 不应命中
    room_other = await RoomService.create_room(async_db, repo2.id, "general", async_test_user2.id)
    await ChatService.send_message(async_db, room_own.id, async_test_user.id, "shared keyword")
    await ChatService.send_message(async_db, room_other.id, async_test_user2.id, "shared keyword")

    result = await ChatService.search_messages(async_db, async_test_user.id, q="shared")
    assert len(result["messages"]) == 1
    assert result["messages"][0]["room_id"] == room_own.id


@pytest.mark.asyncio
async def test_search_messages_empty_query_rejected(async_db: AsyncSession, async_test_user: User):
    with pytest.raises(ValidationException):
        await ChatService.search_messages(async_db, async_test_user.id, q="   ")


@pytest.mark.asyncio
async def test_search_messages_in_dm(
    async_db: AsyncSession, async_test_user: User, async_test_user2: User
):
    dm = await RoomService.get_or_create_dm_room(async_db, async_test_user.id, async_test_user2.id)
    await ChatService.send_message(async_db, dm.id, async_test_user.id, "private secret plan")

    result = await ChatService.search_messages(async_db, async_test_user2.id, q="secret")
    assert len(result["messages"]) == 1
    assert result["messages"][0]["room_type"] == "dm"
    assert result["messages"][0]["repository_id"] is None


@pytest.mark.asyncio
async def test_search_messages_case_insensitive(
    async_db: AsyncSession, async_test_repo: Repository, async_test_user: User
):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await ChatService.send_message(async_db, room.id, async_test_user.id, "Hello World")

    result_lower = await ChatService.search_messages(async_db, async_test_user.id, q="hello")
    result_mixed = await ChatService.search_messages(async_db, async_test_user.id, q="HeLLo")
    assert len(result_lower["messages"]) == 1
    assert len(result_mixed["messages"]) == 1