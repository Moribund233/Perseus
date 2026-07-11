import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from models.pull_request import PullRequest
from services import pr_label_service
from core.exception import ConflictException, NotFoundException


@pytest_asyncio.fixture
async def test_repo(async_db, async_test_user):
    repo = Repository(
        name="prl-test",
        path=f"{async_test_user.username}/prl-test",
        owner_id=async_test_user.id,
        is_public=True,
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)
    return repo


@pytest_asyncio.fixture
async def test_pr(async_db, test_repo, async_test_user):
    pr = PullRequest(
        repository_id=test_repo.id,
        pr_number=1,
        title="PR1",
        source_branch="feature",
        target_branch="main",
        author_id=async_test_user.id,
    )
    async_db.add(pr)
    await async_db.commit()
    await async_db.refresh(pr)
    return pr


@pytest.mark.asyncio
async def test_create_pr_label(async_db, test_repo):
    result = await pr_label_service.create_label(
        test_repo.id, {"name": "bug", "color": "#ff0000"}, async_db
    )
    assert result["name"] == "bug"
    assert result["color"] == "#ff0000"


@pytest.mark.asyncio
async def test_create_label_duplicate(async_db, test_repo):
    await pr_label_service.create_label(test_repo.id, {"name": "bug"}, async_db)
    with pytest.raises(ConflictException):
        await pr_label_service.create_label(test_repo.id, {"name": "bug"}, async_db)


@pytest.mark.asyncio
async def test_add_label_to_pr(async_db, test_pr, test_repo):
    label = await pr_label_service.create_label(test_repo.id, {"name": "bug"}, async_db)
    result = await pr_label_service.add_label_to_pr(test_pr.id, label["id"], async_db)
    assert result["message"] == "Label added to pull request"


@pytest.mark.asyncio
async def test_list_prs_by_label(async_db, test_pr, test_repo):
    label = await pr_label_service.create_label(test_repo.id, {"name": "bug"}, async_db)
    await pr_label_service.add_label_to_pr(test_pr.id, label["id"], async_db)
    prs = await pr_label_service.get_prs_by_label(label["id"], async_db)
    assert len(prs) == 1
    assert prs[0]["id"] == test_pr.id


@pytest.mark.asyncio
async def test_get_labels(async_db, test_repo):
    await pr_label_service.create_label(test_repo.id, {"name": "bug"}, async_db)
    await pr_label_service.create_label(test_repo.id, {"name": "feature"}, async_db)
    labels = await pr_label_service.get_labels(test_repo.id, async_db)
    assert len(labels) == 2


@pytest.mark.asyncio
async def test_delete_label(async_db, test_repo):
    label = await pr_label_service.create_label(test_repo.id, {"name": "bug"}, async_db)
    await pr_label_service.delete_label(test_repo.id, label["id"], async_db)
    labels = await pr_label_service.get_labels(test_repo.id, async_db)
    assert len(labels) == 0


@pytest.mark.asyncio
async def test_get_labels_repo_not_found(async_db):
    with pytest.raises(NotFoundException):
        await pr_label_service.get_labels(9999, async_db)


@pytest.mark.asyncio
async def test_create_label_repo_not_found(async_db):
    with pytest.raises(NotFoundException):
        await pr_label_service.create_label(9999, {"name": "bug"}, async_db)
