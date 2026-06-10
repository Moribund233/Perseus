"""
Issue 标签管理功能异步测试

测试 Issue 标签管理相关的核心功能
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.issue import Issue, Label
from models.repository import Repository
from services import issue_service
from core.exception import NotFoundException, ValidationException


@pytest_asyncio.fixture
async def test_issue(async_db: AsyncSession, async_test_repo: Repository, async_test_user):
    """创建测试 Issue"""
    issue = Issue(
        repository_id=async_test_repo.id,
        issue_number=1,
        title="Test Issue",
        description="This is a test issue",
        author_id=async_test_user.id,
        status="open",
        priority="medium"
    )
    async_db.add(issue)
    await async_db.commit()
    await async_db.refresh(issue)
    return issue


@pytest_asyncio.fixture
async def test_label(async_db: AsyncSession, async_test_repo: Repository):
    """创建测试标签"""
    label = Label(
        name="bug",
        color="#ff0000",
        repository_id=async_test_repo.id
    )
    async_db.add(label)
    await async_db.commit()
    await async_db.refresh(label)
    return label


@pytest_asyncio.fixture
async def test_label2(async_db: AsyncSession, async_test_repo: Repository):
    """创建第二个测试标签"""
    label = Label(
        name="feature",
        color="#00ff00",
        repository_id=async_test_repo.id
    )
    async_db.add(label)
    await async_db.commit()
    await async_db.refresh(label)
    return label


@pytest.mark.asyncio
async def test_add_label_to_issue_success(async_db: AsyncSession, async_test_repo: Repository, test_issue: Issue, test_label: Label, async_test_user):
    """测试成功为 Issue 添加标签"""
    updated_issue = await issue_service.add_label_to_issue(
        async_db, async_test_repo.id, test_issue.issue_number, test_label.id, async_test_user.id
    )
    assert len(updated_issue["labels"]) == 1
    assert updated_issue["labels"][0]["name"] == "bug"


@pytest.mark.asyncio
async def test_add_label_to_issue_not_found(async_db: AsyncSession, async_test_repo: Repository, test_issue: Issue, async_test_user):
    """测试为 Issue 添加不存在的标签"""
    with pytest.raises(NotFoundException) as exc_info:
        await issue_service.add_label_to_issue(
            async_db, async_test_repo.id, test_issue.issue_number, 999, async_test_user.id
        )
    assert "Label not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_add_label_to_issue_already_added(async_db: AsyncSession, async_test_repo: Repository, test_issue: Issue, test_label: Label, async_test_user):
    """测试为 Issue 添加已存在的标签"""
    # 先添加标签
    await issue_service.add_label_to_issue(
        async_db, async_test_repo.id, test_issue.issue_number, test_label.id, async_test_user.id
    )
    # 再次添加应该失败
    with pytest.raises(ValidationException) as exc_info:
        await issue_service.add_label_to_issue(
            async_db, async_test_repo.id, test_issue.issue_number, test_label.id, async_test_user.id
        )
    assert "Label already added to this issue" in str(exc_info.value)


@pytest.mark.asyncio
async def test_add_label_to_issue_issue_not_found(async_db: AsyncSession, async_test_repo: Repository, test_label: Label, async_test_user):
    """测试为不存在的 Issue 添加标签"""
    with pytest.raises(NotFoundException) as exc_info:
        await issue_service.add_label_to_issue(
            async_db, async_test_repo.id, 999, test_label.id, async_test_user.id
        )
    assert "Issue #999 not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_add_multiple_labels_to_issue(async_db: AsyncSession, async_test_repo: Repository, test_issue: Issue, test_label: Label, test_label2: Label, async_test_user):
    """测试为 Issue 添加多个标签"""
    # 添加第一个标签
    await issue_service.add_label_to_issue(
        async_db, async_test_repo.id, test_issue.issue_number, test_label.id, async_test_user.id
    )
    # 添加第二个标签
    updated_issue = await issue_service.add_label_to_issue(
        async_db, async_test_repo.id, test_issue.issue_number, test_label2.id, async_test_user.id
    )
    assert len(updated_issue["labels"]) == 2


@pytest.mark.asyncio
async def test_remove_label_from_issue_success(async_db: AsyncSession, async_test_repo: Repository, test_issue: Issue, test_label: Label, async_test_user):
    """测试成功从 Issue 移除标签"""
    # 先添加标签
    await issue_service.add_label_to_issue(
        async_db, async_test_repo.id, test_issue.issue_number, test_label.id, async_test_user.id
    )
    # 再移除标签
    updated_issue = await issue_service.remove_label_from_issue(
        async_db, async_test_repo.id, test_issue.issue_number, test_label.id, async_test_user.id
    )
    assert len(updated_issue["labels"]) == 0


@pytest.mark.asyncio
async def test_remove_label_from_issue_not_found(async_db: AsyncSession, async_test_repo: Repository, test_issue: Issue, async_test_user):
    """测试从 Issue 移除不存在的标签"""
    with pytest.raises(NotFoundException) as exc_info:
        await issue_service.remove_label_from_issue(
            async_db, async_test_repo.id, test_issue.issue_number, 999, async_test_user.id
        )
    assert "Label not found" in str(exc_info.value)
