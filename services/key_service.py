"""
SSH Key 服务

F-019: SSH Key 管理
"""

import hashlib
import base64
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.ssh_key import SSHKey
from models.user import User
from core.exception import ValidationException, NotFoundException, AuthorizationException


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
    user_id: int,
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

    return ssh_key.to_dict()


async def list_user_ssh_keys(db: AsyncSession, user_id: int) -> List[Dict]:
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
    key_id: int,
    user_id: int
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
