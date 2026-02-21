"""
Commit Service 异步测试

测试提交服务层的所有功能
"""
import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models import BaseModel
from models.commit import Commit
from models.branch import Branch
from models.repository import Repository
from models.user import User
from services import commit_service
from exception import NotFoundException, ValidationException, ConflictException

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
async def test_branch(db: AsyncSession, test_repo: Repository):
    """创建测试分支"""
    branch = Branch(
        name="main",
        repository_id=test_repo.id,
        is_default=True
    )
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return branch


@pytest_asyncio.fixture
async def test_commit(db: AsyncSession, test_repo: Repository, test_branch: Branch):
    """创建测试提交"""
    commit = Commit(
        hash="abc123def456",
        repository_id=test_repo.id,
        branch_id=test_branch.id,
        author_name="Test Author",
        author_email="author@example.com",
        committer_name="Test Author",
        committer_email="author@example.com",
        commit_message="Initial commit"
    )
    db.add(commit)
    await db.commit()
    await db.refresh(commit)
    return commit


@pytest.mark.asyncio
async def test_get_commits(db: AsyncSession, test_repo: Repository, test_branch: Branch, test_commit: Commit):
    """测试获取仓库提交列表"""
    commits = await commit_service.get_commits(test_repo.id, db)
    assert len(commits) == 1
    assert commits[0].hash == test_commit.hash


@pytest.mark.asyncio
async def test_get_commits_empty(db: AsyncSession, test_repo: Repository):
    """测试获取空提交列表"""
    commits = await commit_service.get_commits(test_repo.id, db)
    assert len(commits) == 0


@pytest.mark.asyncio
async def test_get_commits_by_branch(db: AsyncSession, test_branch: Branch, test_commit: Commit):
    """测试获取分支提交列表"""
    commits = await commit_service.get_commits_by_branch(test_branch.id, db)
    assert len(commits) == 1
    assert commits[0].hash == test_commit.hash


@pytest.mark.asyncio
async def test_get_commit_by_hash(db: AsyncSession, test_repo: Repository, test_commit: Commit):
    """测试根据哈希获取提交"""
    commit = await commit_service.get_commit_by_hash(test_repo.id, test_commit.hash, db)
    assert commit.hash == test_commit.hash
    assert commit.commit_message == test_commit.commit_message


@pytest.mark.asyncio
async def test_get_commit_by_hash_not_found(db: AsyncSession, test_repo: Repository):
    """测试获取不存在的提交"""
    with pytest.raises(NotFoundException):
        await commit_service.get_commit_by_hash(test_repo.id, "nonexistent", db)


@pytest.mark.asyncio
async def test_get_commit_by_id(db: AsyncSession, test_commit: Commit):
    """测试根据ID获取提交"""
    commit = await commit_service.get_commit_by_id(test_commit.id, db)
    assert commit.id == test_commit.id
    assert commit.hash == test_commit.hash


@pytest.mark.asyncio
async def test_get_commit_by_id_not_found(db: AsyncSession):
    """测试获取不存在的提交ID"""
    with pytest.raises(NotFoundException):
        await commit_service.get_commit_by_id(9999, db)


@pytest.mark.asyncio
async def test_create_commit(db: AsyncSession, test_repo: Repository, test_branch: Branch):
    """测试创建提交"""
    commit_data = {
        "hash": "newhash123",
        "repository_id": test_repo.id,
        "branch_id": test_branch.id,
        "author_name": "New Author",
        "author_email": "new@example.com",
        "commit_message": "New commit"
    }
    commit = await commit_service.create_commit(commit_data, db)
    assert commit.hash == "newhash123"
    assert commit.commit_message == "New commit"


@pytest.mark.asyncio
async def test_create_commit_missing_fields(db: AsyncSession, test_repo: Repository, test_branch: Branch):
    """测试创建提交缺少必填字段"""
    commit_data = {
        "hash": "newhash123",
        "repository_id": test_repo.id,
        # 缺少 branch_id, author_name 等
    }
    with pytest.raises(ValidationException):
        await commit_service.create_commit(commit_data, db)


