"""
Issue 标签管理功能异步测试

测试 Issue 标签管理相关的核心功能
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models import BaseModel
from models.issue import Issue, Label
from models.repository import Repository
from models.user import User
from services import issue_service
from exception import NotFoundException, ValidationException

# 使用内存数据库进行测试
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db():
    """创建测试数据库会话"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(db: AsyncSession):
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        password="hashed_password",
        full_name="Test User",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_repo(db: AsyncSession, test_user: User):
    """创建测试仓库"""
    repo = Repository(
        name="test-repo",
        description="Test repository",
        owner_id=test_user.id,
        is_public=True,
        path="testuser/test-repo"
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    return repo


@pytest_asyncio.fixture
async def test_issue(db: AsyncSession, test_repo: Repository, test_user: User):
    """创建测试 Issue"""
    issue = Issue(
        repository_id=test_repo.id,
        issue_number=1,
        title="Test Issue",
        description="This is a test issue",
        author_id=test_user.id,
        status="open",
        priority="medium"
    )
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    return issue


@pytest_asyncio.fixture
async def test_label(db: AsyncSession, test_repo: Repository):
    """创建测试标签"""
    label = Label(
        name="bug",
        color="#ff0000",
        repository_id=test_repo.id
    )
    db.add(label)
    await db.commit()
    await db.refresh(label)
    return label


@pytest_asyncio.fixture
async def test_label2(db: AsyncSession, test_repo: Repository):
    """创建第二个测试标签"""
    label = Label(
        name="feature",
        color="#00ff00",
        repository_id=test_repo.id
    )
    db.add(label)
    await db.commit()
    await db.refresh(label)
    return label


@pytest.mark.asyncio
async def test_add_label_to_issue_success(db: AsyncSession, test_repo: Repository, test_issue: Issue, test_label: Label, test_user: User):
    """测试成功为 Issue 添加标签"""
    updated_issue = await issue_service.add_label_to_issue(
        db, test_repo.id, test_issue.issue_number, test_label.id, test_user.id
    )
    assert len(updated_issue["labels"]) == 1
    assert updated_issue["labels"][0]["name"] == "bug"


@pytest.mark.asyncio
async def test_add_label_to_issue_not_found(db: AsyncSession, test_repo: Repository, test_issue: Issue, test_user: User):
    """测试为 Issue 添加不存在的标签"""
    with pytest.raises(NotFoundException) as exc_info:
        await issue_service.add_label_to_issue(
            db, test_repo.id, test_issue.issue_number, 999, test_user.id
        )
    assert "Label not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_add_label_to_issue_already_added(db: AsyncSession, test_repo: Repository, test_issue: Issue, test_label: Label, test_user: User):
    """测试为 Issue 添加已存在的标签"""
    # 先添加标签
    await issue_service.add_label_to_issue(
        db, test_repo.id, test_issue.issue_number, test_label.id, test_user.id
    )
    # 再次添加应该失败
    with pytest.raises(ValidationException) as exc_info:
        await issue_service.add_label_to_issue(
            db, test_repo.id, test_issue.issue_number, test_label.id, test_user.id
        )
    assert "Label already added to this issue" in str(exc_info.value)


@pytest.mark.asyncio
async def test_add_label_to_issue_issue_not_found(db: AsyncSession, test_repo: Repository, test_label: Label, test_user: User):
    """测试为不存在的 Issue 添加标签"""
    with pytest.raises(NotFoundException) as exc_info:
        await issue_service.add_label_to_issue(
            db, test_repo.id, 999, test_label.id, test_user.id
        )
    assert "Issue #999 not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_add_multiple_labels_to_issue(db: AsyncSession, test_repo: Repository, test_issue: Issue, test_label: Label, test_label2: Label, test_user: User):
    """测试为 Issue 添加多个标签"""
    # 添加第一个标签
    await issue_service.add_label_to_issue(
        db, test_repo.id, test_issue.issue_number, test_label.id, test_user.id
    )
    # 添加第二个标签
    updated_issue = await issue_service.add_label_to_issue(
        db, test_repo.id, test_issue.issue_number, test_label2.id, test_user.id
    )
    assert len(updated_issue["labels"]) == 2


@pytest.mark.asyncio
async def test_remove_label_from_issue_success(db: AsyncSession, test_repo: Repository, test_issue: Issue, test_label: Label, test_user: User):
    """测试成功从 Issue 移除标签"""
    # 先添加标签
    await issue_service.add_label_to_issue(
        db, test_repo.id, test_issue.issue_number, test_label.id, test_user.id
    )
    # 再移除标签
    updated_issue = await issue_service.remove_label_from_issue(
        db, test_repo.id, test_issue.issue_number, test_label.id, test_user.id
    )
    assert len(updated_issue["labels"]) == 0


@pytest.mark.asyncio
async def test_remove_label_from_issue_not_found(db: AsyncSession, test_repo: Repository, test_issue: Issue, test_user: User):
    """测试从 Issue 移除不存在的标签"""
    with pytest.raises(NotFoundException) as exc_info:
        await issue_service.remove_label_from_issue(
            db, test_repo.id, test_issue.issue_number, 999, test_user.id
        )
    assert "Label not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_remove_label_from_issue_not_in_issue(db: AsyncSession, test_repo: Repository, test_issue: Issue, test_label: Label, test_user: User):
    """测试从 Issue 移除未添加的标签"""
    with pytest.raises(ValidationException) as exc_info:
        await issue_service.remove_label_from_issue(
            db, test_repo.id, test_issue.issue_number, test_label.id, test_user.id
        )
    assert "Label not found in this issue" in str(exc_info.value)


@pytest.mark.asyncio
async def test_remove_label_from_issue_issue_not_found(db: AsyncSession, test_repo: Repository, test_label: Label, test_user: User):
    """测试从不存在的 Issue 移除标签"""
    with pytest.raises(NotFoundException) as exc_info:
        await issue_service.remove_label_from_issue(
            db, test_repo.id, 999, test_label.id, test_user.id
        )
    assert "Issue #999 not found" in str(exc_info.value)
