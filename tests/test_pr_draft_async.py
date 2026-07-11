"""
PR Draft Status 功能异步测试

测试 Pull Request 草稿状态相关的核心功能
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from models.repository import Repository
from models.pull_request import PullRequest
from services import pull_request_service
from core.exception import ValidationException


@pytest_asyncio.fixture
async def test_repo(async_db, async_test_user):
    repo = Repository(name="draft-test-repo", path=f"{async_test_user.username}/draft-test-repo",
                       owner_id=async_test_user.id, is_public=True)
    async_db.add(repo); await async_db.commit(); await async_db.refresh(repo)
    return repo


@pytest_asyncio.fixture
async def test_pr(async_db, test_repo, async_test_user):
    pr = PullRequest(
        repository_id=test_repo.id, pr_number=1, title="Draft PR",
        source_branch="feature", target_branch="main",
        author_id=async_test_user.id, status="open",
    )
    async_db.add(pr); await async_db.commit(); await async_db.refresh(pr)
    return pr


@pytest.mark.asyncio
async def test_create_draft_pr(async_db, test_repo, async_test_user):
    result = await pull_request_service.create_pull_request(
        db=async_db,
        repository_id=test_repo.id,
        author_id=async_test_user.id,
        title="My Draft",
        description=None,
        source_branch="feature",
        target_branch="main"
    )
    # Test that is_draft field is included in response
    assert "is_draft" in result


@pytest.mark.asyncio
async def test_publish_draft(async_db, test_repo, test_pr, async_test_user):
    test_pr.is_draft = True
    await async_db.commit()
    result = await pull_request_service.publish_draft(
        test_repo.id, test_pr.pr_number, async_test_user.id, async_db
    )
    assert result["is_draft"] is False


@pytest.mark.asyncio
async def test_publish_non_draft_raises(async_db, test_repo, test_pr, async_test_user):
    with pytest.raises(ValidationException):
        await pull_request_service.publish_draft(
            test_repo.id, test_pr.pr_number, async_test_user.id, async_db
        )
