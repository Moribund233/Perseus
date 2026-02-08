"""
Token 认证服务

提供基于 JWT 的 Token 认证功能，替代 Basic Auth
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import secrets
import hashlib
import logging

from models.user import User
from models.db import get_db

# 配置
SECRET_KEY = secrets.token_urlsafe(32)  # 应该从配置文件读取
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 日志记录器
logger = logging.getLogger(__name__)


class TokenData:
    """Token 数据类"""
    def __init__(self, user_id: int, username: str, scopes: list = None):
        self.user_id = user_id
        self.username = username
        self.scopes = scopes or []


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
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
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
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_token_pair(user: User) -> Dict[str, str]:
    """
    创建访问令牌和刷新令牌对

    Args:
        user: 用户对象

    Returns:
        dict: 包含 access_token 和 refresh_token 的字典
    """
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "is_admin": user.is_admin
    }

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

    Args:
        token: JWT 令牌
        token_type: 期望的令牌类型（access 或 refresh）

    Returns:
        TokenData: 令牌数据，验证失败返回 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 检查令牌类型
        if payload.get("type") != token_type:
            logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
            return None

        user_id: int = int(payload.get("sub"))
        username: str = payload.get("username")

        if user_id is None or username is None:
            return None

        return TokenData(user_id=user_id, username=username)

    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """
    使用刷新令牌获取新的访问令牌

    Args:
        refresh_token: 刷新令牌

    Returns:
        dict: 新的令牌对，验证失败返回 None
    """
    token_data = verify_token(refresh_token, token_type="refresh")
    if not token_data:
        return None

    # 获取用户信息
    db = next(get_db())
    try:
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user or not user.is_active:
            return None

        return create_token_pair(user)
    finally:
        db.close()


def revoke_token(token: str) -> bool:
    """
    撤销令牌

    将令牌加入黑名单（实际实现需要 Redis 或数据库支持）

    Args:
        token: 要撤销的令牌

    Returns:
        bool: 是否成功撤销
    """
    # TODO: 实现令牌黑名单（需要 Redis 或数据库）
    # 这里仅作示例
    logger.info(f"Token revoked: {token[:10]}...")
    return True


def generate_api_token(user: User, name: str = "API Token") -> Dict[str, Any]:
    """
    生成个人访问令牌（PAT）

    用于 Git HTTP 协议认证和 API 访问

    Args:
        user: 用户对象
        name: 令牌名称

    Returns:
        dict: 包含令牌信息的字典
    """
    # 生成随机令牌
    raw_token = secrets.token_urlsafe(32)

    # 计算令牌哈希（用于存储）
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    # 创建令牌记录
    token_record = {
        "id": secrets.token_hex(16),
        "user_id": user.id,
        "name": name,
        "token_hash": token_hash,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat(),
        "last_used_at": None,
        "is_active": True
    }

    # TODO: 将 token_record 保存到数据库

    logger.info(f"API token generated for user {user.username}")

    return {
        "id": token_record["id"],
        "name": name,
        "token": raw_token,  # 仅显示一次
        "expires_at": token_record["expires_at"]
    }


def verify_api_token(token: str, db: Session) -> Optional[User]:
    """
    验证 API 令牌

    Args:
        token: API 令牌
        db: 数据库会话

    Returns:
        User: 用户对象，验证失败返回 None
    """
    # 计算令牌哈希
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # TODO: 从数据库查询令牌记录
    # 这里简化处理，实际应该查询数据库

    # 验证令牌格式
    if len(token) < 32:
        return None

    # 这里应该查询数据库验证令牌哈希
    # 简化处理：直接返回 None，需要实际实现
    return None


def get_current_user_from_token(
    token: str,
    db: Session,
    allow_api_token: bool = True
) -> Optional[User]:
    """
    从令牌获取当前用户

    支持 JWT 访问令牌和 API 令牌

    Args:
        token: 令牌字符串
        db: 数据库会话
        allow_api_token: 是否允许 API 令牌

    Returns:
        User: 用户对象，验证失败返回 None
    """
    # 尝试验证 JWT 令牌
    token_data = verify_token(token, token_type="access")
    if token_data:
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if user and user.is_active:
            return user
        return None

    # 尝试验证 API 令牌
    if allow_api_token:
        return verify_api_token(token, db)

    return None
