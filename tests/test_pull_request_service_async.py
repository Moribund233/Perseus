"""
Pull Request Service 异步测试

测试 Pull Request 服务层的所有功能
"""
import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from models.pull_request import PullRequest, PRComment, PRReview
from services import pull_request_service
from core.exception import NotFoundException, ValidationException


@pytest_asyncio.fixture
async def test_pr(async_db: AsyncSession, async_test_repo, async_test_user):
    """创建测试 Pull Request"""
    pr = PullRequest(
        repository_id=async_test_repo.id,
        pr_number=1,
        title="Test PR",
        description="This is a test PR",
        source_branch="feature",
        target_branch="main",
        author_id=async_test_user.id,
        status="open"
    )
    async_db.add(pr)
    await async_db.commit()
    await async_db.refresh(pr)
    return pr


@pytest.mark.asyncio
async def test_list_pull_requests(async_db: AsyncSession, async_test_repo, test_pr: PullRequest):
    """测试获取 PR 列表"""
    result = await pull_request_service.list_pull_requests(async_db, async_test_repo.id)
    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["title"] == test_pr.title


@pytest.mark.asyncio
async def test_list_pull_requests_with_status_filter(async_db: AsyncSession, async_test_repo, test_pr: PullRequest):
    """测试按状态过滤 PR"""
    result = await pull_request_service.list_pull_requests(async_db, async_test_repo.id, status="open")
    assert result["total"] == 1

    result = await pull_request_service.list_pull_requests(async_db, async_test_repo.id, status="closed")
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_get_pull_request(async_db: AsyncSession, async_test_repo, test_pr: PullRequest):
    """测试获取 PR 详情"""
    pr = await pull_request_service.get_pull_request(async_db, async_test_repo.id, test_pr.pr_number)
    assert pr["title"] == test_pr.title
    assert pr["status"] == test_pr.status


@pytest.mark.asyncio
async def test_get_pull_request_not_found(async_db: AsyncSession, async_test_repo):
    """测试获取不存在的 PR"""
    with pytest.raises(NotFoundException):
        await pull_request_service.get_pull_request(async_db, async_test_repo.id, 999)


@pytest.mark.asyncio
async def test_create_pull_request(async_db: AsyncSession, async_test_repo, async_test_user):
    """测试创建 PR"""
    pr = await pull_request_service.create_pull_request(
        async_db, async_test_repo.id, async_test_user.id,
        title="New PR",
        description="New description",
        source_branch="feature-branch",
        target_branch="main"
    )
    assert pr["title"] == "New PR"
    assert pr["status"] == "open"
    assert pr["source_branch"] == "feature-branch"
    assert pr["target_branch"] == "main"


@pytest.mark.asyncio
async def test_create_pull_request_empty_title(async_db: AsyncSession, async_test_repo, async_test_user):
    """测试创建 PR 空标题"""
    with pytest.raises(ValidationException):
        await pull_request_service.create_pull_request(
            async_db, async_test_repo.id, async_test_user.id,
            title="",
            description="Description",
            source_branch="feature",
            target_branch="main"
        )


@pytest.mark.asyncio
async def test_create_pull_request_same_branches(async_db: AsyncSession, async_test_repo, async_test_user):
    """测试创建 PR 相同分支"""
    with pytest.raises(ValidationException):
        await pull_request_service.create_pull_request(
            async_db, async_test_repo.id, async_test_user.id,
            title="New PR",
            description="Description",
            source_branch="main",
            target_branch="main"
        )


@pytest.mark.asyncio
async def test_update_pull_request(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试更新 PR"""
    updated = await pull_request_service.update_pull_request(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
        title="Updated Title",
        description="Updated description"
    )
    assert updated["title"] == "Updated Title"
    assert updated["description"] == "Updated description"


@pytest.mark.asyncio
async def test_update_pull_request_not_found(async_db: AsyncSession, async_test_repo, async_test_user):
    """测试更新不存在的 PR"""
    with pytest.raises(NotFoundException):
        await pull_request_service.update_pull_request(
            async_db, async_test_repo.id, 999, async_test_user.id,
            title="Updated Title"
        )


@pytest.mark.asyncio
async def test_close_pull_request(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试关闭 PR"""
    closed = await pull_request_service.close_pull_request(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id
    )
    assert closed["status"] == "closed"


@pytest.mark.asyncio
async def test_close_pull_request_already_closed(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试关闭已关闭的 PR"""
    await pull_request_service.close_pull_request(async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id)
    with pytest.raises(ValidationException):
        await pull_request_service.close_pull_request(async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id)


@pytest.mark.asyncio
async def test_create_pr_comment(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试添加 PR 评论"""
    comment = await pull_request_service.create_pr_comment(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
        content="This is a PR comment"
    )
    assert comment["content"] == "This is a PR comment"


@pytest.mark.asyncio
async def test_create_pr_comment_empty_content(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试添加空内容评论"""
    with pytest.raises(ValidationException):
        await pull_request_service.create_pr_comment(
            async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
            content=""
        )


@pytest.mark.asyncio
async def test_create_pr_review_approved(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试创建批准审查"""
    review = await pull_request_service.create_pr_review(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
        status="approved",
        comment="LGTM"
    )
    assert review["status"] == "approved"
    assert review["comment"] == "LGTM"


@pytest.mark.asyncio
async def test_create_pr_review_changes_requested(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试创建请求修改审查"""
    review = await pull_request_service.create_pr_review(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
        status="changes_requested",
        comment="Please fix this"
    )
    assert review["status"] == "changes_requested"


@pytest.mark.asyncio
async def test_create_pr_review_invalid_status(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试创建无效状态审查"""
    with pytest.raises(ValidationException):
        await pull_request_service.create_pr_review(
            async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
            status="invalid_status"
        )


@pytest.mark.asyncio
async def test_list_pr_comments(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试获取 PR 评论列表"""
    # 添加评论
    await pull_request_service.create_pr_comment(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
        content="Comment 1"
    )
    await pull_request_service.create_pr_comment(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
        content="Comment 2"
    )

    comments = await pull_request_service.list_pr_comments(async_db, async_test_repo.id, test_pr.pr_number)
    assert len(comments) == 2
