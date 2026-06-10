"""
密码工具模块

提供统一的密码哈希和验证功能
"""
from passlib.context import CryptContext

# 密码哈希上下文（全局单例）
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# 常量定义
MAX_PASSWORD_LENGTH = 72  # bcrypt 最大支持长度


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        bool: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    获取密码哈希

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码

    Raises:
        ValueError: 密码长度超过 bcrypt 最大支持长度
    """
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password too long (max {MAX_PASSWORD_LENGTH} characters)")
    return pwd_context.hash(password)
