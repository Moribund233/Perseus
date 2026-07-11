"""
PR Activity Log 异步测试

测试 Pull Request 活动日志相关的核心功能
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from models.repository import Repository
from models.pull_request import PullRequest
from services import pr_activity_service


@pytest_asyncio.fixture
async def test_repo(async_db, async_test_user):
    repo = Repository(name="pra-test", path=f"{async_test_user.username}/pra-test",
                       owner_id=async_test_user.id, is_public=True)
    async_db.add(repo); await async_db.commit(); await async_db.refresh(repo)
    return repo


@pytest_asyncio.fixture
async def test_pr(async_db, test_repo, async_test_user):
    pr = PullRequest(repository_id=test_repo.id, pr_number=1, title="PR1",
                      source_branch="f", target_branch="m", author_id=async_test_user.id)
    async_db.add(pr); await async_db.commit(); await async_db.refresh(pr)
    return pr


@pytest.mark.asyncio
async def test_record_activity(async_db, test_pr, async_test_user):
    result = await pr_activity_service.record_activity(
        test_pr.id, async_test_user.id, "created", "PR opened", async_db
    )
    assert result["action"] == "created"
    assert result["details"] == "PR opened"
    assert result["actor_id"] == async_test_user.id


@pytest.mark.asyncio
async def test_list_activities(async_db, test_pr, async_test_user):
    await pr_activity_service.record_activity(test_pr.id, async_test_user.id, "created", None, async_db)
    await pr_activity_service.record_activity(test_pr.id, async_test_user.id, "reviewed", "LGTM", async_db)
    activities = await pr_activity_service.list_activities(test_pr.id, async_db)
    assert len(activities) == 2
    # Most recent first
    assert activities[0]["action"] == "reviewed"
    assert activities[1]["action"] == "created"


@pytest.mark.asyncio
async def test_record_activity_without_details(async_db, test_pr, async_test_user):
    result = await pr_activity_service.record_activity(
        test_pr.id, async_test_user.id, "merged", None, async_db
    )
    assert result["action"] == "merged"
    assert result["details"] is None
