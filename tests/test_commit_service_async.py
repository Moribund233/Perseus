"""
Commit Service 异步测试

测试提交服务层的所有功能
"""
import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from models.commit import Commit
from models.branch import Branch
from models.repository import Repository
from services import commit_service
from core.exception import NotFoundException, ValidationException, ConflictException


@pytest_asyncio.fixture
async def test_branch(async_db: AsyncSession, async_test_repo: Repository):
    """创建测试分支"""
    branch = Branch(
        name="main",
        repository_id=async_test_repo.id,
        is_default=True
    )
    async_db.add(branch)
    await async_db.commit()
    await async_db.refresh(branch)
    return branch


@pytest_asyncio.fixture
async def test_commit(async_db: AsyncSession, async_test_repo: Repository, test_branch: Branch):
    """创建测试提交"""
    commit = Commit(
        hash="abc123def456",
        repository_id=async_test_repo.id,
        branch_id=test_branch.id,
        author_name="Test Author",
        author_email="author@example.com",
        committer_name="Test Author",
        committer_email="author@example.com",
        commit_message="Initial commit"
    )
    async_db.add(commit)
    await async_db.commit()
    await async_db.refresh(commit)
    return commit


@pytest.mark.asyncio
async def test_get_commits(async_db: AsyncSession, async_test_repo: Repository, test_branch: Branch, test_commit: Commit):
    """测试获取仓库提交列表"""
    commits = await commit_service.get_commits(async_test_repo.id, async_db)
    assert len(commits) == 1
    assert commits[0].hash == test_commit.hash


@pytest.mark.asyncio
async def test_get_commits_empty(async_db: AsyncSession, async_test_repo: Repository):
    """测试获取空提交列表"""
    commits = await commit_service.get_commits(async_test_repo.id, async_db)
    assert len(commits) == 0


@pytest.mark.asyncio
async def test_get_commits_by_branch(async_db: AsyncSession, test_branch: Branch, test_commit: Commit):
    """测试获取分支提交列表"""
    commits = await commit_service.get_commits_by_branch(test_branch.id, async_db)
    assert len(commits) == 1
    assert commits[0].hash == test_commit.hash


@pytest.mark.asyncio
async def test_get_commit_by_hash(async_db: AsyncSession, async_test_repo: Repository, test_commit: Commit):
    """测试根据哈希获取提交"""
    commit = await commit_service.get_commit_by_hash(async_test_repo.id, test_commit.hash, async_db)
    assert commit.hash == test_commit.hash
    assert commit.commit_message == test_commit.commit_message


@pytest.mark.asyncio
async def test_get_commit_by_hash_not_found(async_db: AsyncSession, async_test_repo: Repository):
    """测试获取不存在的提交"""
    with pytest.raises(NotFoundException):
        await commit_service.get_commit_by_hash(async_test_repo.id, "nonexistent", async_db)


@pytest.mark.asyncio
async def test_get_commit_by_id(async_db: AsyncSession, test_commit: Commit):
    """测试根据ID获取提交"""
    commit = await commit_service.get_commit_by_id(test_commit.id, async_db)
    assert commit.id == test_commit.id
    assert commit.hash == test_commit.hash


@pytest.mark.asyncio
async def test_get_commit_by_id_not_found(async_db: AsyncSession):
    """测试获取不存在的提交ID"""
    with pytest.raises(NotFoundException):
        await commit_service.get_commit_by_id(9999, async_db)


@pytest.mark.asyncio
async def test_create_commit(async_db: AsyncSession, async_test_repo: Repository, test_branch: Branch):
    """测试创建提交"""
    commit_data = {
        "hash": "newhash123",
        "repository_id": async_test_repo.id,
        "branch_id": test_branch.id,
        "author_name": "New Author",
        "author_email": "new@example.com",
        "commit_message": "New commit"
    }
    commit = await commit_service.create_commit(commit_data, async_db)
    assert commit.hash == "newhash123"
    assert commit.commit_message == "New commit"


@pytest.mark.asyncio
async def test_create_commit_missing_fields(async_db: AsyncSession, async_test_repo: Repository, test_branch: Branch):
    """测试创建提交缺少必填字段"""
    commit_data = {
        "hash": "newhash123",
        "repository_id": async_test_repo.id,
        # 缺少 branch_id, author_name 等
    }
    with pytest.raises(ValidationException):
        await commit_service.create_commit(commit_data, async_db)


