"""
仓库服务层异步功能测试

测试 repository_service.py 中所有异步函数的正确性
"""
import pytest
import pytest_asyncio
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models.repository import Repository
from models.user import User
from models.branch import Branch
from models.repository_member import RepositoryMember
from models.base import BaseModel
from services import repository_service
from services import user_service
from exception import NotFoundException, ConflictException, ValidationException


# 使用内存中的 SQLite 进行测试
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_db():
    """
    创建异步数据库会话用于测试
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )
    
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    
    async with async_session() as session:
        yield session
    
    # 清理
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
    
    await engine.dispose()


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
