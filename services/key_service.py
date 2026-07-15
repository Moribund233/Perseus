"""
SSH Key 服务

F-019: SSH Key 管理
F-021: Authorized Keys 同步
"""

import hashlib
import base64
import os
import logging
from typing import List, Dict
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.ssh_key import SSHKey
from models.user import User
from core.exception import ValidationException, NotFoundException, AuthorizationException

logger = logging.getLogger(__name__)

# authorized_keys 文件标记
PERSEUS_KEY_MARKER_START = "# Perseus managed keys - BEGIN"
PERSEUS_KEY_MARKER_END = "# Perseus managed keys - END"


def _calculate_fingerprint(public_key: str) -> str:
    """
    计算 SSH Key 的 fingerprint

    使用 MD5 格式: xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx
    """
    # 提取 key 部分（去掉前缀和注释）
    parts = public_key.strip().split()
    if len(parts) < 2:
        raise ValidationException(detail="Invalid SSH key format")

    # parts[0] 是类型 (ssh-rsa, ssh-ed25519 等)
    # parts[1] 是 base64 编码的 key
    key_data = parts[1]

    try:
        decoded = base64.b64decode(key_data)
        fingerprint = hashlib.md5(decoded).hexdigest()
        # 格式化为 xx:xx:xx:... 格式
        return ':'.join(fingerprint[i:i+2] for i in range(0, len(fingerprint), 2))
    except Exception:
        raise ValidationException(detail="Invalid SSH key format")


def _validate_ssh_key(public_key: str) -> bool:
    """
    验证 SSH Key 格式是否有效

    基本验证：
    1. 不能为空
    2. 应该以 ssh-rsa, ssh-ed25519, ecdsa-sha2-nistp256 等开头
    3. 应该有 base64 编码的部分
    """
    if not public_key or not public_key.strip():
        return False

    valid_prefixes = (
        'ssh-rsa',
        'ssh-ed25519',
        'ssh-dss',
        'ecdsa-sha2-nistp256',
        'ecdsa-sha2-nistp384',
        'ecdsa-sha2-nistp521',
    )

    parts = public_key.strip().split()
    if len(parts) < 2:
        return False

    if not any(parts[0].startswith(prefix) for prefix in valid_prefixes):
        return False

    # 尝试解码 base64 部分
    try:
        base64.b64decode(parts[1])
    except Exception:
        return False

    return True


async def add_ssh_key(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    public_key: str
) -> Dict:
    """
    添加 SSH Key

    Args:
        db: 异步数据库会话
        user_id: 用户 ID
        name: Key 名称
        public_key: SSH 公钥内容

    Returns:
        Dict: 创建的 key 信息

    Raises:
        ValidationException: Key 格式无效或重复
    """
    # 验证 key 格式
    if not _validate_ssh_key(public_key):
        raise ValidationException(detail="Invalid SSH key format")

    # 计算 fingerprint
    fingerprint = _calculate_fingerprint(public_key)

    # 检查是否已存在相同的 key
    result = await db.execute(
        select(SSHKey).filter(SSHKey.fingerprint == fingerprint)
    )
    if result.scalar_one_or_none():
        raise ValidationException(detail="SSH key already exists")

    # 创建 key
    ssh_key = SSHKey(
        name=name,
        public_key=public_key.strip(),
        fingerprint=fingerprint,
        user_id=user_id
    )

    db.add(ssh_key)
    await db.commit()
    await db.refresh(ssh_key)

    # F-021: 同步到 authorized_keys
    try:
        await sync_authorized_keys(db)
    except Exception as e:
        logger.warning(f"Failed to sync authorized_keys after adding key: {e}")

    return ssh_key.to_dict()


async def list_user_ssh_keys(db: AsyncSession, user_id: uuid.UUID) -> List[Dict]:
    """
    列出用户的所有 SSH Keys

    Args:
        db: 异步数据库会话
        user_id: 用户 ID

    Returns:
        List[Dict]: Key 列表
    """
    result = await db.execute(
        select(SSHKey).filter(SSHKey.user_id == user_id)
    )
    keys = result.scalars().all()
    return [key.to_dict() for key in keys]


async def delete_ssh_key(
    db: AsyncSession,
    key_id: uuid.UUID,
    user_id: uuid.UUID
) -> None:
    """
    删除 SSH Key

    Args:
        db: 异步数据库会话
        key_id: Key ID
        user_id: 用户 ID（用于权限验证）

    Raises:
        NotFoundException: Key 不存在
        AuthorizationException: 无权删除
    """
    result = await db.execute(
        select(SSHKey).filter(SSHKey.id == key_id)
    )
    key = result.scalar_one_or_none()

    if not key:
        raise NotFoundException(detail="SSH key not found")

    if key.user_id != user_id:
        raise AuthorizationException(detail="You don't have permission to delete this key")

    await db.delete(key)
    await db.commit()

    # F-021: 同步到 authorized_keys
    try:
        await sync_authorized_keys(db)
    except Exception as e:
        logger.warning(f"Failed to sync authorized_keys after deleting key: {e}")


