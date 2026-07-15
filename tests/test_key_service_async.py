import uuid
"""
SSH Key 服务测试

F-019: SSH Key 管理
F-021: Authorized Keys 同步
"""

import pytest
import os
import tempfile
import asyncio
from unittest.mock import patch, MagicMock, mock_open
from sqlalchemy.ext.asyncio import AsyncSession

from services.key_service import (
    add_ssh_key,
    list_user_ssh_keys,
    delete_ssh_key,
    get_ssh_key_by_fingerprint,
    _calculate_fingerprint,
    _validate_ssh_key,
    sync_authorized_keys,
    get_authorized_keys_path,
)
from core.exception import ValidationException, NotFoundException, AuthorizationException


# ============ 基础工具函数测试 ============

def test_validate_ssh_key_valid_rsa():
    """测试验证有效的 RSA SSH Key"""
    valid_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"
    assert _validate_ssh_key(valid_key) is True


def test_validate_ssh_key_valid_ed25519():
    """测试验证有效的 Ed25519 SSH Key"""
    valid_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDIhz2GK/XCUj4i6Q5yQJNL1MXMY0RxzPV2QrBqfHrDq test@example.com"
    assert _validate_ssh_key(valid_key) is True


def test_validate_ssh_key_empty():
    """测试验证空 SSH Key"""
    assert _validate_ssh_key("") is False
    assert _validate_ssh_key(None) is False
    assert _validate_ssh_key("   ") is False


def test_validate_ssh_key_invalid_prefix():
    """测试验证无效前缀的 SSH Key"""
    invalid_key = "invalid-prefix AAAAB3NzaC1yc2E test@example.com"
    assert _validate_ssh_key(invalid_key) is False


def test_validate_ssh_key_invalid_base64():
    """测试验证 base64 无效的 SSH Key"""
    invalid_key = "ssh-rsa !!!invalid-base64!!! test@example.com"
    assert _validate_ssh_key(invalid_key) is False


def test_calculate_fingerprint_valid():
    """测试计算有效的 SSH Key fingerprint"""
    # 使用一个真实的 SSH 公钥格式
    valid_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"
    fingerprint = _calculate_fingerprint(valid_key)
    # 验证格式：应该是 xx:xx:xx:... 格式
    assert len(fingerprint) == 47  # 16 bytes * 2 hex chars + 15 colons
    assert fingerprint.count(":") == 15


def test_calculate_fingerprint_invalid_format():
    """测试计算无效格式的 SSH Key fingerprint"""
    with pytest.raises(ValidationException):
        _calculate_fingerprint("invalid-key")


# ============ SSH Key CRUD 测试 ============

@pytest.mark.asyncio
async def test_add_ssh_key_success(async_db: AsyncSession, async_test_user):
    """测试成功添加 SSH Key"""
    key_name = "My Laptop"
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"

    result = await add_ssh_key(async_db, async_test_user.id, key_name, public_key)

    assert result["name"] == key_name
    assert result["public_key"] == public_key.strip()
    assert "fingerprint" in result
    assert result["user_id"] == async_test_user.id


@pytest.mark.asyncio
async def test_add_ssh_key_invalid_format(async_db: AsyncSession, async_test_user):
    """测试添加无效格式的 SSH Key"""
    with pytest.raises(ValidationException) as exc_info:
        await add_ssh_key(async_db, async_test_user.id, "Test", "invalid-key")
    assert "Invalid SSH key format" in str(exc_info.value)


