"""
分支服务层异步功能测试

测试 branch_service.py 中所有异步函数的正确性
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models.branch import Branch
from models.repository import Repository
from models.user import User
from models.base import BaseModel
from services import branch_service
from services import repository_service
from services import user_service
from core.exception import NotFoundException, ConflictException, ValidationException, AuthorizationException


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
        "username": "branchtestuser",
        "email": "branchtest@example.com",
        "password": "testpass123",
        "full_name": "Branch Test User"
    }
    user = await user_service.create_user(user_data, async_db)
    return user


@pytest_asyncio.fixture
async def test_repo(async_db: AsyncSession, test_user):
    """创建测试仓库"""
    repo_data = {
        "name": "test-repo",
        "path": "test-branch-repo",
        "description": "Test repository for branches",
        "is_public": True,
        "owner_id": test_user["id"],
        "default_branch": "main"
    }
    repo = await repository_service.create_repository(repo_data, async_db)
    return repo


@pytest.mark.asyncio
async def test_create_branch(async_db: AsyncSession, test_repo):
    """测试创建分支"""
    branch_data = {
        "name": "feature-branch",
        "is_protected": False,
        "require_code_review": True,
        "require_status_checks": False,
        "is_default": False
    }
    
    created = await branch_service.create_branch(test_repo["id"], branch_data, async_db)
    
    assert created.name == "feature-branch"
    assert created.repository_id == test_repo["id"]
    assert created.is_protected == False
    assert created.require_code_review == True
    assert created.is_default == False
    
    print("✓ test_create_branch 通过")


@pytest.mark.asyncio
async def test_create_branch_missing_name(async_db: AsyncSession, test_repo):
    """测试创建分支时缺少名称"""
    with pytest.raises(ValidationException) as exc_info:
        await branch_service.create_branch(test_repo["id"], {}, async_db)
    
    assert "Branch name is required" in str(exc_info.value)
    print("✓ test_create_branch_missing_name 通过")


@pytest.mark.asyncio
async def test_create_branch_duplicate_name(async_db: AsyncSession, test_repo):
    """测试创建同名分支"""
    # 创建第一个分支
    await branch_service.create_branch(test_repo["id"], {"name": "duplicate-branch"}, async_db)
    
    # 尝试创建同名分支
    with pytest.raises(ConflictException) as exc_info:
        await branch_service.create_branch(test_repo["id"], {"name": "duplicate-branch"}, async_db)
    
    assert "Branch 'duplicate-branch' already exists" in str(exc_info.value)
    print("✓ test_create_branch_duplicate_name 通过")


@pytest.mark.asyncio
async def test_get_branches(async_db: AsyncSession, test_repo):
    """测试获取所有分支"""
    # 创建多个分支
    await branch_service.create_branch(test_repo["id"], {"name": "branch1"}, async_db)
    await branch_service.create_branch(test_repo["id"], {"name": "branch2"}, async_db)
    await branch_service.create_branch(test_repo["id"], {"name": "branch3"}, async_db)
    
    # 获取所有分支
    branches = await branch_service.get_branches(test_repo["id"], async_db)
    
    # 验证结果（包括默认创建的 main 分支，应该有4个）
    assert len(branches) >= 3
    branch_names = [b.name for b in branches]
    assert "branch1" in branch_names
    assert "branch2" in branch_names
    assert "branch3" in branch_names
    
    print("✓ test_get_branches 通过")


@pytest.mark.asyncio
async def test_get_branch(async_db: AsyncSession, test_repo):
    """测试获取特定分支"""
    # 创建分支
    await branch_service.create_branch(test_repo["id"], {"name": "test-get-branch"}, async_db)
    
    # 获取分支
    branch = await branch_service.get_branch(test_repo["id"], "test-get-branch", async_db)
    
    assert branch.name == "test-get-branch"
    assert branch.repository_id == test_repo["id"]
    
    print("✓ test_get_branch 通过")


@pytest.mark.asyncio
async def test_get_branch_not_found(async_db: AsyncSession, test_repo):
    """测试获取不存在的分支"""
    with pytest.raises(NotFoundException) as exc_info:
        await branch_service.get_branch(test_repo["id"], "nonexistent-branch", async_db)
    
    assert "Branch 'nonexistent-branch' not found" in str(exc_info.value)
    print("✓ test_get_branch_not_found 通过")


@pytest.mark.asyncio
async def test_get_branch_by_id(async_db: AsyncSession, test_repo):
    """测试根据ID获取分支"""
    # 创建分支
    created = await branch_service.create_branch(test_repo["id"], {"name": "test-by-id"}, async_db)
    branch_id = created.id
    
    # 根据ID获取
    branch = await branch_service.get_branch_by_id(branch_id, async_db)
    
    assert branch.name == "test-by-id"
    assert branch.id == branch_id
    
    print("✓ test_get_branch_by_id 通过")


@pytest.mark.asyncio
async def test_get_branch_by_id_not_found(async_db: AsyncSession):
    """测试根据ID获取不存在的分支"""
    with pytest.raises(NotFoundException) as exc_info:
        await branch_service.get_branch_by_id(99999, async_db)
    
    assert "Branch not found" in str(exc_info.value)
    print("✓ test_get_branch_by_id_not_found 通过")


@pytest.mark.asyncio
async def test_update_branch(async_db: AsyncSession, test_repo):
    """测试更新分支信息"""
    # 创建分支
    await branch_service.create_branch(test_repo["id"], {"name": "update-test"}, async_db)
    
    # 更新分支
    updated = await branch_service.update_branch(
        test_repo["id"], "update-test",
        {"is_protected": True, "require_code_review": True},
        async_db
    )
    
    assert updated.is_protected == True
    assert updated.require_code_review == True
    
    print("✓ test_update_branch 通过")


@pytest.mark.asyncio
async def test_delete_branch(async_db: AsyncSession, test_repo):
    """测试删除分支"""
    # 创建分支
    await branch_service.create_branch(test_repo["id"], {"name": "delete-test"}, async_db)
    
    # 删除分支
    result = await branch_service.delete_branch(test_repo["id"], "delete-test", async_db)
    
    assert result["message"] == "Branch 'delete-test' deleted successfully"
    
    # 验证分支已被删除
    with pytest.raises(NotFoundException):
        await branch_service.get_branch(test_repo["id"], "delete-test", async_db)
    
    print("✓ test_delete_branch 通过")


@pytest.mark.asyncio
async def test_delete_default_branch(async_db: AsyncSession, test_repo):
    """测试删除默认分支（应该失败）"""
    # 获取默认分支（main）
    default_branch = await branch_service.get_default_branch(test_repo["id"], async_db)
    
    # 尝试删除默认分支
    with pytest.raises(AuthorizationException) as exc_info:
        await branch_service.delete_branch(test_repo["id"], default_branch.name, async_db)
    
    assert "Cannot delete default branch" in str(exc_info.value)
    print("✓ test_delete_default_branch 通过")


@pytest.mark.asyncio
async def test_protect_branch(async_db: AsyncSession, test_repo):
    """测试保护分支"""
    # 创建分支
    await branch_service.create_branch(test_repo["id"], {"name": "protect-test"}, async_db)
    
    # 保护分支
    protected = await branch_service.protect_branch(
        test_repo["id"], "protect-test",
        {"require_code_review": True, "require_status_checks": True},
        async_db
    )
    
    assert protected.is_protected == True
    assert protected.require_code_review == True
    assert protected.require_status_checks == True
    
    print("✓ test_protect_branch 通过")


@pytest.mark.asyncio
async def test_unprotect_branch(async_db: AsyncSession, test_repo):
    """测试取消分支保护"""
    # 创建并保护分支
    await branch_service.create_branch(test_repo["id"], {"name": "unprotect-test", "is_protected": True}, async_db)
    
    # 取消保护
    unprotected = await branch_service.unprotect_branch(test_repo["id"], "unprotect-test", async_db)
    
    assert unprotected.is_protected == False
    assert unprotected.require_code_review == False
    assert unprotected.require_status_checks == False
    
    print("✓ test_unprotect_branch 通过")


@pytest.mark.asyncio
async def test_get_default_branch(async_db: AsyncSession, test_repo):
    """测试获取默认分支"""
    # 获取默认分支
    default_branch = await branch_service.get_default_branch(test_repo["id"], async_db)
    
    assert default_branch.is_default == True
    assert default_branch.repository_id == test_repo["id"]
    
    print("✓ test_get_default_branch 通过")


@pytest.mark.asyncio
async def test_check_branch_protection(async_db: AsyncSession, test_repo):
    """测试检查分支保护状态"""
    # 创建保护分支
    await branch_service.create_branch(
        test_repo["id"],
        {"name": "check-protect", "is_protected": True, "require_code_review": True},
        async_db
    )
    
    # 检查保护状态
    protection = await branch_service.check_branch_protection(test_repo["id"], "check-protect", async_db)
    
    assert protection["is_protected"] == True
    assert protection["require_code_review"] == True
    
    print("✓ test_check_branch_protection 通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
