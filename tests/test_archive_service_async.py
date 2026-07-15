import uuid
"""
测试仓库归档/取消归档功能
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from services import repository_service
from core.exception import NotFoundException


@pytest_asyncio.fixture
async def test_repo(async_db: AsyncSession, async_test_user):
    """
    创建测试用的归档仓库
    
    Args:
        async_db: 异步数据库会话
        async_test_user: 异步测试用户
        
    Returns:
        Repository: 测试仓库实例
    """
    repo = Repository(
        name="archive-test-repo",
        path=f"{async_test_user.username}/archive-test-repo",
        description="Archive test",
        owner_id=async_test_user.id,
        is_public=True,
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)
    return repo


@pytest.mark.asyncio
async def test_archive_repository(async_db: AsyncSession, test_repo):
    """
    测试归档仓库
    
    Args:
        async_db: 异步数据库会话
        test_repo: 测试仓库实例
    """
    result = await repository_service.archive_repository(test_repo.id, async_db)
    assert result["is_archived"] is True


@pytest.mark.asyncio
async def test_unarchive_repository(async_db: AsyncSession, test_repo):
    """
    测试取消归档仓库
    
    Args:
        async_db: 异步数据库会话
        test_repo: 测试仓库实例
    """
    await repository_service.archive_repository(test_repo.id, async_db)
    result = await repository_service.unarchive_repository(test_repo.id, async_db)
    assert result["is_archived"] is False


@pytest.mark.asyncio
async def test_archive_nonexistent_repo(async_db: AsyncSession):
    """
    测试归档不存在的仓库
    
    Args:
        async_db: 异步数据库会话
    """
    with pytest.raises(NotFoundException):
        await repository_service.archive_repository(uuid.UUID("00000000-0000-0000-0000-000000000000"), async_db)


@pytest.mark.asyncio
async def test_archive_filter(async_db: AsyncSession, async_test_user):
    """
    测试归档仓库从列表中排除
    
    Args:
        async_db: 异步数据库会话
        async_test_user: 异步测试用户
    """
    repo1 = Repository(name="repo1", path="u/repo1", owner_id=async_test_user.id, is_public=True)
    repo2 = Repository(name="repo2", path="u/repo2", owner_id=async_test_user.id, is_public=True, is_archived=True)
    async_db.add_all([repo1, repo2])
    await async_db.commit()

    result = await repository_service.get_repositories(async_db)
    repo_names = [r["name"] for r in result["items"]]
    assert "repo2" not in repo_names
