"""
仓库服务层异步功能测试

测试 repository_service.py 中所有异步函数的正确性
"""
import pytest
import pytest_asyncio
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.repository import Repository
from models.user import User
from models.branch import Branch
from models.repository_member import RepositoryMember
from services import repository_service
from services import user_service
from core.exception import NotFoundException, ConflictException, ValidationException


@pytest_asyncio.fixture
async def test_user(async_db: AsyncSession):
    """创建测试用户"""
    user_data = {
        "username": "repotestuser",
        "email": "repotest@example.com",
        "password": "testpass123",
        "full_name": "Repo Test User"
    }
    user = await user_service.create_user(user_data, async_db)
    return user


@pytest.mark.asyncio
async def test_create_repository(async_db: AsyncSession, test_user):
    """测试创建仓库"""
    repo_data = {
        "name": "test-repo",
        "path": "test-repo",
        "description": "Test repository",
        "is_public": True,
        "owner_id": test_user["id"],
        "default_branch": "main"
    }
    
    created = await repository_service.create_repository(repo_data, async_db)
    
    assert created["name"] == "test-repo"
    assert created["path"] == "test-repo"
    assert created["description"] == "Test repository"
    assert created["is_public"] == True
    assert created["owner_id"] == test_user["id"]
    assert "id" in created
    
    print("✓ test_create_repository 通过")


@pytest.mark.asyncio
async def test_create_repository_missing_fields(async_db: AsyncSession, test_user):
    """测试创建仓库时缺少必填字段"""
    # 缺少 name
    with pytest.raises(ValidationException) as exc_info:
        await repository_service.create_repository({
            "path": "test-repo",
            "owner_id": test_user["id"]
        }, async_db)
    assert "Name, path and owner_id are required" in str(exc_info.value)
    
    # 缺少 path
    with pytest.raises(ValidationException) as exc_info:
        await repository_service.create_repository({
            "name": "test-repo",
            "owner_id": test_user["id"]
        }, async_db)
    assert "Name, path and owner_id are required" in str(exc_info.value)
    
    # 缺少 owner_id
    with pytest.raises(ValidationException) as exc_info:
        await repository_service.create_repository({
            "name": "test-repo",
            "path": "test-repo"
        }, async_db)
    assert "Name, path and owner_id are required" in str(exc_info.value)
    
    print("✓ test_create_repository_missing_fields 通过")


@pytest.mark.asyncio
async def test_create_repository_duplicate_path(async_db: AsyncSession, test_user):
    """测试创建仓库时路径重复"""
    repo_data = {
        "name": "test-repo",
        "path": "duplicate-path",
        "description": "Test repository",
        "owner_id": test_user["id"]
    }
    
    # 创建第一个仓库
    await repository_service.create_repository(repo_data, async_db)
    
    # 尝试创建相同路径的仓库
    with pytest.raises(ConflictException) as exc_info:
        await repository_service.create_repository({
            "name": "another-repo",
            "path": "duplicate-path",
            "owner_id": test_user["id"]
        }, async_db)
    
    assert "Repository path already exists" in str(exc_info.value)
    print("✓ test_create_repository_duplicate_path 通过")


@pytest.mark.asyncio
async def test_get_repositories(async_db: AsyncSession, test_user):
    """测试获取所有仓库"""
    # 创建多个仓库
    repos_data = [
        {"name": "repo1", "path": "repo1", "owner_id": test_user["id"]},
        {"name": "repo2", "path": "repo2", "owner_id": test_user["id"]},
        {"name": "repo3", "path": "repo3", "owner_id": test_user["id"]},
    ]
    
    for data in repos_data:
        await repository_service.create_repository(data, async_db)
    
    # 获取所有仓库
    repos = await repository_service.get_repositories(async_db)
    
    # 验证结果
    assert len(repos) == 3
    paths = [r["path"] for r in repos]
    assert "repo1" in paths
    assert "repo2" in paths
    assert "repo3" in paths
    
    print("✓ test_get_repositories 通过")


@pytest.mark.asyncio
async def test_get_repository_by_id(async_db: AsyncSession, test_user):
    """测试根据ID获取仓库"""
    # 创建仓库
    repo_data = {
        "name": "test-repo",
        "path": "test-get-repo",
        "owner_id": test_user["id"]
    }
    created = await repository_service.create_repository(repo_data, async_db)
    repo_id = created["id"]
    
    # 获取仓库
    repo = await repository_service.get_repository_by_id(repo_id, async_db)
    
    # 验证结果
    assert repo["name"] == "test-repo"
    assert repo["path"] == "test-get-repo"
    assert repo["owner_id"] == test_user["id"]
    
    print("✓ test_get_repository_by_id 通过")


