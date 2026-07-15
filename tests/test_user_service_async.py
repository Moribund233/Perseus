import uuid
"""
用户服务层异步功能测试

测试 user_service.py 中所有异步函数的正确性
"""
import pytest
import pytest_asyncio
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from models.user import User
from services import user_service
from core.exception import NotFoundException, ConflictException, AuthenticationException


@pytest.mark.asyncio
async def test_user_to_dict(async_db: AsyncSession):
    """测试用户对象转换为字典"""
    # 创建测试用户
    user = User(
        username="testuser",
        email="test@example.com",
        password="hashed_password",
        full_name="Test User",
        is_active=True,
        is_admin=False
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    
    # 转换为字典
    user_dict = user_service.user_to_dict(user)
    
    # 验证字典内容
    assert user_dict["id"] == user.id
    assert user_dict["username"] == "testuser"
    assert user_dict["email"] == "test@example.com"
    assert user_dict["full_name"] == "Test User"
    assert user_dict["is_active"] == True
    assert user_dict["is_admin"] == False
    assert "password" not in user_dict  # 确保密码不包含在字典中
    
    print("✓ test_user_to_dict 通过")


@pytest.mark.asyncio
async def test_verify_password():
    """测试密码验证功能"""
    # 生成密码哈希
    password = "testpassword123"
    hashed = user_service.get_password_hash(password)
    
    # 验证正确密码
    assert user_service.verify_password(password, hashed) == True
    
    # 验证错误密码
    assert user_service.verify_password("wrongpassword", hashed) == False
    
    print("✓ test_verify_password 通过")


@pytest.mark.asyncio
async def test_get_users(async_db: AsyncSession):
    """测试获取所有用户"""
    # 创建多个测试用户
    users_data = [
        {"username": "user1", "email": "user1@example.com", "password": "pass1"},
        {"username": "user2", "email": "user2@example.com", "password": "pass2"},
        {"username": "user3", "email": "user3@example.com", "password": "pass3"},
    ]
    
    for data in users_data:
        await user_service.create_user(data, async_db)
    
    # 获取所有用户
    users = await user_service.get_users(async_db)
    
    # 验证结果
    assert len(users) == 3
    usernames = [u["username"] for u in users]
    assert "user1" in usernames
    assert "user2" in usernames
    assert "user3" in usernames
    
    print("✓ test_get_users 通过")


@pytest.mark.asyncio
async def test_get_user_by_id(async_db: AsyncSession):
    """测试根据ID获取用户"""
    # 创建测试用户
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User"
    }
    created = await user_service.create_user(user_data, async_db)
    user_id = created["id"]
    
    # 获取用户
    user = await user_service.get_user_by_id(user_id, async_db)
    
    # 验证结果
    assert user["username"] == "testuser"
    assert user["email"] == "test@example.com"
    assert user["full_name"] == "Test User"
    
    print("✓ test_get_user_by_id 通过")


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(async_db: AsyncSession):
    """测试获取不存在的用户"""
    with pytest.raises(NotFoundException) as exc_info:
        await user_service.get_user_by_id(uuid.UUID("00000000-0000-0000-0000-000000000000"), async_db)
    
    assert "User not found" in str(exc_info.value)
    print("✓ test_get_user_by_id_not_found 通过")


@pytest.mark.asyncio
async def test_create_user(async_db: AsyncSession):
    """测试创建用户"""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "newpass123",
        "full_name": "New User",
        "is_active": True,
        "is_admin": False
    }
    
    # 创建用户
    created = await user_service.create_user(user_data, async_db)
    
    # 验证结果
    assert created["username"] == "newuser"
    assert created["email"] == "newuser@example.com"
    assert created["full_name"] == "New User"
    assert created["is_active"] == True
    assert created["is_admin"] == False
    assert "id" in created
    
    print("✓ test_create_user 通过")


@pytest.mark.asyncio
async def test_create_user_duplicate_username(async_db: AsyncSession):
    """测试创建用户时用户名重复"""
    # 创建第一个用户
    user_data1 = {
        "username": "duplicateuser",
        "email": "user1@example.com",
        "password": "pass123"
    }
    await user_service.create_user(user_data1, async_db)
    
    # 尝试创建同名用户
    user_data2 = {
        "username": "duplicateuser",
        "email": "user2@example.com",
        "password": "pass456"
    }
    
    with pytest.raises(ConflictException) as exc_info:
        await user_service.create_user(user_data2, async_db)
    
    assert "Username already exists" in str(exc_info.value)
    print("✓ test_create_user_duplicate_username 通过")


@pytest.mark.asyncio
async def test_create_user_duplicate_email(async_db: AsyncSession):
    """测试创建用户时邮箱重复"""
    # 创建第一个用户
    user_data1 = {
        "username": "user1",
        "email": "duplicate@example.com",
        "password": "pass123"
    }
    await user_service.create_user(user_data1, async_db)
    
    # 尝试创建同邮箱用户
    user_data2 = {
        "username": "user2",
        "email": "duplicate@example.com",
        "password": "pass456"
    }
    
    with pytest.raises(ConflictException) as exc_info:
        await user_service.create_user(user_data2, async_db)
    
    assert "Email already exists" in str(exc_info.value)
    print("✓ test_create_user_duplicate_email 通过")


