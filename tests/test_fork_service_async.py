"""
仓库 Fork 服务层异步测试

测试 Fork 仓库的创建、查询和同步功能
"""
import pytest
import pytest_asyncio
import os
import tempfile
import shutil
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from models.user import User
from services import fork_service
from core.exception import NotFoundException, ValidationException, AuthorizationException


@pytest_asyncio.fixture
async def temp_repo_dir():
    """创建临时仓库目录"""
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@pytest_asyncio.fixture
async def source_git_repo(temp_repo_dir):
    """创建源 Git 仓库"""
    import subprocess

    repo_path = os.path.join(temp_repo_dir, "source", "testuser", "test-repo")
    os.makedirs(repo_path, exist_ok=True)

    # 初始化 Git 仓库
    subprocess.run(["git", "init", "--bare"], cwd=repo_path, check=True, capture_output=True)

    return repo_path


# =============================================================================
# Fork 创建测试
# =============================================================================

@pytest.mark.asyncio
async def test_fork_repository_success(async_db: AsyncSession, async_test_user, async_test_repo, temp_repo_dir, source_git_repo):
    """测试成功 Fork 仓库"""
    # 更新测试仓库的路径为实际的 Git 仓库路径
    async_test_repo.path = "source/testuser/test-repo"
    await async_db.commit()

    forked = await fork_service.fork_repository(
        db=async_db,
        source_repository_id=async_test_repo.id,
        user_id=async_test_user.id,
        repo_root=temp_repo_dir
    )

    assert forked["name"] == "test-repo"
    assert forked["path"] == "testuser/test-repo"
    assert forked["is_fork"] is True
    assert forked["forked_from_id"] == async_test_repo.id
    assert "source" in forked


@pytest.mark.asyncio
async def test_fork_repository_with_custom_name(async_db: AsyncSession, async_test_user, async_test_repo, temp_repo_dir, source_git_repo):
    """测试使用自定义名称 Fork 仓库"""
    async_test_repo.path = "source/testuser/test-repo"
    await async_db.commit()

    forked = await fork_service.fork_repository(
        db=async_db,
        source_repository_id=async_test_repo.id,
        user_id=async_test_user.id,
        name="my-fork",
        repo_root=temp_repo_dir
    )

    assert forked["name"] == "my-fork"
    assert forked["path"] == "testuser/my-fork"


@pytest.mark.asyncio
async def test_fork_repository_with_custom_description(async_db: AsyncSession, async_test_user, async_test_repo, temp_repo_dir, source_git_repo):
    """测试使用自定义描述 Fork 仓库"""
    async_test_repo.path = "source/testuser/test-repo"
    await async_db.commit()

    forked = await fork_service.fork_repository(
        db=async_db,
        source_repository_id=async_test_repo.id,
        user_id=async_test_user.id,
        description="My custom fork description",
        repo_root=temp_repo_dir
    )

    assert forked["description"] == "My custom fork description"


@pytest.mark.asyncio
async def test_fork_repository_private(async_db: AsyncSession, async_test_user, async_test_repo, temp_repo_dir, source_git_repo):
    """测试 Fork 为私有仓库"""
    async_test_repo.path = "source/testuser/test-repo"
    await async_db.commit()

    forked = await fork_service.fork_repository(
        db=async_db,
        source_repository_id=async_test_repo.id,
        user_id=async_test_user.id,
        is_public=False,
        repo_root=temp_repo_dir
    )

    assert forked["is_public"] is False


