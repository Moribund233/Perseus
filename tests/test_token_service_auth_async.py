"""
Token Service 认证功能异步测试

测试 Token 认证相关的核心功能
"""
import pytest
import pytest_asyncio
from datetime import timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models import BaseModel
from models.user import User
from services import token_service
from exception import AuthenticationException

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


@pytest.mark.asyncio
async def test_get_user_by_username_success(db: AsyncSession, test_user: User):
    """测试成功根据用户名获取用户"""
    user = await token_service.get_user_by_username(db, "testuser")
    assert user is not None
    assert user.username == "testuser"
    assert user.id == test_user.id


@pytest.mark.asyncio
async def test_get_user_by_username_not_found(db: AsyncSession):
    """测试获取不存在的用户"""
    user = await token_service.get_user_by_username(db, "nonexistent")
    assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_success(db: AsyncSession, test_user: User):
    """测试成功认证用户"""
    user = await token_service.authenticate_user(db, "testuser", "testpassword")
    assert user is not None
    assert user.username == "testuser"


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(db: AsyncSession, test_user: User):
    """测试错误密码认证"""
    with pytest.raises(AuthenticationException) as exc_info:
        await token_service.authenticate_user(db, "testuser", "wrongpassword")
    assert "Invalid username or password" in str(exc_info.value)


@pytest.mark.asyncio
async def test_authenticate_user_not_found(db: AsyncSession):
    """测试认证不存在的用户"""
    with pytest.raises(AuthenticationException) as exc_info:
        await token_service.authenticate_user(db, "nonexistent", "password")
    assert "Invalid username or password" in str(exc_info.value)


@pytest.mark.asyncio
async def test_authenticate_user_inactive(db: AsyncSession, inactive_user: User):
    """测试认证未激活用户"""
    with pytest.raises(AuthenticationException) as exc_info:
        await token_service.authenticate_user(db, "inactiveuser", "testpassword")
    assert "User account is disabled" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_current_user_success(db: AsyncSession, test_user: User):
    """测试成功从令牌获取当前用户"""
    token = token_service.create_access_token({
        "sub": str(test_user.id),
        "username": test_user.username
    })
    user = await token_service.get_current_user(db, token)
    assert user is not None
    assert user.id == test_user.id
    assert user.username == test_user.username


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(db: AsyncSession):
    """测试无效令牌"""
    with pytest.raises(AuthenticationException) as exc_info:
        await token_service.get_current_user(db, "invalid_token")
    assert "Invalid or expired token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_current_user_expired_token(db: AsyncSession, test_user: User):
    """测试过期令牌"""
    token = token_service.create_access_token(
        {"sub": str(test_user.id), "username": test_user.username},
        expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(AuthenticationException) as exc_info:
        await token_service.get_current_user(db, token)
    assert "Invalid or expired token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(db: AsyncSession):
    """测试令牌有效但用户不存在"""
    token = token_service.create_access_token({
        "sub": "9999",
        "username": "nonexistent"
    })
    with pytest.raises(AuthenticationException) as exc_info:
        await token_service.get_current_user(db, token)
    assert "User not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_current_user_inactive_user(db: AsyncSession, inactive_user: User):
    """测试令牌对应用户未激活"""
    token = token_service.create_access_token({
        "sub": str(inactive_user.id),
        "username": inactive_user.username
    })
    with pytest.raises(AuthenticationException) as exc_info:
        await token_service.get_current_user(db, token)
    assert "User account is disabled" in str(exc_info.value)


@pytest.mark.asyncio
async def test_validate_token_success(db: AsyncSession, test_user: User):
    """测试成功验证令牌"""
    token = token_service.create_access_token({
        "sub": str(test_user.id),
        "username": test_user.username
    })
    token_data = await token_service.validate_token(db, token)
    assert token_data is not None
    assert token_data.user_id == test_user.id
    assert token_data.username == test_user.username


@pytest.mark.asyncio
async def test_validate_token_invalid(db: AsyncSession):
    """测试无效令牌验证"""
    with pytest.raises(AuthenticationException) as exc_info:
        await token_service.validate_token(db, "invalid_token")
    assert "Invalid or expired token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_validate_token_inactive_user(db: AsyncSession, inactive_user: User):
    """测试验证未激活用户的令牌"""
    token = token_service.create_access_token({
        "sub": str(inactive_user.id),
        "username": inactive_user.username
    })
    with pytest.raises(AuthenticationException) as exc_info:
        await token_service.validate_token(db, token)
    assert "User account is disabled" in str(exc_info.value)
