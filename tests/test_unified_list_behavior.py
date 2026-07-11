import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from models.repository import Repository
from models.issue import Issue
from models.pull_request import PullRequest
from services import issue_service, pull_request_service


@pytest_asyncio.fixture
async def repo_with_data(async_db: AsyncSession, async_test_user):
    repo = Repository(name="ulb-test", path=f"{async_test_user.username}/ulb-test",
                       owner_id=async_test_user.id, is_public=True)
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)
    for i in range(12):
        issue = Issue(repository_id=repo.id, issue_number=i + 1, title=f"Issue {i}",
                       author_id=async_test_user.id, status="open" if i % 2 == 0 else "closed")
        async_db.add(issue)
    for i in range(8):
        pr = PullRequest(repository_id=repo.id, pr_number=i + 1, title=f"PR {i}",
                          source_branch=f"f{i}", target_branch="m",
                          author_id=async_test_user.id, status="open")
        async_db.add(pr)
    await async_db.commit()
    return repo


@pytest.mark.asyncio
async def test_issue_list_pagination(async_db: AsyncSession, repo_with_data: Repository):
    result = await issue_service.list_issues(async_db, repo_with_data.id, page=1, limit=5)
    assert "items" in result
    assert "total" in result
    assert len(result["items"]) == 5
    assert result["total"] == 12


@pytest.mark.asyncio
async def test_issue_list_filter_by_status(async_db: AsyncSession, repo_with_data: Repository):
    result = await issue_service.list_issues(async_db, repo_with_data.id, status="open")
    assert all(i["status"] == "open" for i in result["items"])


@pytest.mark.asyncio
async def test_pr_list_pagination(async_db: AsyncSession, repo_with_data: Repository):
    result = await pull_request_service.list_pull_requests(
        async_db, repo_with_data.id, page=1, limit=3
    )
    assert "items" in result
    assert "total" in result
    assert len(result["items"]) == 3
    assert result["total"] == 8


@pytest.mark.asyncio
async def test_pr_list_filter_by_status(async_db: AsyncSession, repo_with_data: Repository):
    result = await pull_request_service.list_pull_requests(
        async_db, repo_with_data.id, status="open"
    )
    assert all(pr["status"] == "open" for pr in result["items"])
