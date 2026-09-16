import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from services import watch_service
from core.exception import NotFoundException, ConflictException, ValidationException


@pytest_asyncio.fixture
async def test_repo(async_db: AsyncSession, async_test_user):
    repo = Repository(
        name="watch-test-repo",
        path=f"{async_test_user.username}/watch-test-repo",
        description="Watch test",
        owner_id=async_test_user.id,
        is_public=True,
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)
    return repo


@pytest.mark.asyncio
async def test_watch_repository(async_db: AsyncSession, async_test_user, test_repo):
    result = await watch_service.watch_repository(test_repo.id, async_test_user.id, async_db)
    assert result["watch_count"] == 1
    assert result["watching"] is True


@pytest.mark.asyncio
async def test_unwatch_repository(async_db: AsyncSession, async_test_user, test_repo):
    await watch_service.watch_repository(test_repo.id, async_test_user.id, async_db)
    result = await watch_service.unwatch_repository(test_repo.id, async_test_user.id, async_db)
    assert result["watch_count"] == 0
    assert result["watching"] is False


@pytest.mark.asyncio
async def test_watch_already_watching(async_db: AsyncSession, async_test_user, test_repo):
    await watch_service.watch_repository(test_repo.id, async_test_user.id, async_db)
    with pytest.raises(ConflictException) as e:
        await watch_service.watch_repository(test_repo.id, async_test_user.id, async_db)
    assert "already watching" in str(e.value)


@pytest.mark.asyncio
async def test_unwatch_not_watching(async_db: AsyncSession, async_test_user, test_repo):
    with pytest.raises(ValidationException) as e:
        await watch_service.unwatch_repository(test_repo.id, async_test_user.id, async_db)
    assert "not watching" in str(e.value)


@pytest.mark.asyncio
async def test_watch_nonexistent_repo(async_db: AsyncSession, async_test_user):
    with pytest.raises(NotFoundException):
        await watch_service.watch_repository(
            uuid.UUID("00000000-0000-0000-0000-000000000000"),
            async_test_user.id,
            async_db,
        )


@pytest.mark.asyncio
async def test_get_watch_status(async_db: AsyncSession, async_test_user, async_test_user2, test_repo):
    await watch_service.watch_repository(test_repo.id, async_test_user.id, async_db)
    result = await watch_service.get_watch_status(test_repo.id, async_test_user.id, async_db)
    assert result["watching"] is True
    assert result["watch_count"] == 1

    result2 = await watch_service.get_watch_status(test_repo.id, async_test_user2.id, async_db)
    assert result2["watching"] is False
    assert result2["watch_count"] == 1


@pytest.mark.asyncio
async def test_get_watchers(async_db: AsyncSession, async_test_user, test_repo):
    await watch_service.watch_repository(test_repo.id, async_test_user.id, async_db)
    watchers = await watch_service.get_watchers(test_repo.id, async_db)
    assert len(watchers) == 1
    assert watchers[0]["user_id"] == async_test_user.id