@pytest.mark.asyncio
async def test_add_ssh_key_duplicate(async_db: AsyncSession, async_test_user):
    """测试添加重复的 SSH Key"""
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"

    # 添加第一个 key
    await add_ssh_key(async_db, async_test_user.id, "Key 1", public_key)

    # 尝试添加相同的 key
    with pytest.raises(ValidationException) as exc_info:
        await add_ssh_key(async_db, async_test_user.id, "Key 2", public_key)
    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_user_ssh_keys(async_db: AsyncSession, async_test_user):
    """测试列出用户的 SSH Keys"""
    # 添加两个 key
    await add_ssh_key(async_db, async_test_user.id, "Key 1",
                      "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test1@example.com")
    await add_ssh_key(async_db, async_test_user.id, "Key 2",
                      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDIhz2GK/XCUj4i6Q5yQJNL1MXMY0RxzPV2QrBqfHrDq test2@example.com")

    keys = await list_user_ssh_keys(async_db, async_test_user.id)

    assert len(keys) == 2
    assert keys[0]["name"] in ["Key 1", "Key 2"]
    assert keys[1]["name"] in ["Key 1", "Key 2"]


@pytest.mark.asyncio
async def test_delete_ssh_key_success(async_db: AsyncSession, async_test_user):
    """测试成功删除 SSH Key"""
    # 添加 key
    result = await add_ssh_key(async_db, async_test_user.id, "To Delete",
                               "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com")
    key_id = result["id"]

    # 删除 key
    await delete_ssh_key(async_db, key_id, async_test_user.id)

    # 验证已删除
    keys = await list_user_ssh_keys(async_db, async_test_user.id)
    assert len(keys) == 0


@pytest.mark.asyncio
async def test_delete_ssh_key_not_found(async_db: AsyncSession, async_test_user):
    """测试删除不存在的 SSH Key"""
    with pytest.raises(NotFoundException) as exc_info:
        await delete_ssh_key(async_db, uuid.UUID("00000000-0000-0000-0000-000000000000"), async_test_user.id)
    assert "not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_ssh_key_unauthorized(async_db: AsyncSession, async_test_user, async_another_user):
    """测试无权删除他人的 SSH Key"""
    # 用户1添加 key
    result = await add_ssh_key(async_db, async_test_user.id, "My Key",
                               "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com")
    key_id = result["id"]

    # 用户2尝试删除
    with pytest.raises(AuthorizationException) as exc_info:
        await delete_ssh_key(async_db, key_id, async_another_user.id)
    assert "permission" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_ssh_key_by_fingerprint_success(async_db: AsyncSession, async_test_user):
    """测试通过 fingerprint 获取 SSH Key"""
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"
    fingerprint = _calculate_fingerprint(public_key)

    await add_ssh_key(async_db, async_test_user.id, "Test Key", public_key)

    key = await get_ssh_key_by_fingerprint(async_db, fingerprint)

    assert key.name == "Test Key"
    assert key.fingerprint == fingerprint


@pytest.mark.asyncio
async def test_get_ssh_key_by_fingerprint_not_found(async_db: AsyncSession):
    """测试通过 fingerprint 获取不存在的 SSH Key"""
    with pytest.raises(NotFoundException):
        await get_ssh_key_by_fingerprint(async_db, "aa:bb:cc:dd:ee:ff")


# ============ F-021: Authorized Keys 同步测试 ============

@pytest.mark.asyncio
async def test_get_authorized_keys_path():
    """测试获取 authorized_keys 文件路径"""
    path = get_authorized_keys_path()
    assert ".ssh" in path
    assert "authorized_keys" in path


@pytest.mark.asyncio
async def test_sync_authorized_keys_creates_file(async_db: AsyncSession, async_test_user):
    """测试 sync_authorized_keys 创建 authorized_keys 文件"""
    # 添加 SSH Key
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"
    await add_ssh_key(async_db, async_test_user.id, "Test Key", public_key)

    # 使用临时目录测试
    with tempfile.TemporaryDirectory() as tmpdir:
        auth_keys_path = os.path.join(tmpdir, "authorized_keys")

        with patch('services.key_service.get_authorized_keys_path', return_value=auth_keys_path):
            await sync_authorized_keys(async_db)

            # 验证文件已创建
            assert os.path.exists(auth_keys_path)

            # 验证内容包含 SSH Key
            with open(auth_keys_path, 'r') as f:
                content = f.read()
                assert public_key in content


@pytest.mark.asyncio
async def test_sync_authorized_keys_updates_existing_file(async_db: AsyncSession, async_test_user):
    """测试 sync_authorized_keys 更新已存在的 authorized_keys 文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        auth_keys_path = os.path.join(tmpdir, "authorized_keys")

        # 创建已存在的文件
        with open(auth_keys_path, 'w') as f:
            f.write("# Existing comment\n")
            f.write("ssh-rsa OLDKEY old@example.com\n")

        # 添加新的 SSH Key 到数据库
        public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"
        await add_ssh_key(async_db, async_test_user.id, "Test Key", public_key)

        with patch('services.key_service.get_authorized_keys_path', return_value=auth_keys_path):
            await sync_authorized_keys(async_db)

            # 验证文件内容已更新
            with open(auth_keys_path, 'r') as f:
                content = f.read()
                # 应该包含 Perseus 管理的标记
                assert "# Perseus managed keys" in content
                # 应该包含新的 key
                assert public_key in content


@pytest.mark.asyncio
async def test_sync_authorized_keys_multiple_users(async_db: AsyncSession, async_test_user, async_another_user):
    """测试 sync_authorized_keys 同步多个用户的 Keys"""
    # 添加多个用户的 Keys
    key1 = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 user1@example.com"
    key2 = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDIhz2GK/XCUj4i6Q5yQJNL1MXMY0RxzPV2QrBqfHrDq user2@example.com"

    await add_ssh_key(async_db, async_test_user.id, "User1 Key", key1)
    await add_ssh_key(async_db, async_another_user.id, "User2 Key", key2)

    with tempfile.TemporaryDirectory() as tmpdir:
        auth_keys_path = os.path.join(tmpdir, "authorized_keys")

        with patch('services.key_service.get_authorized_keys_path', return_value=auth_keys_path):
            await sync_authorized_keys(async_db)

            with open(auth_keys_path, 'r') as f:
                content = f.read()
                assert key1 in content
                assert key2 in content


@pytest.mark.asyncio
async def test_sync_authorized_keys_preserves_non_managed_keys(async_db: AsyncSession, async_test_user):
    """测试 sync_authorized_keys 保留非 Perseus 管理的 keys"""
    with tempfile.TemporaryDirectory() as tmpdir:
        auth_keys_path = os.path.join(tmpdir, "authorized_keys")

        # 创建包含非管理 keys 的文件
        with open(auth_keys_path, 'w') as f:
            f.write("# Manual key - not managed by Perseus\n")
            f.write("ssh-rsa MANUALKEY manual@example.com\n")

        # 添加 Perseus 管理的 key
        public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"
        await add_ssh_key(async_db, async_test_user.id, "Test Key", public_key)

        with patch('services.key_service.get_authorized_keys_path', return_value=auth_keys_path):
            await sync_authorized_keys(async_db)

            with open(auth_keys_path, 'r') as f:
                content = f.read()
                # 应该保留手动添加的 key
                assert "MANUALKEY" in content
                # 应该包含 Perseus 管理的 key
                assert public_key in content


@pytest.mark.asyncio
async def test_sync_authorized_keys_empty_database(async_db: AsyncSession):
    """测试 sync_authorized_keys 处理空数据库"""
    with tempfile.TemporaryDirectory() as tmpdir:
        auth_keys_path = os.path.join(tmpdir, "authorized_keys")

        with patch('services.key_service.get_authorized_keys_path', return_value=auth_keys_path):
            await sync_authorized_keys(async_db)

            # 验证文件已创建但内容为空（只有头部注释）
            assert os.path.exists(auth_keys_path)
            with open(auth_keys_path, 'r') as f:
                content = f.read()
                assert "# Perseus managed keys" in content


@pytest.mark.asyncio
async def test_sync_authorized_keys_creates_ssh_directory(async_db: AsyncSession, async_test_user):
    """测试 sync_authorized_keys 自动创建 .ssh 目录"""
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"
    await add_ssh_key(async_db, async_test_user.id, "Test Key", public_key)

    with tempfile.TemporaryDirectory() as tmpdir:
        ssh_dir = os.path.join(tmpdir, ".ssh")
        auth_keys_path = os.path.join(ssh_dir, "authorized_keys")

        with patch('services.key_service.get_authorized_keys_path', return_value=auth_keys_path):
            await sync_authorized_keys(async_db)

            # 验证目录已创建
            assert os.path.exists(ssh_dir)
            assert os.path.exists(auth_keys_path)


@pytest.mark.asyncio
async def test_sync_authorized_keys_file_permissions(async_db: AsyncSession, async_test_user):
    """测试 sync_authorized_keys 设置正确的文件权限"""
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"
    await add_ssh_key(async_db, async_test_user.id, "Test Key", public_key)

    with tempfile.TemporaryDirectory() as tmpdir:
        auth_keys_path = os.path.join(tmpdir, "authorized_keys")

        with patch('services.key_service.get_authorized_keys_path', return_value=auth_keys_path):
            await sync_authorized_keys(async_db)

            # 验证文件权限（在 Unix 系统上）
            if os.name != 'nt':  # 非 Windows 系统
                stat_info = os.stat(auth_keys_path)
                # 权限应该是 600 (rw-------)
                assert stat_info.st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_add_ssh_key_triggers_sync(async_db: AsyncSession, async_test_user):
    """测试添加 SSH Key 后触发 authorized_keys 同步"""
    with tempfile.TemporaryDirectory() as tmpdir:
        auth_keys_path = os.path.join(tmpdir, "authorized_keys")

        with patch('services.key_service.get_authorized_keys_path', return_value=auth_keys_path):
            public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"

            # 添加 key（应该触发同步）
            await add_ssh_key(async_db, async_test_user.id, "Test Key", public_key)

            # 验证文件已同步
            assert os.path.exists(auth_keys_path)
            with open(auth_keys_path, 'r') as f:
                assert public_key in f.read()


@pytest.mark.asyncio
async def test_delete_ssh_key_triggers_sync(async_db: AsyncSession, async_test_user):
    """测试删除 SSH Key 后触发 authorized_keys 同步"""
    with tempfile.TemporaryDirectory() as tmpdir:
        auth_keys_path = os.path.join(tmpdir, "authorized_keys")

        with patch('services.key_service.get_authorized_keys_path', return_value=auth_keys_path):
            # 先添加 key
            public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"
            result = await add_ssh_key(async_db, async_test_user.id, "Test Key", public_key)

            # 验证 key 已添加
            with open(auth_keys_path, 'r') as f:
                assert public_key in f.read()

            # 删除 key（应该触发同步）
            await delete_ssh_key(async_db, result["id"], async_test_user.id)

            # 验证 key 已从文件移除
            with open(auth_keys_path, 'r') as f:
                content = f.read()
                assert public_key not in content
