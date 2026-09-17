"""
协作会话邀请 token 服务

短时 JWT (type="collab_invite"), 绑定 docKey + 权限档位 (read/write) + 过期时间。
仅仓库成员可签发 (由 controller 校验); 无仓库角色者凭该 token 获得会话级临时权限。
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_config
from models.collab_invite_revocation import CollabInviteRevocation

INVITE_TOKEN_TYPE = "collab_invite"
VALID_SCOPES = {"read", "write"}
DEFAULT_TTL_MINUTES = 60
MAX_TTL_MINUTES = 24 * 60


def create_invite_token(
    doc_key: str,
    scope: str,
    issued_by: uuid.UUID,
    username: str,
    ttl_minutes: Optional[int] = None,
) -> Dict[str, Any]:
    """
    签发协作邀请 token

    Args:
        doc_key: 绑定的文档标识 (repository_id:branch:path)
        scope: 权限档位, "read" 或 "write"
        issued_by: 签发者用户ID (仓库成员)
        username: 签发者用户名
        ttl_minutes: 有效期(分钟), 默认 60, 上限 24h

    Returns:
        dict: {token, doc_key, scope, expires_at}

    Raises:
        ValueError: scope 非法或 ttl 越界
    """
    if scope not in VALID_SCOPES:
        raise ValueError(f"Invalid scope: {scope}. Valid scopes: {', '.join(sorted(VALID_SCOPES))}")
    ttl = DEFAULT_TTL_MINUTES if ttl_minutes is None else ttl_minutes
    if ttl <= 0 or ttl > MAX_TTL_MINUTES:
        raise ValueError(f"Invalid ttl_minutes: {ttl}. Must be within (0, {MAX_TTL_MINUTES}]")

    security = get_config().security
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ttl)
    payload = {
        "type": INVITE_TOKEN_TYPE,
        "sub": str(issued_by),
        "username": username,
        "doc_key": doc_key,
        "scope": scope,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, security.secret_key, algorithm=security.algorithm)
    return {
        "token": token,
        "doc_key": doc_key,
        "scope": scope,
        "expires_at": expire.isoformat(),
    }


def verify_invite_token(token: Optional[str], doc_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    校验协作邀请 token

    Args:
        token: 邀请 token
        doc_key: 若提供, 校验 token 绑定的文档与之一致

    Returns:
        dict: {issued_by, username, doc_key, scope, jti}; 校验失败返回 None
    """
    if not token or not isinstance(token, str):
        return None
    token = token.strip()
    if token.count(".") != 2:
        return None

    try:
        security = get_config().security
        payload = jwt.decode(token, security.secret_key, algorithms=[security.algorithm])
    except JWTError:
        return None

    if payload.get("type") != INVITE_TOKEN_TYPE:
        return None
    if not payload.get("sub") or not payload.get("doc_key"):
        return None
    if payload.get("scope") not in VALID_SCOPES:
        return None
    if doc_key is not None and payload.get("doc_key") != doc_key:
        return None

    return {
        "issued_by": payload.get("sub"),
        "username": payload.get("username"),
        "doc_key": payload.get("doc_key"),
        "scope": payload.get("scope"),
        "jti": payload.get("jti"),
        "exp": payload.get("exp"),
    }


async def is_invite_token_revoked(db: AsyncSession, jti: Optional[str]) -> bool:
    """该 jti 是否已被撤销 (命中黑名单)。"""
    if not jti:
        return False
    result = await db.execute(
        select(CollabInviteRevocation.id).filter(CollabInviteRevocation.jti == jti)
    )
    return result.scalar_one_or_none() is not None


async def verify_invite_token_active(
    db: AsyncSession, token: Optional[str], doc_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    校验邀请 token 且未被撤销。

    在纯签名/时效校验 (verify_invite_token) 基础上叠加撤销黑名单检查；
    被撤销的 token 一律视为失效 (返回 None)。
    """
    info = verify_invite_token(token, doc_key=doc_key)
    if info is None:
        return None
    if await is_invite_token_revoked(db, info.get("jti")):
        return None
    return info


async def revoke_invite_token(
    db: AsyncSession, token: Optional[str], revoked_by: Optional[uuid.UUID] = None
) -> Optional[Dict[str, Any]]:
    """
    撤销邀请 token (按 jti 记入黑名单, 幂等)。

    Args:
        token: 待撤销的邀请 token
        revoked_by: 执行撤销的用户ID

    Returns:
        dict: {jti, doc_key, scope, expires_at}; token 非法/过期返回 None
    """
    info = verify_invite_token(token)
    if info is None:
        return None

    existing = await db.execute(
        select(CollabInviteRevocation).filter(
            CollabInviteRevocation.jti == info["jti"]
        )
    )
    if existing.scalar_one_or_none() is None:
        exp = info.get("exp")
        expires_at = (
            datetime.fromtimestamp(exp, tz=timezone.utc)
            if isinstance(exp, (int, float))
            else None
        )
        db.add(
            CollabInviteRevocation(
                jti=info["jti"],
                doc_key=info["doc_key"],
                revoked_by=revoked_by,
                expires_at=expires_at,
            )
        )
        await db.commit()

    return {
        "jti": info["jti"],
        "doc_key": info["doc_key"],
        "scope": info["scope"],
        "expires_at": info.get("exp"),
    }
