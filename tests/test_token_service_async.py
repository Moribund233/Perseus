"""
Token Service 异步测试

测试 Token 认证服务层的所有功能
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services import token_service
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


def test_create_access_token():
    """测试创建访问令牌"""
    data = {"sub": "1", "username": "testuser"}
    token = token_service.create_access_token(data)
    assert token is not None
    assert isinstance(token, str)


def test_create_access_token_with_expiry():
    """测试创建带过期时间的访问令牌"""
    data = {"sub": "1", "username": "testuser"}
    expires = timedelta(minutes=5)
    token = token_service.create_access_token(data, expires)
    assert token is not None


def test_create_refresh_token():
    """测试创建刷新令牌"""
    data = {"sub": "1", "username": "testuser"}
    token = token_service.create_refresh_token(data)
    assert token is not None
    assert isinstance(token, str)


def test_verify_password():
    """测试验证密码"""
    from utils.password_utils import get_password_hash, verify_password
    hashed = get_password_hash("testpassword")
    assert verify_password("testpassword", hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_verify_token_valid():
    """测试验证有效令牌"""
    data = {"sub": "1", "username": "testuser"}
    token = token_service.create_access_token(data)
    verified = token_service.verify_token(token)
    assert verified is not None
    assert verified.user_id == 1  # sub 会被转换为 int 类型的 user_id


def test_verify_token_invalid():
    """测试验证无效令牌"""
    verified = token_service.verify_token("invalid_token")
    assert verified is None


def test_verify_token_expired():
    """测试验证过期令牌"""
    data = {"sub": "1", "username": "testuser"}
    token = token_service.create_access_token(data, expires_delta=timedelta(seconds=-1))
    verified = token_service.verify_token(token)
    assert verified is None


def test_create_token_pair(test_user: User):
    """测试创建令牌对"""
    tokens = token_service.create_token_pair(test_user)
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert "token_type" in tokens
    assert tokens["token_type"] == "bearer"


def test_revoke_token():
    """测试撤销令牌"""
    token = token_service.create_access_token({"sub": "1"})
    result = token_service.revoke_token(token)
    assert result is True