@pytest.mark.asyncio
async def test_create_commit_duplicate_hash(async_db: AsyncSession, async_test_repo: Repository, test_branch: Branch, test_commit: Commit):
    """测试创建重复哈希的提交"""
    commit_data = {
        "hash": test_commit.hash,  # 重复的哈希
        "repository_id": async_test_repo.id,
        "branch_id": test_branch.id,
        "author_name": "New Author",
        "author_email": "new@example.com",
        "commit_message": "New commit"
    }
    with pytest.raises(ConflictException):
        await commit_service.create_commit(commit_data, async_db)


@pytest.mark.asyncio
async def test_create_commit_invalid_branch(async_db: AsyncSession, async_test_repo: Repository):
    """测试创建提交使用不存在的分支"""
    commit_data = {
        "hash": "newhash123",
        "repository_id": async_test_repo.id,
        "branch_id": 9999,  # 不存在的分支
        "author_name": "New Author",
        "author_email": "new@example.com",
        "commit_message": "New commit"
    }
    with pytest.raises(NotFoundException):
        await commit_service.create_commit(commit_data, async_db)


@pytest.mark.asyncio
async def test_get_commit_history(async_db: AsyncSession, async_test_repo: Repository, test_branch: Branch, test_commit: Commit):
    """测试获取提交历史"""
    history = await commit_service.get_commit_history(async_test_repo.id, async_db)
    assert len(history) == 1
    assert history[0].hash == test_commit.hash


@pytest.mark.asyncio
async def test_get_commit_history_by_branch(async_db: AsyncSession, async_test_repo: Repository, test_branch: Branch, test_commit: Commit):
    """测试获取指定分支的提交历史"""
    history = await commit_service.get_commit_history(async_test_repo.id, async_db, branch_name=test_branch.name)
    assert len(history) == 1
    assert history[0].hash == test_commit.hash


@pytest.mark.asyncio
async def test_count_repo_commits(async_db: AsyncSession, async_test_repo: Repository, test_commit: Commit):
    """测试统计仓库提交数量"""
    count = await commit_service.count_repo_commits(async_test_repo.id, async_db)
    assert count == 1


@pytest.mark.asyncio
async def test_count_branch_commits(async_db: AsyncSession, test_branch: Branch, test_commit: Commit):
    """测试统计分支提交数量"""
    count = await commit_service.count_branch_commits(test_branch.id, async_db)
    assert count == 1


@pytest.mark.asyncio
async def test_get_latest_commit(async_db: AsyncSession, async_test_repo: Repository, test_commit: Commit):
    """测试获取最新提交"""
    commit = await commit_service.get_latest_commit(async_test_repo.id, async_db)
    assert commit.hash == test_commit.hash


@pytest.mark.asyncio
async def test_get_latest_commit_not_found(async_db: AsyncSession, async_test_repo: Repository):
    """测试获取最新提交（无提交记录）"""
    with pytest.raises(NotFoundException):
        await commit_service.get_latest_commit(async_test_repo.id, async_db)


@pytest.mark.asyncio
async def test_get_latest_commit_by_branch(async_db: AsyncSession, test_branch: Branch, test_commit: Commit):
    """测试获取分支最新提交"""
    commit = await commit_service.get_latest_commit_by_branch(test_branch.id, async_db)
    assert commit.hash == test_commit.hash


@pytest.mark.asyncio
async def test_search_commits(async_db: AsyncSession, async_test_repo: Repository, test_commit: Commit):
    """测试搜索提交"""
    results = await commit_service.search_commits(async_test_repo.id, "Initial", async_db)
    assert len(results) == 1
    assert results[0].hash == test_commit.hash


@pytest.mark.asyncio
async def test_search_commits_no_match(async_db: AsyncSession, async_test_repo: Repository, test_commit: Commit):
    """测试搜索提交无匹配"""
    results = await commit_service.search_commits(async_test_repo.id, "nonexistent", async_db)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_get_commits_by_author(async_db: AsyncSession, async_test_repo: Repository, test_commit: Commit):
    """测试根据作者获取提交"""
    results = await commit_service.get_commits_by_author(async_test_repo.id, "author@example.com", async_db)
    assert len(results) == 1
    assert results[0].hash == test_commit.hash
