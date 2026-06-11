"""
认证控制器测试

测试认证相关的 API 端点
"""
import pytest
import pytest_asyncio
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import create_app
from models.user import User
from services import token_service
from utils.password_utils import get_password_hash


# 创建应用实例
app = create_app()
client = TestClient(app)


@pytest_asyncio.fixture
async def test_user(async_db: AsyncSession):
    """创建测试用户"""
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


# =============================================================================
# F-010: JWT Token 刷新 API 测试
# =============================================================================

@pytest.mark.asyncio
async def test_refresh_token_api_success(async_db: AsyncSession, test_user):
    """
    测试刷新 Token API 成功

    验证点：
    1. 使用有效的 refresh_token 可以获取新的 access_token
    2. 返回包含新的 refresh_token
    3. 新的令牌是有效的
    """
    # 创建刷新令牌
    refresh_token = token_service.create_refresh_token({
        "sub": str(test_user.id),
        "username": test_user.username,
        "is_admin": test_user.is_admin
    })

    # 调用刷新 API
    response = client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })

    # 验证响应
    assert response.status_code == 200, f"刷新 API 应该返回 200, 实际返回 {response.status_code}"
    data = response.json()

    # 验证返回了新的令牌
    assert "access_token" in data, "响应应该包含 access_token"
    assert "refresh_token" in data, "响应应该包含 refresh_token"
    assert data["token_type"] == "bearer", "token_type 应该是 bearer"

    # 验证新的访问令牌有效
    new_access_token = data["access_token"]
    token_data = token_service.verify_token(new_access_token, token_type="access")
    assert token_data is not None, "新的 access_token 应该有效"
    assert token_data.user_id == test_user.id
    assert token_data.username == test_user.username

    print("✓ test_refresh_token_api_success 通过")


@pytest.mark.asyncio
async def test_refresh_token_api_invalid_token():
    """
    测试使用无效的刷新令牌

    验证点：
    1. 无效的刷新令牌应该返回 401
    2. 错误信息应该明确
    """
    response = client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid.token.here"
    })

    assert response.status_code == 401, "无效的令牌应该返回 401"
    data = response.json()
    assert "detail" in data, "错误响应应该包含 detail"

    print("✓ test_refresh_token_api_invalid_token 通过")


@pytest.mark.asyncio
async def test_refresh_token_api_expired_token(async_db: AsyncSession, test_user):
    """
    测试使用过期的刷新令牌

    验证点：
    1. 过期的刷新令牌应该返回 401
    """
    # 创建已过期的刷新令牌
    expired_refresh_token = token_service.create_refresh_token(
        {"sub": str(test_user.id), "username": test_user.username, "is_admin": False},
        expires_delta=timedelta(seconds=-1)
    )

    response = client.post("/api/v1/auth/refresh", json={
        "refresh_token": expired_refresh_token
    })

    assert response.status_code == 401, "过期的令牌应该返回 401"

    print("✓ test_refresh_token_api_expired_token 通过")


@pytest.mark.asyncio
async def test_refresh_token_api_wrong_type_token(async_db: AsyncSession, test_user):
    """
    测试使用错误类型的令牌（access_token 作为 refresh_token）

    验证点：
    1. 使用 access_token 作为 refresh_token 应该返回 401
    """
    # 创建访问令牌
    access_token = token_service.create_access_token({
        "sub": str(test_user.id),
        "username": test_user.username,
        "is_admin": test_user.is_admin
    })

    response = client.post("/api/v1/auth/refresh", json={
        "refresh_token": access_token
    })

    assert response.status_code == 401, "错误类型的令牌应该返回 401"

    print("✓ test_refresh_token_api_wrong_type_token 通过")


@pytest.mark.asyncio
async def test_refresh_token_api_inactive_user(async_db: AsyncSession, inactive_user):
    """
    测试未激活用户无法刷新令牌

    验证点：
    1. 未激活用户的刷新请求应该返回 401
    """
    # 创建刷新令牌
    refresh_token = token_service.create_refresh_token({
        "sub": str(inactive_user.id),
        "username": inactive_user.username,
        "is_admin": inactive_user.is_admin
    })

    response = client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })

    assert response.status_code == 401, "未激活用户应该返回 401"

    print("✓ test_refresh_token_api_inactive_user 通过")


@pytest.mark.asyncio
async def test_refresh_token_api_missing_token():
    """
    测试缺少刷新令牌

    验证点：
    1. 请求体缺少 refresh_token 应该返回 422
    """
    response = client.post("/api/v1/auth/refresh", json={})

    assert response.status_code == 422, "缺少必需字段应该返回 422"

    print("✓ test_refresh_token_api_missing_token 通过")