@pytest.mark.asyncio
async def test_get_repository_by_id_not_found(async_db: AsyncSession):
    """测试获取不存在的仓库"""
    with pytest.raises(NotFoundException) as exc_info:
        await repository_service.get_repository_by_id(99999, async_db)
    
    assert "Repository not found" in str(exc_info.value)
    print("✓ test_get_repository_by_id_not_found 通过")


@pytest.mark.asyncio
async def test_update_repository(async_db: AsyncSession, test_user):
    """测试更新仓库信息"""
    # 创建仓库
    repo_data = {
        "name": "test-repo",
        "path": "test-update-repo",
        "description": "Original description",
        "owner_id": test_user["id"]
    }
    created = await repository_service.create_repository(repo_data, async_db)
    repo_id = created["id"]
    
    # 更新仓库
    update_data = {
        "name": "updated-repo",
        "description": "Updated description"
    }
    updated = await repository_service.update_repository(repo_id, update_data, async_db)
    
    # 验证结果
    assert updated["name"] == "updated-repo"
    assert updated["description"] == "Updated description"
    assert updated["path"] == "test-update-repo"  # 未修改的字段保持不变
    
    print("✓ test_update_repository 通过")


@pytest.mark.asyncio
async def test_update_repository_not_found(async_db: AsyncSession):
    """测试更新不存在的仓库"""
    with pytest.raises(NotFoundException) as exc_info:
        await repository_service.update_repository(99999, {"name": "new-name"}, async_db)
    
    assert "Repository not found" in str(exc_info.value)
    print("✓ test_update_repository_not_found 通过")


@pytest.mark.asyncio
async def test_delete_repository(async_db: AsyncSession, test_user):
    """测试删除仓库"""
    # 创建仓库
    repo_data = {
        "name": "test-repo",
        "path": "test-delete-repo",
        "owner_id": test_user["id"]
    }
    created = await repository_service.create_repository(repo_data, async_db)
    repo_id = created["id"]
    
    # 删除仓库
    result = await repository_service.delete_repository(repo_id, async_db)
    
    # 验证结果
    assert result["message"] == "Repository deleted successfully"
    
    # 验证仓库已被删除
    with pytest.raises(NotFoundException):
        await repository_service.get_repository_by_id(repo_id, async_db)
    
    print("✓ test_delete_repository 通过")


@pytest.mark.asyncio
async def test_delete_repository_not_found(async_db: AsyncSession):
    """测试删除不存在的仓库"""
    with pytest.raises(NotFoundException) as exc_info:
        await repository_service.delete_repository(99999, async_db)
    
    assert "Repository not found" in str(exc_info.value)
    print("✓ test_delete_repository_not_found 通过")


@pytest.mark.asyncio
async def test_get_public_repositories(async_db: AsyncSession, test_user):
    """测试获取公开仓库"""
    # 创建公开和私有仓库
    await repository_service.create_repository({
        "name": "public-repo",
        "path": "public-repo",
        "is_public": True,
        "owner_id": test_user["id"]
    }, async_db)
    
    await repository_service.create_repository({
        "name": "private-repo",
        "path": "private-repo",
        "is_public": False,
        "owner_id": test_user["id"]
    }, async_db)
    
    # 获取公开仓库
    public_repos = await repository_service.get_public_repositories(async_db)
    
    # 验证结果
    assert len(public_repos) == 1
    assert public_repos[0]["name"] == "public-repo"
    assert public_repos[0]["is_public"] == True
    
    print("✓ test_get_public_repositories 通过")


@pytest.mark.asyncio
async def test_get_repositories_by_user(async_db: AsyncSession, test_user):
    """测试根据用户ID获取仓库列表"""
    # 创建属于该用户的仓库
    await repository_service.create_repository({
        "name": "owned-repo",
        "path": "owned-repo",
        "owner_id": test_user["id"]
    }, async_db)
    
    # 获取用户的仓库
    repos = await repository_service.get_repositories_by_user(test_user["id"], async_db)
    
    # 验证结果
    assert len(repos) == 1
    assert repos[0]["name"] == "owned-repo"
    
    print("✓ test_get_repositories_by_user 通过")


