import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from models.repository import Repository
from services import activity_service


@pytest_asyncio.fixture
async def test_repo(async_db, async_test_user):
    repo = Repository(name="act-test", path=f"{async_test_user.username}/act-test",
                       owner_id=async_test_user.id, is_public=True)
    async_db.add(repo); await async_db.commit(); await async_db.refresh(repo)
    return repo


@pytest.mark.asyncio
async def test_record_activity(async_db, test_repo, async_test_user):
    result = await activity_service.record_activity(
        test_repo.id, async_test_user.id, "repository", test_repo.id, "created", "Repo created", async_db
    )
    assert result["entity_type"] == "repository"
    assert result["action"] == "created"
    assert result["details"] == "Repo created"


@pytest.mark.asyncio
async def test_list_activities_by_repo(async_db, test_repo, async_test_user):
    await activity_service.record_activity(
        test_repo.id, async_test_user.id, "repository", test_repo.id, "created", None, async_db
    )
    await activity_service.record_activity(
        test_repo.id, async_test_user.id, "pull_request", uuid.uuid4(), "created", "PR opened", async_db
    )
    result = await activity_service.list_activities(repository_id=test_repo.id, db=async_db)
    assert len(result["items"]) == 2
    assert result["total"] == 2


@pytest.mark.asyncio
async def test_list_activities_filter_by_entity(async_db, test_repo, async_test_user):
    await activity_service.record_activity(
        test_repo.id, async_test_user.id, "repository", test_repo.id, "created", None, async_db
    )
    await activity_service.record_activity(
        test_repo.id, async_test_user.id, "pull_request", uuid.uuid4(), "created", None, async_db
    )
    result = await activity_service.list_activities(
        repository_id=test_repo.id, entity_type="pull_request", db=async_db
    )
    assert len(result["items"]) == 1
    assert result["items"][0]["entity_type"] == "pull_request"


@pytest.mark.asyncio
async def test_list_activities_filter_by_actor(async_db, test_repo, async_test_user, async_test_user2):
    await activity_service.record_activity(
        test_repo.id, async_test_user.id, "repository", test_repo.id, "created", None, async_db
    )
    await activity_service.record_activity(
        test_repo.id, async_test_user2.id, "repository", test_repo.id, "updated", None, async_db
    )
    result = await activity_service.list_activities(
        repository_id=test_repo.id, actor_id=async_test_user.id, db=async_db
    )
    assert len(result["items"]) == 1


@pytest.mark.asyncio
async def test_list_activities_pagination(async_db, test_repo, async_test_user):
    for i in range(15):
        await activity_service.record_activity(
            test_repo.id, async_test_user.id, "repository", test_repo.id, "created", None, async_db
        )
    result = await activity_service.list_activities(repository_id=test_repo.id, db=async_db, page=1, limit=5)
    assert len(result["items"]) == 5
    assert result["total"] == 15
    assert result["has_next"] is True
