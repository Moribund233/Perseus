import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from services import star_service
from core.exception import NotFoundException, ConflictException, ValidationException


@pytest_asyncio.fixture
async def test_repo(async_db: AsyncSession, async_test_user):
    repo = Repository(
        name="star-test-repo",
        path=f"{async_test_user.username}/star-test-repo",
        description="Star test",
        owner_id=async_test_user.id,
        is_public=True,
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)
    return repo


@pytest.mark.asyncio
async def test_star_repository(async_db: AsyncSession, async_test_user, test_repo):
    result = await star_service.star_repository(test_repo.id, async_test_user.id, async_db)
    assert result["star_count"] == 1
    assert result["starred"] is True


@pytest.mark.asyncio
async def test_unstar_repository(async_db: AsyncSession, async_test_user, test_repo):
    await star_service.star_repository(test_repo.id, async_test_user.id, async_db)
    result = await star_service.unstar_repository(test_repo.id, async_test_user.id, async_db)
    assert result["star_count"] == 0
    assert result["starred"] is False


@pytest.mark.asyncio
async def test_star_already_starred(async_db: AsyncSession, async_test_user, test_repo):
    await star_service.star_repository(test_repo.id, async_test_user.id, async_db)
    with pytest.raises(ConflictException) as e:
        await star_service.star_repository(test_repo.id, async_test_user.id, async_db)
    assert "already starred" in str(e.value)


@pytest.mark.asyncio
async def test_unstar_not_starred(async_db: AsyncSession, async_test_user, test_repo):
    with pytest.raises(ValidationException) as e:
        await star_service.unstar_repository(test_repo.id, async_test_user.id, async_db)
    assert "not starred" in str(e.value)


@pytest.mark.asyncio
async def test_star_nonexistent_repo(async_db: AsyncSession, async_test_user):
    with pytest.raises(NotFoundException):
        await star_service.star_repository(99999, async_test_user.id, async_db)


@pytest.mark.asyncio
async def test_get_star_status(async_db: AsyncSession, async_test_user, async_test_user2, test_repo):
    await star_service.star_repository(test_repo.id, async_test_user.id, async_db)
    result = await star_service.get_star_status(test_repo.id, async_test_user.id, async_db)
    assert result["starred"] is True
    assert result["star_count"] == 1

    result2 = await star_service.get_star_status(test_repo.id, async_test_user2.id, async_db)
    assert result2["starred"] is False
    assert result2["star_count"] == 1


@pytest.mark.asyncio
async def test_get_stargazers(async_db: AsyncSession, async_test_user, test_repo):
    await star_service.star_repository(test_repo.id, async_test_user.id, async_db)
    stargazers = await star_service.get_stargazers(test_repo.id, async_db)
    assert len(stargazers) == 1
    assert stargazers[0]["user_id"] == async_test_user.id
