import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from services import label_service
from core.exception import NotFoundException, ConflictException


@pytest_asyncio.fixture
async def test_repo(async_db, async_test_user):
    repo = Repository(
        name="label-test-repo",
        path=f"{async_test_user.username}/label-test-repo",
        owner_id=async_test_user.id,
        is_public=True,
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)
    return repo


@pytest.mark.asyncio
async def test_create_repo_label(async_db, test_repo):
    result = await label_service.create_label(
        test_repo.id,
        {"name": "bug", "color": "#ff0000", "description": "Bug reports"},
        async_db,
    )
    assert result["name"] == "bug"
    assert result["color"] == "#ff0000"


@pytest.mark.asyncio
async def test_create_label_duplicate_name(async_db, test_repo):
    await label_service.create_label(test_repo.id, {"name": "bug"}, async_db)
    with pytest.raises(ConflictException):
        await label_service.create_label(test_repo.id, {"name": "bug"}, async_db)


@pytest.mark.asyncio
async def test_get_labels(async_db, test_repo):
    await label_service.create_label(test_repo.id, {"name": "bug"}, async_db)
    await label_service.create_label(test_repo.id, {"name": "enhancement"}, async_db)
    labels = await label_service.get_labels(test_repo.id, async_db)
    assert len(labels) == 2


@pytest.mark.asyncio
async def test_update_label(async_db, test_repo):
    created = await label_service.create_label(test_repo.id, {"name": "bug"}, async_db)
    result = await label_service.update_label(
        test_repo.id, created["id"], {"name": "bug-fix", "color": "#00ff00"}, async_db
    )
    assert result["name"] == "bug-fix"


@pytest.mark.asyncio
async def test_delete_label(async_db, test_repo):
    created = await label_service.create_label(test_repo.id, {"name": "bug"}, async_db)
    await label_service.delete_label(test_repo.id, created["id"], async_db)
    labels = await label_service.get_labels(test_repo.id, async_db)
    assert len(labels) == 0


@pytest.mark.asyncio
async def test_filter_by_label(async_db, async_test_user, test_repo):
    label = await label_service.create_label(test_repo.id, {"name": "bug"}, async_db)

    repo2 = Repository(
        name="label-test-repo2",
        path=f"{async_test_user.username}/label-test-repo2",
        owner_id=async_test_user.id,
        is_public=True,
    )
    async_db.add(repo2)
    await async_db.commit()
    await async_db.refresh(repo2)

    await label_service.add_label_to_repository(test_repo.id, label["id"], async_db)
    result = await label_service.get_repositories_by_label(label["id"], async_db)
    assert len(result) == 1
    assert result[0]["id"] == test_repo.id


@pytest.mark.asyncio
async def test_label_not_found(async_db, test_repo):
    with pytest.raises(NotFoundException):
        await label_service.get_labels(9999, async_db)


@pytest.mark.asyncio
async def test_create_label_repo_not_found(async_db):
    with pytest.raises(NotFoundException):
        await label_service.create_label(9999, {"name": "bug"}, async_db)
