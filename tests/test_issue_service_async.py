"""
Issue Service 异步测试

测试 Issue 服务层的所有功能
"""
import pytest
import pytest_asyncio
from datetime import datetime
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


@pytest.mark.asyncio
async def test_create_issue(db: AsyncSession, test_repo: Repository, test_user: User):
    """测试创建 Issue"""
    issue = await issue_service.create_issue(
        db, test_repo.id, test_user.id,
        title="New Issue",
        description="New description",
        priority="high"
    )
    assert issue["title"] == "New Issue"
    assert issue["status"] == "open"
    assert issue["priority"] == "high"


@pytest.mark.asyncio
async def test_create_issue_empty_title(db: AsyncSession, test_repo: Repository, test_user: User):
    """测试创建 Issue 空标题"""
    with pytest.raises(ValidationException):
        await issue_service.create_issue(
            db, test_repo.id, test_user.id,
            title="",
            description="Description"
        )


@pytest.mark.asyncio
async def test_create_issue_invalid_priority(db: AsyncSession, test_repo: Repository, test_user: User):
    """测试创建 Issue 无效优先级"""
    with pytest.raises(ValidationException):
        await issue_service.create_issue(
            db, test_repo.id, test_user.id,
            title="New Issue",
            priority="invalid"
        )


@pytest.mark.asyncio
async def test_get_issue_not_found(db: AsyncSession, test_repo: Repository):
    """测试获取不存在的 Issue"""
    with pytest.raises(NotFoundException):
        await issue_service.get_issue(db, test_repo.id, 999)


@pytest.mark.asyncio
async def test_update_issue_not_found(db: AsyncSession, test_repo: Repository, test_user: User):
    """测试更新不存在的 Issue"""
    with pytest.raises(NotFoundException):
        await issue_service.update_issue(
            db, test_repo.id, 999, test_user.id,
            title="Updated Title"
        )


@pytest.mark.asyncio
async def test_close_issue(db: AsyncSession, test_repo: Repository, test_issue: Issue, test_user: User):
    """测试关闭 Issue"""
    closed = await issue_service.close_issue(
        db, test_repo.id, test_issue.issue_number, test_user.id
    )
    assert closed["status"] == "closed"


@pytest.mark.asyncio
async def test_close_issue_already_closed(db: AsyncSession, test_repo: Repository, test_issue: Issue, test_user: User):
    """测试关闭已关闭的 Issue"""
    await issue_service.close_issue(db, test_repo.id, test_issue.issue_number, test_user.id)
    with pytest.raises(ValidationException):
        await issue_service.close_issue(db, test_repo.id, test_issue.issue_number, test_user.id)


@pytest.mark.asyncio
async def test_reopen_issue(db: AsyncSession, test_repo: Repository, test_issue: Issue, test_user: User):
    """测试重新打开 Issue"""
    # 先关闭
    await issue_service.close_issue(db, test_repo.id, test_issue.issue_number, test_user.id)
    # 再重新打开
    reopened = await issue_service.reopen_issue(
        db, test_repo.id, test_issue.issue_number, test_user.id
    )
    assert reopened["status"] == "open"


@pytest.mark.asyncio
async def test_create_issue_comment_empty_content(db: AsyncSession, test_repo: Repository, test_issue: Issue, test_user: User):
    """测试添加空内容评论"""
    with pytest.raises(ValidationException):
        await issue_service.create_issue_comment(
            db, test_repo.id, test_issue.issue_number, test_user.id,
            content=""
        )


@pytest.mark.asyncio
async def test_create_label(db: AsyncSession, test_repo: Repository):
    """测试创建标签"""
    label = await issue_service.create_label(
        db, test_repo.id, "feature", "#00ff00"
    )
    assert label["name"] == "feature"
    assert label["color"] == "#00ff00"


@pytest.mark.asyncio
async def test_create_label_empty_name(db: AsyncSession, test_repo: Repository):
    """测试创建空名称标签"""
    with pytest.raises(ValidationException):
        await issue_service.create_label(db, test_repo.id, "", "#00ff00")


@pytest.mark.asyncio
async def test_list_labels(db: AsyncSession, test_repo: Repository, test_label: Label):
    """测试获取标签列表"""
    labels = await issue_service.list_labels(db, test_repo.id)
    assert len(labels) == 1
    assert labels[0]["name"] == test_label.name


@pytest.mark.asyncio
async def test_update_label(db: AsyncSession, test_repo: Repository, test_label: Label):
    """测试更新标签"""
    updated = await issue_service.update_label(
        db, test_repo.id, test_label.id, "bug-fixed", "#0000ff"
    )
    assert updated["name"] == "bug-fixed"
    assert updated["color"] == "#0000ff"


@pytest.mark.asyncio
async def test_delete_label(db: AsyncSession, test_repo: Repository, test_label: Label):
    """测试删除标签"""
    await issue_service.delete_label(db, test_repo.id, test_label.id)
    # 验证标签已被删除
    labels = await issue_service.list_labels(db, test_repo.id)
    assert len(labels) == 0
