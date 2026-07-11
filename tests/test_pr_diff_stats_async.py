"""
PR Diff Stats 功能异步测试

测试 PR 列表响应中包含 diff_stats 字段
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from models.repository import Repository
from models.pull_request import PullRequest
from services import pull_request_service


@pytest_asyncio.fixture
async def test_repo(async_db, async_test_user):
    repo = Repository(name="prds-test", path=f"{async_test_user.username}/prds-test",
                       owner_id=async_test_user.id, is_public=True)
    async_db.add(repo); await async_db.commit(); await async_db.refresh(repo)
    return repo


@pytest.mark.asyncio
async def test_pr_list_includes_diff_stats(async_db, test_repo, async_test_user):
    pr = PullRequest(
        repository_id=test_repo.id, pr_number=1, title="PR1",
        source_branch="f", target_branch="m", author_id=async_test_user.id,
    )
    async_db.add(pr); await async_db.commit()

    result = await pull_request_service.list_pull_requests(async_db, test_repo.id)
    assert "diff_stats" in result["items"][0]


@pytest.mark.asyncio
async def test_pr_list_diff_stats_is_none_by_default(async_db, test_repo, async_test_user):
    pr = PullRequest(
        repository_id=test_repo.id, pr_number=1, title="PR1",
        source_branch="f", target_branch="m", author_id=async_test_user.id,
    )
    async_db.add(pr); await async_db.commit()

    result = await pull_request_service.list_pull_requests(async_db, test_repo.id)
    assert result["items"][0]["diff_stats"] is None
