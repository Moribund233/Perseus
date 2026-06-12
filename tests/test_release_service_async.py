"""
Release 服务层异步测试

测试 Release 和 Git 标签管理相关的核心功能
"""
import pytest
import pytest_asyncio
import os
import tempfile
import subprocess
from sqlalchemy.ext.asyncio import AsyncSession

from models.release import Release, ReleaseAsset
from models.repository import Repository
from services import release_service
from services.release_service import (
    _create_git_tag, _delete_git_tag, list_git_tags, get_git_tag
)
from core.exception import NotFoundException, ValidationException


@pytest.fixture
def temp_repo():
    """创建临时 Git 仓库"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = os.path.join(tmpdir, "test-repo.git")
        # 初始化 bare 仓库
        subprocess.run(
            ["git", "init", "--bare", repo_path],
            check=True,
            capture_output=True
        )

        # 配置 bare 仓库的 git identity（创建附注标签时需要）
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True
        )

        # 创建临时工作目录用于提交
        work_dir = os.path.join(tmpdir, "work")
        os.makedirs(work_dir)

        # 克隆 bare 仓库
        subprocess.run(
            ["git", "clone", repo_path, work_dir],
            check=True,
            capture_output=True
        )

        # 配置 git
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=work_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=work_dir,
            check=True,
            capture_output=True
        )

        # 创建初始提交
        with open(os.path.join(work_dir, "README.md"), "w") as f:
            f.write("# Test Repository\n")

        subprocess.run(
            ["git", "add", "."],
            cwd=work_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=work_dir,
            check=True,
            capture_output=True
        )

        # 确定默认分支名称
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        default_branch = result.stdout.strip()

        subprocess.run(
            ["git", "push", "origin", default_branch],
            cwd=work_dir,
            check=True,
            capture_output=True
        )

        # 获取提交哈希
        result = subprocess.run(
            ["git", "rev-parse", default_branch],
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        commit_hash = result.stdout.strip()

        yield {
            "repo_path": repo_path,
            "commit_hash": commit_hash
        }


# =============================================================================
# Git 标签管理测试
# =============================================================================

@pytest.mark.asyncio
async def test_create_git_tag_success(temp_repo):
    """测试成功创建 Git 标签"""
    tag_hash = _create_git_tag(
        temp_repo["repo_path"],
        "v1.0.0",
        temp_repo["commit_hash"],
        message="Release v1.0.0"
    )

    assert tag_hash is not None
    assert len(tag_hash) == 40  # SHA-1 哈希长度


@pytest.mark.asyncio
async def test_create_git_tag_lightweight(temp_repo):
    """测试创建轻量标签"""
    tag_hash = _create_git_tag(
        temp_repo["repo_path"],
        "v1.0.0-light",
        temp_repo["commit_hash"]
    )

    assert tag_hash is not None


@pytest.mark.asyncio
async def test_list_git_tags(temp_repo):
    """测试列出 Git 标签"""
    # 创建两个标签
    _create_git_tag(
        temp_repo["repo_path"], "v1.0.0", temp_repo["commit_hash"], "First release"
    )
    _create_git_tag(
        temp_repo["repo_path"], "v1.1.0", temp_repo["commit_hash"], "Second release"
    )

    tags = list_git_tags(temp_repo["repo_path"])

    assert len(tags) == 2
    tag_names = [t["name"] for t in tags]
    assert "v1.0.0" in tag_names
    assert "v1.1.0" in tag_names


@pytest.mark.asyncio
async def test_list_git_tags_with_pattern(temp_repo):
    """测试使用模式匹配列出标签"""
    _create_git_tag(
        temp_repo["repo_path"], "v1.0.0", temp_repo["commit_hash"]
    )
    _create_git_tag(
        temp_repo["repo_path"], "v2.0.0", temp_repo["commit_hash"]
    )
    _create_git_tag(
        temp_repo["repo_path"], "release-1.0", temp_repo["commit_hash"]
    )

    tags = list_git_tags(temp_repo["repo_path"], pattern="v1.*")

    assert len(tags) == 1
    assert tags[0]["name"] == "v1.0.0"


@pytest.mark.asyncio
async def test_get_git_tag(temp_repo):
    """测试获取单个标签信息"""
    _create_git_tag(
        temp_repo["repo_path"], "v1.0.0", temp_repo["commit_hash"], "Test tag"
    )

    tag = get_git_tag(temp_repo["repo_path"], "v1.0.0")

    assert tag is not None
    assert tag["name"] == "v1.0.0"
    assert tag["commit_hash"] == temp_repo["commit_hash"]


@pytest.mark.asyncio
async def test_get_git_tag_not_found(temp_repo):
    """测试获取不存在的标签"""
    tag = get_git_tag(temp_repo["repo_path"], "nonexistent")
    assert tag is None


@pytest.mark.asyncio
async def test_delete_git_tag(temp_repo):
    """测试删除 Git 标签"""
    _create_git_tag(
        temp_repo["repo_path"], "v1.0.0", temp_repo["commit_hash"]
    )

    # 确认标签存在
    assert get_git_tag(temp_repo["repo_path"], "v1.0.0") is not None

    # 删除标签
    _delete_git_tag(temp_repo["repo_path"], "v1.0.0")

    # 确认标签已删除
    assert get_git_tag(temp_repo["repo_path"], "v1.0.0") is None


# =============================================================================
# Release 管理测试（使用依赖注入）
# =============================================================================

@pytest.mark.asyncio
async def test_create_release(async_db: AsyncSession, temp_repo, async_test_user):
    """测试创建 Release - 使用依赖注入传入仓库路径"""
    # 创建测试仓库记录
    repo = Repository(
        name="test-repo",
        description="Test repository",
        owner_id=async_test_user.id,
        is_public=True,
        path="testuser/test-repo"
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)

    # 创建 Release，直接传入仓库路径（依赖注入）
    release = await release_service.create_release(
        db=async_db,
        repository_id=repo.id,
        author_id=async_test_user.id,
        tag_name="v1.0.0",
        name="First Release",
        description="This is the first release",
        commit_hash=temp_repo["commit_hash"],
        is_draft=False,
        is_prerelease=False,
        repo_path=temp_repo["repo_path"]  # 依赖注入：传入临时仓库路径
    )

    assert release["tag_name"] == "v1.0.0"
    assert release["name"] == "First Release"
    assert release["release_number"] == 1


@pytest.mark.asyncio
async def test_create_release_duplicate_tag(async_db: AsyncSession, temp_repo, async_test_user):
    """测试创建重复标签的 Release"""
    repo = Repository(
        name="test-repo",
        description="Test repository",
        owner_id=async_test_user.id,
        is_public=True,
        path="testuser/test-repo"
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)

    # 创建第一个 Release
    await release_service.create_release(
        db=async_db,
        repository_id=repo.id,
        author_id=async_test_user.id,
        tag_name="v1.0.0",
        name="First Release",
        commit_hash=temp_repo["commit_hash"],
        repo_path=temp_repo["repo_path"]
    )

    # 尝试创建相同标签的 Release
    with pytest.raises(ValidationException) as exc_info:
        await release_service.create_release(
            db=async_db,
            repository_id=repo.id,
            author_id=async_test_user.id,
            tag_name="v1.0.0",
            name="Duplicate Release",
            commit_hash=temp_repo["commit_hash"],
            repo_path=temp_repo["repo_path"]
        )

    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_release(async_db: AsyncSession, temp_repo, async_test_user):
    """测试获取 Release"""
    repo = Repository(
        name="test-repo",
        description="Test repository",
        owner_id=async_test_user.id,
        is_public=True,
        path="testuser/test-repo"
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)

    # 创建 Release
    created = await release_service.create_release(
        db=async_db,
        repository_id=repo.id,
        author_id=async_test_user.id,
        tag_name="v1.0.0",
        name="First Release",
        commit_hash=temp_repo["commit_hash"],
        repo_path=temp_repo["repo_path"]
    )

    # 获取 Release
    release = await release_service.get_release(
        db=async_db,
        repository_id=repo.id,
        release_number=created["release_number"]
    )

    assert release["tag_name"] == "v1.0.0"
    assert release["name"] == "First Release"


@pytest.mark.asyncio
async def test_get_release_by_tag(async_db: AsyncSession, temp_repo, async_test_user):
    """测试通过标签获取 Release"""
    repo = Repository(
        name="test-repo",
        description="Test repository",
        owner_id=async_test_user.id,
        is_public=True,
        path="testuser/test-repo"
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)

    # 创建 Release
    await release_service.create_release(
        db=async_db,
        repository_id=repo.id,
        author_id=async_test_user.id,
        tag_name="v1.0.0",
        name="First Release",
        commit_hash=temp_repo["commit_hash"],
        repo_path=temp_repo["repo_path"]
    )

    # 通过标签获取
    release = await release_service.get_release_by_tag(
        db=async_db,
        repository_id=repo.id,
        tag_name="v1.0.0"
    )

    assert release["tag_name"] == "v1.0.0"
    assert release["name"] == "First Release"


@pytest.mark.asyncio
async def test_list_releases(async_db: AsyncSession, temp_repo, async_test_user):
    """测试获取 Release 列表"""
    repo = Repository(
        name="test-repo",
        description="Test repository",
        owner_id=async_test_user.id,
        is_public=True,
        path="testuser/test-repo"
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)

    # 创建两个 Release
    await release_service.create_release(
        db=async_db,
        repository_id=repo.id,
        author_id=async_test_user.id,
        tag_name="v1.0.0",
        name="First Release",
        commit_hash=temp_repo["commit_hash"],
        repo_path=temp_repo["repo_path"]
    )
    await release_service.create_release(
        db=async_db,
        repository_id=repo.id,
        author_id=async_test_user.id,
        tag_name="v2.0.0",
        name="Second Release",
        commit_hash=temp_repo["commit_hash"],
        repo_path=temp_repo["repo_path"]
    )

    # 获取列表
    result = await release_service.list_releases(
        db=async_db,
        repository_id=repo.id
    )

    assert result["total"] == 2
    assert len(result["items"]) == 2


@pytest.mark.asyncio
async def test_update_release(async_db: AsyncSession, temp_repo, async_test_user):
    """测试更新 Release"""
    repo = Repository(
        name="test-repo",
        description="Test repository",
        owner_id=async_test_user.id,
        is_public=True,
        path="testuser/test-repo"
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)

    # 创建 Release
    created = await release_service.create_release(
        db=async_db,
        repository_id=repo.id,
        author_id=async_test_user.id,
        tag_name="v1.0.0",
        name="First Release",
        commit_hash=temp_repo["commit_hash"],
        repo_path=temp_repo["repo_path"]
    )

    # 更新 Release
    updated = await release_service.update_release(
        db=async_db,
        repository_id=repo.id,
        release_number=created["release_number"],
        user_id=async_test_user.id,
        name="Updated Release",
        description="Updated description",
        is_draft=True,
        is_prerelease=True
    )

    assert updated["name"] == "Updated Release"
    assert updated["description"] == "Updated description"
    assert updated["is_draft"] is True
    assert updated["is_prerelease"] is True


@pytest.mark.asyncio
async def test_delete_release(async_db: AsyncSession, temp_repo, async_test_user):
    """测试删除 Release - 使用依赖注入传入仓库路径"""
    repo = Repository(
        name="test-repo",
        description="Test repository",
        owner_id=async_test_user.id,
        is_public=True,
        path="testuser/test-repo"
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)

    # 创建 Release
    created = await release_service.create_release(
        db=async_db,
        repository_id=repo.id,
        author_id=async_test_user.id,
        tag_name="v1.0.0",
        name="First Release",
        commit_hash=temp_repo["commit_hash"],
        repo_path=temp_repo["repo_path"]
    )

    # 确认 Git 标签已创建
    assert get_git_tag(temp_repo["repo_path"], "v1.0.0") is not None

    # 删除 Release，同时删除 Git 标签
    await release_service.delete_release(
        db=async_db,
        repository_id=repo.id,
        release_number=created["release_number"],
        user_id=async_test_user.id,
        delete_git_tag=True,
        repo_path=temp_repo["repo_path"]  # 依赖注入：传入临时仓库路径
    )

    # 确认 Release 已删除
    with pytest.raises(NotFoundException):
        await release_service.get_release(
            db=async_db,
            repository_id=repo.id,
            release_number=created["release_number"]
        )

    # 确认 Git 标签也已删除
    assert get_git_tag(temp_repo["repo_path"], "v1.0.0") is None


# =============================================================================
# Release Asset 管理测试
# =============================================================================

@pytest.mark.asyncio
async def test_add_release_asset(async_db: AsyncSession, temp_repo, async_test_user):
    """测试添加 Release 附件"""
    repo = Repository(
        name="test-repo",
        description="Test repository",
        owner_id=async_test_user.id,
        is_public=True,
        path="testuser/test-repo"
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)

    # 创建 Release
    release = await release_service.create_release(
        db=async_db,
        repository_id=repo.id,
        author_id=async_test_user.id,
        tag_name="v1.0.0",
        name="First Release",
        commit_hash=temp_repo["commit_hash"],
        repo_path=temp_repo["repo_path"]
    )

    # 添加附件
    asset = await release_service.add_release_asset(
        db=async_db,
        repository_id=repo.id,
        release_number=release["release_number"],
        user_id=async_test_user.id,
        name="app.zip",
        file_path="/path/to/app.zip",
        file_size=1024,
        content_type="application/zip"
    )

    assert asset["name"] == "app.zip"
    assert asset["file_size"] == 1024
    assert asset["content_type"] == "application/zip"


@pytest.mark.asyncio
async def test_delete_release_asset(async_db: AsyncSession, temp_repo, async_test_user):
    """测试删除 Release 附件"""
    repo = Repository(
        name="test-repo",
        description="Test repository",
        owner_id=async_test_user.id,
        is_public=True,
        path="testuser/test-repo"
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)

    # 创建 Release
    release = await release_service.create_release(
        db=async_db,
        repository_id=repo.id,
        author_id=async_test_user.id,
        tag_name="v1.0.0",
        name="First Release",
        commit_hash=temp_repo["commit_hash"],
        repo_path=temp_repo["repo_path"]
    )

    # 添加附件
    asset = await release_service.add_release_asset(
        db=async_db,
        repository_id=repo.id,
        release_number=release["release_number"],
        user_id=async_test_user.id,
        name="app.zip",
        file_path="/path/to/app.zip",
        file_size=1024,
        content_type="application/zip"
    )

    # 删除附件
    await release_service.delete_release_asset(
        db=async_db,
        repository_id=repo.id,
        release_number=release["release_number"],
        asset_id=asset["id"],
        user_id=async_test_user.id
    )

    # 确认附件已删除
    release_detail = await release_service.get_release(
        db=async_db,
        repository_id=repo.id,
        release_number=release["release_number"]
    )
    assert len(release_detail["assets"]) == 0