@pytest.mark.asyncio
async def test_create_commit_duplicate_hash(db: AsyncSession, test_repo: Repository, test_branch: Branch, test_commit: Commit):
    """测试创建重复哈希的提交"""
    commit_data = {
        "hash": test_commit.hash,  # 重复的哈希
        "repository_id": test_repo.id,
        "branch_id": test_branch.id,
        "author_name": "New Author",
        "author_email": "new@example.com",
        "commit_message": "New commit"
    }
    with pytest.raises(ConflictException):
        await commit_service.create_commit(commit_data, db)


@pytest.mark.asyncio
async def test_create_commit_invalid_branch(db: AsyncSession, test_repo: Repository):
    """测试创建提交使用不存在的分支"""
    commit_data = {
        "hash": "newhash123",
        "repository_id": test_repo.id,
        "branch_id": 9999,  # 不存在的分支
        "author_name": "New Author",
        "author_email": "new@example.com",
        "commit_message": "New commit"
    }
    with pytest.raises(NotFoundException):
        await commit_service.create_commit(commit_data, db)


@pytest.mark.asyncio
async def test_get_commit_history(db: AsyncSession, test_repo: Repository, test_branch: Branch, test_commit: Commit):
    """测试获取提交历史"""
    history = await commit_service.get_commit_history(test_repo.id, db)
    assert len(history) == 1
    assert history[0].hash == test_commit.hash


@pytest.mark.asyncio
async def test_get_commit_history_by_branch(db: AsyncSession, test_repo: Repository, test_branch: Branch, test_commit: Commit):
    """测试获取指定分支的提交历史"""
    history = await commit_service.get_commit_history(test_repo.id, db, branch_name=test_branch.name)
    assert len(history) == 1
    assert history[0].hash == test_commit.hash


@pytest.mark.asyncio
async def test_count_repo_commits(db: AsyncSession, test_repo: Repository, test_commit: Commit):
    """测试统计仓库提交数量"""
    count = await commit_service.count_repo_commits(test_repo.id, db)
    assert count == 1


@pytest.mark.asyncio
async def test_count_branch_commits(db: AsyncSession, test_branch: Branch, test_commit: Commit):
    """测试统计分支提交数量"""
    count = await commit_service.count_branch_commits(test_branch.id, db)
    assert count == 1


@pytest.mark.asyncio
async def test_get_latest_commit(db: AsyncSession, test_repo: Repository, test_commit: Commit):
    """测试获取最新提交"""
    commit = await commit_service.get_latest_commit(test_repo.id, db)
    assert commit.hash == test_commit.hash


@pytest.mark.asyncio
async def test_get_latest_commit_not_found(db: AsyncSession, test_repo: Repository):
    """测试获取最新提交（无提交记录）"""
    with pytest.raises(NotFoundException):
        await commit_service.get_latest_commit(test_repo.id, db)


@pytest.mark.asyncio
async def test_get_latest_commit_by_branch(db: AsyncSession, test_branch: Branch, test_commit: Commit):
    """测试获取分支最新提交"""
    commit = await commit_service.get_latest_commit_by_branch(test_branch.id, db)
    assert commit.hash == test_commit.hash


@pytest.mark.asyncio
async def test_search_commits(db: AsyncSession, test_repo: Repository, test_commit: Commit):
    """测试搜索提交"""
    results = await commit_service.search_commits(test_repo.id, "Initial", db)
    assert len(results) == 1
    assert results[0].hash == test_commit.hash


@pytest.mark.asyncio
async def test_search_commits_no_match(db: AsyncSession, test_repo: Repository, test_commit: Commit):
    """测试搜索提交无匹配"""
    results = await commit_service.search_commits(test_repo.id, "nonexistent", db)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_get_commits_by_author(db: AsyncSession, test_repo: Repository, test_commit: Commit):
    """测试根据作者获取提交"""
    results = await commit_service.get_commits_by_author(test_repo.id, "author@example.com", db)
    assert len(results) == 1
    assert results[0].hash == test_commit.hash
