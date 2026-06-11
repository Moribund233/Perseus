"""
SSH Key 服务异步测试

F-019: SSH Key CRUD 测试
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_add_ssh_key_success(async_db: AsyncSession, async_test_user):
    """
    测试成功添加 SSH Key

    验证点：
    1. 可以添加有效的 SSH Key
    2. 返回的 key 包含正确信息
    3. Key 被正确存储到数据库
    """
    from services import key_service

    # 测试用的 SSH Public Key (格式: ssh-rsa AAAA... user@example.com)
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"
    key_name = "My Laptop"

    # 添加 SSH Key
    key = await key_service.add_ssh_key(
        async_db,
        user_id=async_test_user.id,
        name=key_name,
        public_key=public_key
    )

    # 验证返回结果
    assert key["name"] == key_name, "Key 名称应该匹配"
    assert key["public_key"] == public_key, "Public key 应该匹配"
    assert key["user_id"] == async_test_user.id, "User ID 应该匹配"
    assert key["id"] is not None, "应该有 ID"
    assert key["fingerprint"] is not None, "应该有 fingerprint"
    assert key["created_at"] is not None, "应该有创建时间"

    print("✓ test_add_ssh_key_success 通过")


@pytest.mark.asyncio
async def test_add_ssh_key_invalid_format(async_db: AsyncSession, async_test_user):
    """
    测试添加格式无效的 SSH Key

    验证点：
    1. 无效的 SSH Key 格式应该被拒绝
    2. 抛出 ValidationException
    """
    from services import key_service
    from core.exception import ValidationException

    # 无效的 SSH Key
    invalid_key = "not-a-valid-ssh-key"

    with pytest.raises(ValidationException) as exc_info:
        await key_service.add_ssh_key(
            async_db,
            user_id=async_test_user.id,
            name="Invalid Key",
            public_key=invalid_key
        )

    assert "invalid" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower(), \
        "错误信息应该提示格式无效"

    print("✓ test_add_ssh_key_invalid_format 通过")


@pytest.mark.asyncio
async def test_add_ssh_key_duplicate(async_db: AsyncSession, async_test_user):
    """
    测试添加重复的 SSH Key

    验证点：
    1. 同一个 SSH Key 不能被重复添加
    2. 抛出 ValidationException
    """
    from services import key_service
    from core.exception import ValidationException

    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQD1 duplicate@test.com"

    # 第一次添加成功
    await key_service.add_ssh_key(
        async_db,
        user_id=async_test_user.id,
        name="First Key",
        public_key=public_key
    )

    # 第二次添加应该失败
    with pytest.raises(ValidationException) as exc_info:
        await key_service.add_ssh_key(
            async_db,
            user_id=async_test_user.id,
            name="Second Key",
            public_key=public_key
        )

    assert "duplicate" in str(exc_info.value).lower() or "already" in str(exc_info.value).lower(), \
        "错误信息应该提示重复"

    print("✓ test_add_ssh_key_duplicate 通过")


@pytest.mark.asyncio
async def test_list_user_ssh_keys(async_db: AsyncSession, async_test_user):
    """
    测试列出用户的 SSH Keys

    验证点：
    1. 可以获取用户的所有 SSH Key
    2. 返回列表包含所有 key
    """
    from services import key_service

    # 添加两个 key
    await key_service.add_ssh_key(
        async_db,
        user_id=async_test_user.id,
        name="Key 1",
        public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQE1 key1@test.com"
    )
    await key_service.add_ssh_key(
        async_db,
        user_id=async_test_user.id,
        name="Key 2",
        public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQE2 key2@test.com"
    )

    # 获取列表
    keys = await key_service.list_user_ssh_keys(async_db, async_test_user.id)

    assert len(keys) == 2, "应该返回 2 个 key"
    key_names = [k["name"] for k in keys]
    assert "Key 1" in key_names, "应该包含 Key 1"
    assert "Key 2" in key_names, "应该包含 Key 2"

    print("✓ test_list_user_ssh_keys 通过")


@pytest.mark.asyncio
async def test_delete_ssh_key(async_db: AsyncSession, async_test_user):
    """
    测试删除 SSH Key

    验证点：
    1. 可以删除自己的 SSH Key
    2. 删除后 key 不再出现在列表中
    """
    from services import key_service

    # 添加 key
    key = await key_service.add_ssh_key(
        async_db,
        user_id=async_test_user.id,
        name="Key to Delete",
        public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQD3 delete@test.com"
    )

    # 删除 key
    await key_service.delete_ssh_key(
        async_db,
        key_id=key["id"],
        user_id=async_test_user.id
    )

    # 验证已删除
    keys = await key_service.list_user_ssh_keys(async_db, async_test_user.id)
    assert len(keys) == 0, "Key 应该被删除"

    print("✓ test_delete_ssh_key 通过")


@pytest.mark.asyncio
async def test_delete_ssh_key_not_owner(async_db: AsyncSession, async_test_user):
    """
    测试删除他人的 SSH Key

    验证点：
    1. 不能删除其他用户的 SSH Key
    2. 抛出 AuthorizationException
    """
    from services import key_service
    from core.exception import AuthorizationException
    from models.user import User

    # 创建另一个用户
    other_user = User(
        username="otheruser",
        email="other@example.com",
        password="hashedpassword"
    )
    async_db.add(other_user)
    await async_db.commit()
    await async_db.refresh(other_user)

    # 为 other_user 添加 key
    key = await key_service.add_ssh_key(
        async_db,
        user_id=other_user.id,
        name="Other's Key",
        public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQD4 other@test.com"
    )

    # async_test_user 尝试删除 other_user 的 key
    with pytest.raises(AuthorizationException):
        await key_service.delete_ssh_key(
            async_db,
            key_id=key["id"],
            user_id=async_test_user.id
        )

    print("✓ test_delete_ssh_key_not_owner 通过")


@pytest.mark.asyncio
async def test_get_ssh_key_fingerprint(async_db: AsyncSession, async_test_user):
    """
    测试获取 SSH Key 的 fingerprint

    验证点：
    1. 添加 key 时自动生成 fingerprint
    2. Fingerprint 格式正确
    """
    from services import key_service

    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQD5 fingerprint@test.com"

    key = await key_service.add_ssh_key(
        async_db,
        user_id=async_test_user.id,
        name="Key with Fingerprint",
        public_key=public_key
    )

    # 验证 fingerprint 存在且格式正确 (通常是 MD5 或 SHA256 格式)
    assert key["fingerprint"] is not None, "应该有 fingerprint"
    assert len(key["fingerprint"]) > 0, "fingerprint 不应为空"
    # Fingerprint 通常包含冒号分隔的十六进制字符或 SHA256 格式
    assert ":" in key["fingerprint"] or "SHA256:" in key["fingerprint"], \
        "fingerprint 格式应该正确"

    print("✓ test_get_ssh_key_fingerprint 通过")
