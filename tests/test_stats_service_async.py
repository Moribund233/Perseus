import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from models.repository import Repository
from models.pull_request import PullRequest, PRReview
from models.issue import Issue
from models.repository_member import RepositoryMember
from models.stargazer import Stargazer
from services import stats_service
from core.exception import NotFoundException


@pytest_asyncio.fixture
async def repo_with_data(async_db, async_test_user):
    repo = Repository(name="stats-repo", path=f"{async_test_user.username}/stats-repo",
                       owner_id=async_test_user.id, is_public=True)
    async_db.add(repo); await async_db.commit(); await async_db.refresh(repo)
    member = RepositoryMember(repository_id=repo.id, user_id=async_test_user.id, role="owner")
    async_db.add(member)
    star = Stargazer(repository_id=repo.id, user_id=async_test_user.id)
    async_db.add(star)
    pr = PullRequest(repository_id=repo.id, pr_number=1, title="PR1", source_branch="f",
                      target_branch="m", author_id=async_test_user.id, status="open")
    async_db.add(pr); await async_db.commit(); await async_db.refresh(pr)
    issue = Issue(repository_id=repo.id, issue_number=1, title="Issue1",
                   author_id=async_test_user.id, status="open")
    async_db.add(issue)
    review = PRReview(pull_request_id=pr.id, reviewer_id=async_test_user.id, status="approved")
    async_db.add(review); await async_db.commit()
    return repo


@pytest.mark.asyncio
async def test_repo_stats(async_db, repo_with_data):
    result = await stats_service.get_repo_stats(repo_with_data.id, async_db)
    assert result["pr_count"] == 1
    assert result["issue_count"] == 1
    assert result["review_count"] == 1
    assert result["star_count"] == 1
    assert result["member_count"] == 1


@pytest.mark.asyncio
async def test_repo_stats_empty(async_db, async_test_user):
    repo = Repository(name="empty-stats", path=f"{async_test_user.username}/empty-stats",
                       owner_id=async_test_user.id, is_public=True)
    async_db.add(repo); await async_db.commit(); await async_db.refresh(repo)
    result = await stats_service.get_repo_stats(repo.id, async_db)
    assert result["pr_count"] == 0
    assert result["issue_count"] == 0
    assert result["star_count"] == 0
    assert result["member_count"] == 0


@pytest.mark.asyncio
async def test_repo_stats_not_found(async_db):
    with pytest.raises(NotFoundException):
        await stats_service.get_repo_stats(uuid.UUID("00000000-0000-0000-0000-000000000000"), async_db)