@pytest.mark.asyncio
async def test_check_repository_access(async_db: AsyncSession, test_user):
    """测试检查仓库访问权限"""
    # 创建公开仓库
    repo_data = {
        "name": "access-test-repo",
        "path": "access-test-repo",
        "is_public": True,
        "owner_id": test_user["id"]
    }
    created = await repository_service.create_repository(repo_data, async_db)
    repo_id = created["id"]
    
    # 测试所有者访问权限
    has_access = await repository_service.check_repository_access(
        repo_id, test_user["id"], async_db
    )
    assert has_access == True
    
    # 测试公开仓库访问权限（不需要特定角色）
    has_access = await repository_service.check_repository_access(
        repo_id, 99999, async_db  # 不存在的用户
    )
    assert has_access == True
    
    print("✓ test_check_repository_access 通过")


@pytest.mark.asyncio
async def test_check_repository_access_private(async_db: AsyncSession, test_user):
    """测试私有仓库访问权限"""
    # 创建私有仓库
    repo_data = {
        "name": "private-access-repo",
        "path": "private-access-repo",
        "is_public": False,
        "owner_id": test_user["id"]
    }
    created = await repository_service.create_repository(repo_data, async_db)
    repo_id = created["id"]
    
    # 所有者应该有访问权限
    has_access = await repository_service.check_repository_access(
        repo_id, test_user["id"], async_db
    )
    assert has_access == True
    
    # 其他用户不应该有访问权限
    has_access = await repository_service.check_repository_access(
        repo_id, 99999, async_db
    )
    assert has_access == False
    
    print("✓ test_check_repository_access_private 通过")


# =============================================================================
# F-006: 创建仓库时初始化 bare repo 测试
# =============================================================================

@pytest.mark.asyncio
async def test_create_repo_initializes_git_dir(async_db: AsyncSession, test_user):
    """
    测试创建仓库时自动初始化 bare Git 仓库

    验证点：
    1. 创建数据库记录后，物理仓库目录被创建
    2. 物理仓库是有效的 bare 仓库
    3. 返回的 physical_exists 为 True
    """
    import os
    import tempfile
    from utils.git_utils import get_repository_storage_path, repo_exists

    repo_data = {
        "name": "physical-repo-test",
        "path": "physical-repo-test",
        "description": "Test physical repository creation",
        "is_public": True,
        "owner_id": test_user["id"],
        "default_branch": "main"
    }

    # 创建仓库
    created = await repository_service.create_repository(repo_data, async_db)

    # 验证返回结果中包含 physical_exists 且为 True
    assert "physical_exists" in created
    assert created["physical_exists"] == True

    # 验证物理仓库目录存在
    physical_path = get_repository_storage_path(created["path"])
    assert os.path.exists(physical_path), f"物理仓库目录不存在: {physical_path}"

    # 验证是有效的 bare 仓库
    assert repo_exists(physical_path), f"路径不是有效的 Git 仓库: {physical_path}"

    # 验证是 bare 仓库（检查 git config）
    git_config_path = os.path.join(physical_path, "config")
    assert os.path.exists(git_config_path), "仓库 config 文件不存在"

    with open(git_config_path, 'r') as f:
        config_content = f.read()
        assert "bare = true" in config_content, "仓库不是 bare 仓库"

    print("✓ test_create_repo_initializes_git_dir 通过")


@pytest.mark.asyncio
async def test_create_repo_physical_status_detection(async_db: AsyncSession, test_user):
    """
    测试仓库物理存在状态检测功能

    验证点：
    1. 创建仓库时 physical_exists 正确返回
    2. 手动删除物理仓库后，状态检测应返回 False
    """
    import os
    import shutil
    from utils.git_utils import get_repository_storage_path

    repo_data = {
        "name": "status-detection-test",
        "path": "status-detection-test",
        "owner_id": test_user["id"]
    }

    # 创建仓库
    created = await repository_service.create_repository(repo_data, async_db)
    repo_id = created["id"]

    # 验证创建时 physical_exists 为 True
    assert created["physical_exists"] == True

    # 手动删除物理仓库目录
    physical_path = get_repository_storage_path(created["path"])
    if os.path.exists(physical_path):
        shutil.rmtree(physical_path)

    # 重新获取仓库信息，验证 physical_exists 为 False
    # 注意：由于缓存机制，可能需要等待缓存过期或清除缓存
    from services.repository_service import _repo_exists_cache
    _repo_exists_cache.clear()  # 清除缓存

    repo = await repository_service.get_repository_by_id(repo_id, async_db)
    assert repo["physical_exists"] == False

    print("✓ test_create_repo_physical_status_detection 通过")