@pytest.mark.asyncio
async def test_fork_repository_not_found(async_db: AsyncSession, async_test_user):
    """测试 Fork 不存在的仓库"""
    with pytest.raises(NotFoundException) as exc_info:
        await fork_service.fork_repository(
            db=async_db,
            source_repository_id=99999,
            user_id=async_test_user.id
        )

    assert "Source repository not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fork_repository_duplicate(async_db: AsyncSession, async_test_user, async_test_repo, temp_repo_dir, source_git_repo):
    """测试重复 Fork 同一仓库"""
    async_test_repo.path = "source/testuser/test-repo"
    await async_db.commit()

    # 第一次 Fork
    await fork_service.fork_repository(
        db=async_db,
        source_repository_id=async_test_repo.id,
        user_id=async_test_user.id,
        repo_root=temp_repo_dir
    )

    # 第二次 Fork 应该失败
    with pytest.raises(ValidationException) as exc_info:
        await fork_service.fork_repository(
            db=async_db,
            source_repository_id=async_test_repo.id,
            user_id=async_test_user.id,
            repo_root=temp_repo_dir
        )

    assert "already forked" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fork_repository_path_conflict(async_db: AsyncSession, async_test_user, async_test_repo, temp_repo_dir, source_git_repo):
    """测试 Fork 时路径冲突"""
    async_test_repo.path = "source/testuser/test-repo"
    await async_db.commit()

    # 创建一个同名仓库
    existing_repo = Repository(
        name="test-repo",
        description="Existing repo",
        owner_id=async_test_user.id,
        is_public=True,
        path="testuser/test-repo"
    )
    async_db.add(existing_repo)
    await async_db.commit()

    with pytest.raises(ValidationException) as exc_info:
        await fork_service.fork_repository(
            db=async_db,
            source_repository_id=async_test_repo.id,
            user_id=async_test_user.id,
            repo_root=temp_repo_dir
        )

    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fork_private_repository_no_permission(async_db: AsyncSession, async_another_user, async_test_repo):
    """测试无权限 Fork 私有仓库"""
    # 将仓库设为私有
    async_test_repo.is_public = False
    await async_db.commit()

    with pytest.raises(AuthorizationException) as exc_info:
        await fork_service.fork_repository(
            db=async_db,
            source_repository_id=async_test_repo.id,
            user_id=async_another_user.id
        )

    assert "Not authorized" in str(exc_info.value)


# =============================================================================
# Fork 查询测试
# =============================================================================

@pytest.mark.asyncio
async def test_get_repository_forks(async_db: AsyncSession, async_test_user, async_test_repo, temp_repo_dir, source_git_repo):
    """测试获取仓库的所有 Fork"""
    async_test_repo.path = "source/testuser/test-repo"
    await async_db.commit()

    # 创建多个 Fork
    for i in range(3):
        user = User(
            username=f"forker{i}",
            email=f"forker{i}@example.com",
            password="hashed_password",
            full_name=f"Forker {i}",
            is_active=True
        )
        async_db.add(user)
        await async_db.commit()
        await async_db.refresh(user)

        await fork_service.fork_repository(
            db=async_db,
            source_repository_id=async_test_repo.id,
            user_id=user.id,
            repo_root=temp_repo_dir
        )

    result = await fork_service.get_repository_forks(
        db=async_db,
        repository_id=async_test_repo.id
    )

    assert result["total"] == 3
    assert len(result["items"]) == 3


@pytest.mark.asyncio
async def test_get_repository_forks_not_found(async_db: AsyncSession):
    """测试获取不存在的仓库的 Fork"""
    with pytest.raises(NotFoundException) as exc_info:
        await fork_service.get_repository_forks(
            db=async_db,
            repository_id=99999
        )

    assert "Repository not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_user_forks(async_db: AsyncSession, async_test_user, async_test_repo, temp_repo_dir, source_git_repo):
    """测试获取用户的所有 Fork"""
    async_test_repo.path = "source/testuser/test-repo"
    await async_db.commit()

    # 创建 Fork
    await fork_service.fork_repository(
        db=async_db,
        source_repository_id=async_test_repo.id,
        user_id=async_test_user.id,
        repo_root=temp_repo_dir
    )

    result = await fork_service.get_user_forks(
        db=async_db,
        user_id=async_test_user.id
    )

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["is_fork"] is True


