"""
Token 认证服务

提供基于 JWT 的 Token 认证功能，替代 Basic Auth
"""
from datetime import datetime, timedelta, timezone
import uuid
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.revoked_token import RevokedToken
from core.config import get_config
from utils.password_utils import verify_password, get_password_hash

# 日志记录器
logger = logging.getLogger(__name__)


def _get_security_config():
    """获取安全配置（运行时读取，支持密钥轮换）"""
    config = get_config()
    return config.security


class TokenData:
    """Token 数据类"""
    def __init__(self, user_id: uuid.UUID, username: str, scopes: list | None = None, oauth_provider: Optional[str] = None, jti: Optional[str] = None):
        self.user_id = user_id
        self.username = username
        self.scopes = scopes or []
        self.oauth_provider = oauth_provider
        self.jti = jti


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建访问令牌

    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量

    Returns:
        str: JWT 令牌
    """
    security_config = _get_security_config()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=security_config.access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "jti": to_encode.get("jti") or uuid.uuid4().hex
    })

    encoded_jwt = jwt.encode(to_encode, security_config.secret_key, algorithm=security_config.algorithm)
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建刷新令牌

    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量

    Returns:
        str: JWT 刷新令牌
    """
    security_config = _get_security_config()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=security_config.refresh_token_expire_days)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": to_encode.get("jti") or uuid.uuid4().hex
    })

    encoded_jwt = jwt.encode(to_encode, security_config.secret_key, algorithm=security_config.algorithm)
    return encoded_jwt


def create_token_pair(user: User, extra_claims: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    创建访问令牌和刷新令牌对

    Args:
        user: 用户对象
        extra_claims: 额外要编码到令牌中的声明（可选）

    Returns:
        dict: 包含 access_token 和 refresh_token 的字典
    """
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "is_admin": user.is_admin
    }
    if extra_claims:
        token_data.update(extra_claims)

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """
    验证令牌

    执行严格的令牌验证：
    1. 检查令牌是否为空或无效格式
    2. 验证 JWT 签名和结构
    3. 检查令牌类型匹配
    4. 验证必需的声明字段

    Args:
        token: JWT 令牌
        token_type: 期望的令牌类型（access 或 refresh）

    Returns:
        TokenData: 令牌数据，验证失败返回 None
    """
    # 严格检查：空令牌、纯空白字符、或明显的无效格式
    if not token or not isinstance(token, str):
        logger.warning("Token is empty or not a string")
        return None

    token = token.strip()

    if not token or token.lower() in ('null', 'undefined', 'none', 'admin', 'user', 'test'):
        logger.warning(f"Token is empty or contains invalid keyword: {token}")
        return None

    # 检查 JWT 基本格式（应该包含两个点，分为三个部分）
    parts = token.split('.')
    if len(parts) != 3:
        logger.warning(f"Invalid JWT format: expected 3 parts, got {len(parts)}")
        return None

    # 检查每个部分是否为空
    if any(not part.strip() for part in parts):
        logger.warning("Invalid JWT format: empty part detected")
        return None

    try:
        security_config = _get_security_config()
        payload = jwt.decode(token, security_config.secret_key, algorithms=[security_config.algorithm])

        # 检查令牌类型
        if payload.get("type") != token_type:
            logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
            return None

        # 检查必需字段
        user_id = payload.get("sub")
        username = payload.get("username")

        if user_id is None or username is None:
            logger.warning("Token missing required claims: sub or username")
            return None

        # 验证 user_id 是有效的 UUID
        try:
            user_id = uuid.UUID(user_id)
        except (ValueError, TypeError):
            logger.warning(f"user_id is not a valid UUID: {user_id}")
            return None

        # 验证 username 是非空字符串
        if not isinstance(username, str) or not username.strip():
            logger.warning("username is empty or not a string")
            return None

        oauth_provider = payload.get("oauth_provider")
        if oauth_provider is not None and not isinstance(oauth_provider, str):
            oauth_provider = None

        return TokenData(
            user_id=user_id,
            username=username,
            oauth_provider=oauth_provider,
            jti=payload.get("jti"),
        )

    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None


async def refresh_access_token(refresh_token: str, db: AsyncSession) -> Optional[Dict[str, str]]:
    """
    使用刷新令牌获取新的访问令牌

    Args:
        refresh_token: 刷新令牌
        db: 异步数据库会话

    Returns:
        dict: 新的令牌对，验证失败返回 None
    """
    token_data = verify_token(refresh_token, token_type="refresh")
    if not token_data:
        return None

    # 获取用户信息
    result = await db.execute(select(User).filter(User.id == token_data.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None

    return create_token_pair(user)


async def is_token_revoked(db: AsyncSession, jti: Optional[str]) -> bool:
    """该 jti 是否已被撤销（命中黑名单）。"""
    if not jti:
        return False
    result = await db.execute(
        select(RevokedToken.id).filter(RevokedToken.jti == jti)
    )
    return result.scalar_one_or_none() is not None


async def revoke_token(
    db: AsyncSession,
    token: str,
    token_type: str = "access",
    revoked_by: Optional[uuid.UUID] = None,
) -> bool:
    """
    撤销令牌（按 jti 记入黑名单，幂等）

    Args:
        db: 异步数据库会话
        token: 要撤销的 JWT（access 或 refresh）
        token_type: 令牌类型，须与 token 的 type 声明一致
        revoked_by: 执行撤销的用户ID（可选，通常为 token 本人）

    Returns:
        bool: 是否成功撤销；token 非法、类型不符或缺少 jti 时返回 False
    """
    token_data = verify_token(token, token_type=token_type)
    if token_data is None or not token_data.jti:
        logger.warning("revoke_token: invalid token or missing jti")
        return False

    existing = await db.execute(
        select(RevokedToken).filter(RevokedToken.jti == token_data.jti)
    )
    if existing.scalar_one_or_none() is not None:
        return True

    payload = jwt.decode(
        token,
        _get_security_config().secret_key,
        algorithms=[_get_security_config().algorithm],
    )
    exp = payload.get("exp")
    expires_at = (
        datetime.fromtimestamp(exp, tz=timezone.utc)
        if isinstance(exp, (int, float))
        else None
    )

    db.add(
        RevokedToken(
            jti=token_data.jti,
            user_id=revoked_by or token_data.user_id,
            token_type=token_type,
            expires_at=expires_at,
        )
    )
    await db.commit()
    logger.info(f"Token revoked: jti={token_data.jti} type={token_type}")
    return True


async def verify_token_active(
    db: AsyncSession, token: str, token_type: str = "access"
) -> Optional[TokenData]:
    """
    校验令牌且未被撤销。

    在纯签名/时效校验（verify_token）基础上叠加撤销黑名单检查；
    被撤销的 token 一律视为失效（返回 None）。
    """
    token_data = verify_token(token, token_type=token_type)
    if token_data is None:
        return None
    if await is_token_revoked(db, token_data.jti):
        return None
    return token_data


