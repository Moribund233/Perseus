"""
Token Service 异步测试

测试 Token 认证服务层的所有功能
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models import BaseModel
from models.user import User
from services import token_service
from core.exception import AuthenticationException

# 使用内存数据库进行测试
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db():
    """创建测试数据库会话"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(db: AsyncSession):
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        password=token_service.pwd_context.hash("testpassword"),
        full_name="Test User",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(db: AsyncSession):
    """创建未激活测试用户"""
    user = User(
        username="inactiveuser",
        email="inactive@example.com",
        password=token_service.pwd_context.hash("testpassword"),
        full_name="Inactive User",
        is_active=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
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
    hashed = token_service.pwd_context.hash("testpassword")
    assert token_service.pwd_context.verify("testpassword", hashed) is True
    assert token_service.pwd_context.verify("wrongpassword", hashed) is False


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