@pytest.mark.asyncio
async def test_update_user(async_db: AsyncSession):
    """测试更新用户信息"""
    # 创建测试用户
    user_data = {
        "username": "updatetest",
        "email": "update@example.com",
        "password": "pass123",
        "full_name": "Original Name"
    }
    created = await user_service.create_user(user_data, async_db)
    user_id = created["id"]
    
    # 更新用户信息
    update_data = {
        "full_name": "Updated Name",
        "email": "updated@example.com"
    }
    updated = await user_service.update_user(user_id, update_data, async_db)
    
    # 验证结果
    assert updated["full_name"] == "Updated Name"
    assert updated["email"] == "updated@example.com"
    assert updated["username"] == "updatetest"  # 未修改的字段保持不变
    
    print("✓ test_update_user 通过")


@pytest.mark.asyncio
async def test_update_user_not_found(async_db: AsyncSession):
    """测试更新不存在的用户"""
    with pytest.raises(NotFoundException) as exc_info:
        await user_service.update_user(uuid.UUID("00000000-0000-0000-0000-000000000000"), {"full_name": "New Name"}, async_db)
    
    assert "User not found" in str(exc_info.value)
    print("✓ test_update_user_not_found 通过")


@pytest.mark.asyncio
async def test_delete_user(async_db: AsyncSession):
    """测试删除用户"""
    # 创建测试用户
    user_data = {
        "username": "deletetest",
        "email": "delete@example.com",
        "password": "pass123"
    }
    created = await user_service.create_user(user_data, async_db)
    user_id = created["id"]
    
    # 删除用户
    result = await user_service.delete_user(user_id, async_db)
    
    # 验证结果
    assert result["message"] == "User deleted successfully"
    
    # 验证用户已被删除
    with pytest.raises(NotFoundException):
        await user_service.get_user_by_id(user_id, async_db)
    
    print("✓ test_delete_user 通过")


@pytest.mark.asyncio
async def test_delete_user_not_found(async_db: AsyncSession):
    """测试删除不存在的用户"""
    with pytest.raises(NotFoundException) as exc_info:
        await user_service.delete_user(uuid.UUID("00000000-0000-0000-0000-000000000000"), async_db)
    
    assert "User not found" in str(exc_info.value)
    print("✓ test_delete_user_not_found 通过")


@pytest.mark.asyncio
async def test_login_user(async_db: AsyncSession):
    """测试用户登录"""
    # 创建测试用户
    user_data = {
        "username": "logintest",
        "email": "login@example.com",
        "password": "loginpass123",
        "full_name": "Login Test User"
    }
    created = await user_service.create_user(user_data, async_db)
    
    # 登录
    credentials = {
        "username": "logintest",
        "password": "loginpass123"
    }
    result = await user_service.login_user(credentials, async_db)
    
    # 验证结果
    assert result["username"] == "logintest"
    assert result["email"] == "login@example.com"
    assert result["full_name"] == "Login Test User"
    assert "token" in result
    
    print("✓ test_login_user 通过")


@pytest.mark.asyncio
async def test_login_user_invalid_credentials(async_db: AsyncSession):
    """测试使用无效凭据登录"""
    # 创建测试用户
    user_data = {
        "username": "invalidtest",
        "email": "invalid@example.com",
        "password": "correctpass"
    }
    await user_service.create_user(user_data, async_db)
    
    # 使用错误密码登录
    credentials = {
        "username": "invalidtest",
        "password": "wrongpass"
    }
    
    with pytest.raises(AuthenticationException) as exc_info:
        await user_service.login_user(credentials, async_db)
    
    assert "Invalid username or password" in str(exc_info.value)
    print("✓ test_login_user_invalid_credentials 通过")


@pytest.mark.asyncio
async def test_login_user_missing_credentials(async_db: AsyncSession):
    """测试使用不完整的凭据登录"""
    # 缺少密码
    with pytest.raises(Exception) as exc_info:
        await user_service.login_user({"username": "test"}, async_db)
    
    assert "Username and password are required" in str(exc_info.value)
    print("✓ test_login_user_missing_credentials 通过")


@pytest.mark.asyncio
async def test_authenticate_user(async_db: AsyncSession):
    """测试用户认证"""
    # 创建测试用户
    user_data = {
        "username": "authtest",
        "email": "auth@example.com",
        "password": "authpass123"
    }
    await user_service.create_user(user_data, async_db)
    
    # 认证成功
    user = await user_service.authenticate_user("authtest", "authpass123", async_db)
    assert user is not None
    assert user.username == "authtest"
    
    # 认证失败 - 错误密码
    user = await user_service.authenticate_user("authtest", "wrongpass", async_db)
    assert user is None
    
    # 认证失败 - 不存在的用户
    user = await user_service.authenticate_user("nonexistent", "pass", async_db)
    assert user is None
    
    print("✓ test_authenticate_user 通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
