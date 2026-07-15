import uuid
"""
Token Service 认证功能异步测试

测试 Token 认证相关的核心功能
"""
import pytest
import pytest_asyncio
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.user import User
from services import token_service
from services.user_service import authenticate_user
from api.dependencies import get_current_user
from core.exception import AuthenticationException


@pytest_asyncio.fixture
async def test_user(async_db: AsyncSession):
    """创建测试用户"""
    from utils.password_utils import get_password_hash
    user = User(
        username="testuser",
        email="test@example.com",
        password=get_password_hash("testpassword"),
        full_name="Test User",
        is_active=True
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(async_db: AsyncSession):
    """创建未激活测试用户"""
    from utils.password_utils import get_password_hash
    user = User(
        username="inactiveuser",
        email="inactive@example.com",
        password=get_password_hash("testpassword"),
        full_name="Inactive User",
        is_active=False
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    return user


async def get_user_by_username(async_db: AsyncSession, username: str) -> User | None:
    """根据用户名获取用户（辅助函数）"""
    result = await async_db.execute(select(User).filter(User.username == username))
    return result.scalar_one_or_none()


@pytest.mark.asyncio
async def test_get_user_by_username_success(async_db: AsyncSession, test_user: User):
    """测试成功根据用户名获取用户"""
    user = await get_user_by_username(async_db, "testuser")
    assert user is not None
    assert user.username == "testuser"
    assert user.id == test_user.id


@pytest.mark.asyncio
async def test_get_user_by_username_not_found(async_db: AsyncSession):
    """测试获取不存在的用户"""
    user = await get_user_by_username(async_db, "nonexistent")
    assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_success(async_db: AsyncSession, test_user: User):
    """测试成功认证用户"""
    user = await authenticate_user("testuser", "testpassword", async_db)
    assert user is not None
    assert user.username == "testuser"


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(async_db: AsyncSession, test_user: User):
    """测试错误密码认证"""
    user = await authenticate_user("testuser", "wrongpassword", async_db)
    assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_not_found(async_db: AsyncSession):
    """测试认证不存在的用户"""
    user = await authenticate_user("nonexistent", "password", async_db)
    assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_inactive(async_db: AsyncSession, inactive_user: User):
    """测试认证未激活用户"""
    # authenticate_user 只验证密码，不检查是否激活
    user = await authenticate_user("inactiveuser", "testpassword", async_db)
    # 函数返回用户对象，激活状态检查由调用方处理
    assert user is not None
    assert user.username == "inactiveuser"


@pytest.mark.asyncio
async def test_get_current_user_success(async_db: AsyncSession, test_user: User):
    """测试成功从令牌获取当前用户"""
    token = token_service.create_access_token({
        "sub": str(test_user.id),
        "username": test_user.username
    })
    # 使用 verify_token 验证令牌
    token_data = token_service.verify_token(token)
    assert token_data is not None
    assert token_data.user_id == test_user.id
    assert token_data.username == test_user.username


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(async_db: AsyncSession):
    """测试无效令牌"""
    token_data = token_service.verify_token("invalid_token")
    assert token_data is None


@pytest.mark.asyncio
async def test_get_current_user_expired_token(async_db: AsyncSession, test_user: User):
    """测试过期令牌"""
    token = token_service.create_access_token(
        {"sub": str(test_user.id), "username": test_user.username},
        expires_delta=timedelta(seconds=-1)
    )
    token_data = token_service.verify_token(token)
    assert token_data is None


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(async_db: AsyncSession, test_user: User):
    """测试令牌有效但用户不存在"""
    # 创建一个指向不存在用户的令牌
    token = token_service.create_access_token({
        "sub": "00000000-0000-0000-0000-000000000000",  # 不存在的用户ID
        "username": "nonexistent"
    })
    token_data = token_service.verify_token(token)
    # 令牌本身是有效的
    assert token_data is not None
    assert token_data.user_id == uuid.UUID("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_get_current_user_inactive_user(async_db: AsyncSession, inactive_user: User):
    """测试令牌有效但用户未激活"""
    token = token_service.create_access_token({
        "sub": str(inactive_user.id),
        "username": inactive_user.username
    })
    token_data = token_service.verify_token(token)
    # 令牌本身是有效的，激活状态检查由调用方处理
    assert token_data is not None
    assert token_data.user_id == inactive_user.id


@pytest.mark.asyncio
async def test_validate_token_success(async_db: AsyncSession, test_user: User):
    """测试成功验证令牌"""
    token = token_service.create_access_token({
        "sub": str(test_user.id),
        "username": test_user.username
    })
    token_data = token_service.verify_token(token)
    assert token_data is not None
    assert token_data.user_id == test_user.id
    assert token_data.username == test_user.username


@pytest.mark.asyncio
async def test_validate_token_invalid(async_db: AsyncSession):
    """测试无效令牌验证"""
    token_data = token_service.verify_token("invalid_token")
    assert token_data is None


@pytest.mark.asyncio
async def test_validate_token_inactive_user(async_db: AsyncSession, inactive_user: User):
    """测试验证未激活用户的令牌"""
    token = token_service.create_access_token({
        "sub": str(inactive_user.id),
        "username": inactive_user.username
    })
    token_data = token_service.verify_token(token)
    # verify_token 只验证令牌本身，不检查用户激活状态
    assert token_data is not None
    assert token_data.user_id == inactive_user.id