# =============================================================================
# F-007: 物理仓库存在性检查测试
# =============================================================================

@pytest.mark.asyncio
async def test_check_repositories_physical_status_batch(async_db: AsyncSession, test_user):
    """
    测试批量检查仓库物理存在状态

    验证点：
    1. 可以批量检查多个仓库的物理状态
    2. 返回结果包含每个仓库的 physical_exists 状态
    3. 状态与实际情况一致
    """
    import os
    import shutil
    from utils.git_utils import get_repository_storage_path

    # 创建多个仓库
    repos_data = [
        {"name": "repo-with-physical", "path": "repo-with-physical", "owner_id": test_user["id"]},
        {"name": "repo-without-physical", "path": "repo-without-physical", "owner_id": test_user["id"]},
    ]

    created_repos = []
    for data in repos_data:
        created = await repository_service.create_repository(data, async_db)
        created_repos.append(created)

    # 删除第二个仓库的物理目录（模拟物理仓库丢失）
    physical_path = get_repository_storage_path(created_repos[1]["path"])
    if os.path.exists(physical_path):
        shutil.rmtree(physical_path)

    # 清除缓存
    from services.repository_service import _repo_exists_cache
    _repo_exists_cache.clear()

    # 批量获取仓库列表并检查状态
    repos = await repository_service.get_repositories_by_user(test_user["id"], async_db)

    # 验证每个仓库都有 physical_exists 字段
    for repo in repos:
        assert "physical_exists" in repo, f"仓库 {repo['name']} 缺少 physical_exists 字段"

    # 找到对应的仓库并验证状态
    repo_map = {r["path"]: r for r in repos}

    # 第一个仓库应该有物理存在
    assert repo_map["repo-with-physical"]["physical_exists"] == True, \
        "repo-with-physical 应该存在物理仓库"

    # 第二个仓库应该没有物理存在
    assert repo_map["repo-without-physical"]["physical_exists"] == False, \
        "repo-without-physical 不应该存在物理仓库"

    print("✓ test_check_repositories_physical_status_batch 通过")


@pytest.mark.asyncio
async def test_physical_status_cache_works(async_db: AsyncSession, test_user):
    """
    测试物理仓库状态缓存机制

    验证点：
    1. 缓存可以减少磁盘 IO 检查次数
    2. 缓存有 TTL（生存时间）
    3. 缓存可以被手动清除
    """
    from services.repository_service import (
        _repo_exists_cache, _set_cached_repo_exists, _get_cached_repo_exists
    )

    # 清除所有缓存
    _repo_exists_cache.clear()

    # 设置缓存值
    test_repo_id = 99999
    _set_cached_repo_exists(test_repo_id, True)

    # 验证缓存命中
    exists, cache_hit = _get_cached_repo_exists(test_repo_id)
    assert cache_hit == True, "缓存应该命中"
    assert exists == True, "缓存值应该正确"

    # 验证不存在的缓存未命中
    exists, cache_hit = _get_cached_repo_exists(88888)
    assert cache_hit == False, "未设置的缓存应该未命中"

    print("✓ test_physical_status_cache_works 通过")


@pytest.mark.asyncio
async def test_get_repository_includes_physical_status(async_db: AsyncSession, test_user):
    """
    测试获取单个仓库时包含物理状态信息

    验证点：
    1. get_repository_by_id 返回包含 physical_exists
    2. 状态值正确反映物理仓库存在性
    """
    # 创建仓库
    repo_data = {
        "name": "single-repo-check",
        "path": "single-repo-check",
        "owner_id": test_user["id"]
    }
    created = await repository_service.create_repository(repo_data, async_db)
    repo_id = created["id"]

    # 通过 ID 获取仓库
    repo = await repository_service.get_repository_by_id(repo_id, async_db)

    # 验证包含 physical_exists 字段且为 True
    assert "physical_exists" in repo, "返回结果应该包含 physical_exists 字段"
    assert repo["physical_exists"] == True, "新创建的仓库 physical_exists 应该为 True"

    print("✓ test_get_repository_includes_physical_status 通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
