"""
F-201 房间/频道管理 — Service 层异步测试

测试 RealtimeRoom 和 RoomMember 的业务逻辑
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from models.user import User
from services.realtime.room_service import RoomService
from core.exception import NotFoundException, ValidationException


@pytest.mark.asyncio
async def test_create_room_success(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    assert room.name == "general"
    assert room.repository_id == async_test_repo.id
    assert room.is_active is True
    assert room.id is not None


@pytest.mark.asyncio
async def test_create_room_sets_creator_as_admin(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    members = await RoomService.get_members(async_db, room.id)
    assert len(members) == 1
    assert members[0]["user_id"] == async_test_user.id
    assert members[0]["role"] == "admin"


@pytest.mark.asyncio
async def test_create_duplicate_room_raises_error(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    with pytest.raises(ValidationException):
        await RoomService.create_room(async_db, async_test_repo.id, "dev", async_test_user.id)


@pytest.mark.asyncio
async def test_get_repository_room(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    created = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    found = await RoomService.get_repository_room(async_db, async_test_repo.id)
    assert found is not None
    assert found.id == created.id


@pytest.mark.asyncio
async def test_get_repository_room_not_found(async_db: AsyncSession):
    found = await RoomService.get_repository_room(async_db, 9999)
    assert found is None


@pytest.mark.asyncio
async def test_join_room_success(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    member = await RoomService.join_room(async_db, room.id, async_test_user2.id)
    assert member.user_id == async_test_user2.id
    assert member.role == "member"
    assert member.is_muted is False


@pytest.mark.asyncio
async def test_join_room_duplicate_returns_existing(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    member1 = await RoomService.join_room(async_db, room.id, async_test_user.id)
    member2 = await RoomService.join_room(async_db, room.id, async_test_user.id)
    assert member1.id == member2.id


@pytest.mark.asyncio
async def test_leave_room_success(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    result = await RoomService.leave_room(async_db, room.id, async_test_user2.id)
    assert result is True
    members = await RoomService.get_members(async_db, room.id)
    assert len(members) == 1


@pytest.mark.asyncio
async def test_leave_room_not_member(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    result = await RoomService.leave_room(async_db, room.id, 9999)
    assert result is False


@pytest.mark.asyncio
async def test_list_rooms_for_user(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room1 = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    rooms = await RoomService.list_rooms(async_db, async_test_user.id)
    assert len(rooms) == 1
    assert rooms[0].id == room1.id

    rooms_other = await RoomService.list_rooms(async_db, async_test_user2.id)
    assert len(rooms_other) == 0


@pytest.mark.asyncio
async def test_get_members_includes_user_info(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    members = await RoomService.get_members(async_db, room.id)
    assert len(members) == 2
    usernames = {m["username"] for m in members}
    assert "async_testuser" in usernames
    assert "async_testuser2" in usernames


@pytest.mark.asyncio
async def test_update_member_role(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    updated = await RoomService.update_member_role(async_db, room.id, async_test_user2.id, "admin")
    assert updated.role == "admin"


@pytest.mark.asyncio
async def test_update_member_role_invalid(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    with pytest.raises(ValidationException):
        await RoomService.update_member_role(async_db, room.id, async_test_user.id, "invalid_role")


@pytest.mark.asyncio
async def test_remove_member(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_test_user2: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    await RoomService.join_room(async_db, room.id, async_test_user2.id)
    result = await RoomService.remove_member(async_db, room.id, async_test_user2.id)
    assert result is True
    members = await RoomService.get_members(async_db, room.id)
    assert len(members) == 1


@pytest.mark.asyncio
async def test_remove_member_not_found(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    result = await RoomService.remove_member(async_db, room.id, 9999)
    assert result is False


@pytest.mark.asyncio
async def test_delete_room_soft_delete(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    room = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    result = await RoomService.delete_room(async_db, room.id)
    assert result is True

    found = await RoomService.get_room(async_db, room.id)
    assert found is not None
    assert found.is_active is False


@pytest.mark.asyncio
async def test_get_room_not_found(async_db: AsyncSession):
    found = await RoomService.get_room(async_db, 9999)
    assert found is None


@pytest.mark.asyncio
async def test_get_room_by_id(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    created = await RoomService.create_room(async_db, async_test_repo.id, "general", async_test_user.id)
    found = await RoomService.get_room(async_db, created.id)
    assert found is not None
    assert found.id == created.id