@pytest.mark.asyncio
async def test_get_fork_source(async_db: AsyncSession, async_test_user, async_test_repo, temp_repo_dir, source_git_repo):
    """测试获取 Fork 的源仓库"""
    async_test_repo.path = "source/testuser/test-repo"
    await async_db.commit()

    # 创建 Fork
    forked = await fork_service.fork_repository(
        db=async_db,
        source_repository_id=async_test_repo.id,
        user_id=async_test_user.id,
        repo_root=temp_repo_dir
    )

    source = await fork_service.get_fork_source(
        db=async_db,
        repository_id=forked["id"]
    )

    assert source is not None
    assert source["id"] == async_test_repo.id
    assert source["name"] == "test-repo"


@pytest.mark.asyncio
async def test_get_fork_source_not_fork(async_db: AsyncSession, async_test_repo):
    """测试获取非 Fork 仓库的源仓库"""
    source = await fork_service.get_fork_source(
        db=async_db,
        repository_id=async_test_repo.id
    )

    assert source is None


@pytest.mark.asyncio
async def test_get_fork_source_not_found(async_db: AsyncSession):
    """测试获取不存在的仓库的源仓库"""
    with pytest.raises(NotFoundException) as exc_info:
        await fork_service.get_fork_source(
            db=async_db,
            repository_id=99999
        )

    assert "Repository not found" in str(exc_info.value)


# =============================================================================
# Fork 同步测试
# =============================================================================

@pytest.mark.asyncio
async def test_sync_fork_not_fork(async_db: AsyncSession, async_test_repo):
    """测试同步非 Fork 仓库"""
    with pytest.raises(ValidationException) as exc_info:
        await fork_service.sync_fork(
            db=async_db,
            repository_id=async_test_repo.id,
            user_id=async_test_repo.owner_id
        )

    assert "not a fork" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sync_fork_no_permission(async_db: AsyncSession, async_another_user, async_test_repo, temp_repo_dir, source_git_repo):
    """测试无权限同步 Fork"""
    async_test_repo.path = "source/testuser/test-repo"
    await async_db.commit()

    # 创建 Fork
    forked = await fork_service.fork_repository(
        db=async_db,
        source_repository_id=async_test_repo.id,
        user_id=async_test_repo.owner_id,
        repo_root=temp_repo_dir
    )

    with pytest.raises(AuthorizationException) as exc_info:
        await fork_service.sync_fork(
            db=async_db,
            repository_id=forked["id"],
            user_id=async_another_user.id
        )

    assert "Not authorized" in str(exc_info.value)


# =============================================================================
# 辅助函数测试
# =============================================================================

def test_build_fork_response():
    """测试构建 Fork 响应"""
    from datetime import datetime

    fork_repo = Repository(
        id=1,
        name="forked-repo",
        path="user/forked-repo",
        description="A fork",
        is_public=True,
        owner_id=2,
        default_branch="main",
        forked_from_id=10,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 2)
    )

    source_repo = Repository(
        id=10,
        name="original-repo",
        path="original/original-repo",
        owner_id=5
    )

    response = fork_service.build_fork_response(fork_repo, source_repo)

    assert response["id"] == 1
    assert response["name"] == "forked-repo"
    assert response["is_fork"] is True
    assert response["forked_from_id"] == 10
    assert response["source"]["id"] == 10
    assert response["source"]["name"] == "original-repo"


def test_repository_is_fork():
    """测试 Repository.is_fork 方法"""
    fork_repo = Repository(forked_from_id=10)
    normal_repo = Repository(forked_from_id=None)

    assert fork_repo.is_fork() is True
    assert normal_repo.is_fork() is False


def test_repository_get_fork_path():
    """测试 Repository.get_fork_path 方法"""
    repo = Repository(name="test-repo")
    path = repo.get_fork_path("newowner")

    assert path == "newowner/test-repo"