async def get_ssh_key_by_fingerprint(
    db: AsyncSession,
    fingerprint: str
) -> SSHKey:
    """
    通过 fingerprint 获取 SSH Key

    Args:
        db: 异步数据库会话
        fingerprint: Key fingerprint

    Returns:
        SSHKey: Key 对象

    Raises:
        NotFoundException: Key 不存在
    """
    result = await db.execute(
        select(SSHKey).filter(SSHKey.fingerprint == fingerprint)
    )
    key = result.scalar_one_or_none()

    if not key:
        raise NotFoundException(detail="SSH key not found")

    return key


def get_authorized_keys_path() -> str:
    """
    获取 authorized_keys 文件路径

    Returns:
        str: authorized_keys 文件的完整路径
              默认返回 ~/.ssh/authorized_keys
    """
    # 获取用户主目录
    home_dir = os.path.expanduser("~")
    ssh_dir = os.path.join(home_dir, ".ssh")
    auth_keys_path = os.path.join(ssh_dir, "authorized_keys")
    return auth_keys_path


async def sync_authorized_keys(db: AsyncSession, auth_keys_path: str = None) -> None:
    """
    同步所有 SSH Key 到 authorized_keys 文件

    将数据库中所有 SSH Key 写入 authorized_keys 文件，同时保留
    文件中非 Perseus 管理的 key。

    Args:
        db: 异步数据库会话
        auth_keys_path: 可选，自定义 authorized_keys 文件路径
                       默认为 ~/.ssh/authorized_keys

    Raises:
        OSError: 文件操作失败
    """
    if auth_keys_path is None:
        auth_keys_path = get_authorized_keys_path()

    # 获取所有 SSH Keys
    result = await db.execute(select(SSHKey))
    all_keys = result.scalars().all()

    # 构建 Perseus 管理的 keys 内容
    perseus_keys_content = []
    perseus_keys_content.append(PERSEUS_KEY_MARKER_START)
    perseus_keys_content.append("")
    for key in all_keys:
        perseus_keys_content.append(f"# {key.name} (User ID: {key.user_id})")
        perseus_keys_content.append(key.public_key)
    perseus_keys_content.append("")
    perseus_keys_content.append(PERSEUS_KEY_MARKER_END)

    # 读取现有文件内容（保留非 Perseus 管理的 keys）
    non_perseus_lines = []
    if os.path.exists(auth_keys_path):
        try:
            with open(auth_keys_path, 'r') as f:
                lines = f.readlines()

            # 提取非 Perseus 管理的内容
            in_perseus_section = False
            for line in lines:
                stripped = line.strip()
                if stripped == PERSEUS_KEY_MARKER_START:
                    in_perseus_section = True
                    continue
                if stripped == PERSEUS_KEY_MARKER_END:
                    in_perseus_section = False
                    continue
                if not in_perseus_section:
                    non_perseus_lines.append(line.rstrip())
        except Exception as e:
            logger.warning(f"Failed to read existing authorized_keys: {e}")

    # 清理空行
    while non_perseus_lines and non_perseus_lines[-1] == "":
        non_perseus_lines.pop()

    # 构建新文件内容
    new_content_lines = []

    # 添加 Perseus 管理的 keys
    if perseus_keys_content:
        new_content_lines.extend(perseus_keys_content)

    # 添加非 Perseus 管理的 keys
    if non_perseus_lines:
        if new_content_lines:
            new_content_lines.append("")
        new_content_lines.extend(non_perseus_lines)

    # 确保文件以换行符结尾
    if new_content_lines and new_content_lines[-1] != "":
        new_content_lines.append("")

    # 创建 .ssh 目录（如果不存在）
    ssh_dir = os.path.dirname(auth_keys_path)
    if not os.path.exists(ssh_dir):
        try:
            os.makedirs(ssh_dir, mode=0o700)
            logger.info(f"Created SSH directory: {ssh_dir}")
        except Exception as e:
            logger.error(f"Failed to create SSH directory: {e}")
            raise

    # 写入文件
    content = "\n".join(new_content_lines)
    try:
        with open(auth_keys_path, 'w') as f:
            f.write(content)

        # 设置文件权限（仅在 Unix 系统上）
        if os.name != 'nt':
            os.chmod(auth_keys_path, 0o600)

        logger.info(f"Synchronized {len(all_keys)} SSH keys to {auth_keys_path}")
    except Exception as e:
        logger.error(f"Failed to write authorized_keys: {e}")
        raise
