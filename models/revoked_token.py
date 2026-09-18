"""
JWT 撤销记录模型（访问/刷新 token 黑名单）

按 jti 记录被撤销的访问/刷新 token。`verify_token_active` 校验时命中该表即视为
失效，从而支持"登出后 token 立即作废"。
"""
from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid as SAUuid
from sqlalchemy.orm import mapped_column

from models.base import BaseModel


class RevokedToken(BaseModel):
    """被撤销的 JWT（按 jti 唯一）。"""

    __tablename__ = "revoked_tokens"

    jti = mapped_column(String(64), nullable=False, index=True)
    """token 的唯一标识 (JWT jti)"""

    user_id = mapped_column(
        SAUuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    """token 所属用户ID (供审计/按用户清理)"""

    token_type = mapped_column(String(16), nullable=False, default="access")
    """token 类型: access / refresh"""

    expires_at = mapped_column(DateTime(timezone=True), nullable=True)
    """该 token 的原始过期时刻 (供后续清理已过期记录)"""

    __table_args__ = (
        Index("uq_revoked_tokens_jti", "jti", unique=True),
    )

    def __repr__(self) -> str:
        return f"<RevokedToken(jti={self.jti}, type={self.token_type})>"
