"""
协作邀请 token 撤销记录模型（邀请 token 生命周期补齐）

按 jti 记录被撤销的邀请 token（黑名单）。`verify_invite_token_active` 校验时
命中该表即视为失效，从而支持"签发后可撤销"。
"""
from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid as SAUuid
from sqlalchemy.orm import mapped_column

from models.base import BaseModel


class CollabInviteRevocation(BaseModel):
    """被撤销的协作邀请 token（按 jti 唯一）。"""

    __tablename__ = "collab_invite_revocations"

    jti = mapped_column(String(64), nullable=False, index=True)
    """邀请 token 的唯一标识 (JWT jti)"""

    doc_key = mapped_column(String(500), nullable=False)
    """邀请绑定的文档标识 (便于审计/按文档清理)"""

    revoked_by = mapped_column(
        SAUuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    """执行撤销的用户ID (仓库 owner/admin)"""

    expires_at = mapped_column(DateTime(timezone=True), nullable=True)
    """该 token 的原始过期时刻 (供后续清理已过期记录)"""

    __table_args__ = (
        Index("uq_collab_invite_revocations_jti", "jti", unique=True),
    )

    def __repr__(self) -> str:
        return f"<CollabInviteRevocation(jti={self.jti}, doc_key={self.doc_key})>"
