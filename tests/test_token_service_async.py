"""
Token Service 异步测试

测试 Token 认证服务层的所有功能
"""
import uuid
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
    data = {"sub": "00000000-0000-0000-0000-000000000001", "username": "testuser"}
    token = token_service.create_access_token(data)
    verified = token_service.verify_token(token)
    assert verified is not None
    assert verified.user_id == uuid.UUID("00000000-0000-0000-0000-000000000001")


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


# =============================================================================
# F-010: JWT Token 刷新测试
# =============================================================================

def test_refresh_token_works():
    """
    测试使用刷新令牌获取新的访问令牌

    验证点：
    1. 有效的刷新令牌可以换取新的访问令牌
    2. 新的访问令牌包含正确的用户信息
    3. 新的访问令牌是有效的
    """
    # 创建用户数据
    test_uuid = "00000000-0000-0000-0000-000000000042"
    user_data = {"sub": test_uuid, "username": "refreshtest", "is_admin": False}

    # 创建刷新令牌
    refresh_token = token_service.create_refresh_token(user_data)
    assert refresh_token is not None

    # 验证刷新令牌
    token_data = token_service.verify_token(refresh_token, token_type="refresh")
    assert token_data is not None, "刷新令牌应该有效"
    assert token_data.user_id == uuid.UUID(test_uuid)
    assert token_data.username == "refreshtest"

    # 使用刷新令牌创建新的访问令牌
    new_access_token = token_service.create_access_token({
        "sub": str(token_data.user_id),
        "username": token_data.username,
        "is_admin": False
    })
    assert new_access_token is not None

    # 验证新的访问令牌有效
    new_token_data = token_service.verify_token(new_access_token, token_type="access")
    assert new_token_data is not None, "新的访问令牌应该有效"
    assert new_token_data.user_id == uuid.UUID(test_uuid)
    assert new_token_data.username == "refreshtest"


def test_refresh_token_with_wrong_type_fails():
    """
    测试使用错误类型的令牌刷新失败

    验证点：
    1. 使用访问令牌作为刷新令牌应该失败
    2. 验证应该检查令牌类型
    """
    # 创建访问令牌
    user_data = {"sub": "1", "username": "testuser"}
    access_token = token_service.create_access_token(user_data)

    # 尝试用访问令牌作为刷新令牌验证
    token_data = token_service.verify_token(access_token, token_type="refresh")
    assert token_data is None, "访问令牌不应该作为刷新令牌验证通过"


def test_refresh_token_expired():
    """
    测试过期的刷新令牌无效

    验证点：
    1. 过期的刷新令牌不能被使用
    2. 验证应该返回 None
    """
    # 创建已过期的刷新令牌
    user_data = {"sub": "1", "username": "testuser"}
    expired_refresh_token = token_service.create_refresh_token(
        user_data,
        expires_delta=timedelta(seconds=-1)
    )

    # 验证应该失败
    token_data = token_service.verify_token(expired_refresh_token, token_type="refresh")
    assert token_data is None, "过期的刷新令牌应该无效"


def test_refresh_token_invalid_signature():
    """
    测试签名无效的刷新令牌被拒绝

    验证点：
    1. 篡改的令牌应该被拒绝
    2. 验证应该返回 None
    """
    # 创建有效的刷新令牌
    user_data = {"sub": "1", "username": "testuser"}
    refresh_token = token_service.create_refresh_token(user_data)

    # 篡改令牌（修改最后一部分）
    tampered_token = refresh_token[:-10] + "XXXXXXXXXX"

    # 验证应该失败
    token_data = token_service.verify_token(tampered_token, token_type="refresh")
    assert token_data is None, "篡改的令牌应该无效"


@pytest.mark.asyncio
async def test_login_returns_refresh_token(async_db: AsyncSession, test_user):
    """
    测试登录接口返回刷新令牌

    验证点：
    1. 登录成功返回 refresh_token
    2. refresh_token 是有效的
    3. 可以使用 refresh_token 刷新 access_token
    """
    from services.user_service import login_user

    # 执行登录
    result = await login_user({
        "username": "testuser",
        "password": "testpassword"
    }, async_db)

    # 验证返回了刷新令牌
    assert "refresh_token" in result, "登录应该返回 refresh_token"
    refresh_token = result["refresh_token"]
    assert refresh_token is not None
    assert isinstance(refresh_token, str)

    # 验证刷新令牌有效
    token_data = token_service.verify_token(refresh_token, token_type="refresh")
    assert token_data is not None, "返回的 refresh_token 应该有效"
    assert token_data.user_id == test_user.id
    assert token_data.username == test_user.username
