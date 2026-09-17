"""
协作会话级角色覆盖层模型（3.5 权限即时性 / M2 余项）

会话发起人（仓库 owner/admin）可对单个协作文档的参与者：
- 覆盖权限档位（scope: read / write），优先于仓库角色与邀请 token；
- 踢出会话（is_kicked），即时拒绝其连接鉴权与保存。

覆盖以 (doc_key, user_id) 唯一。scope 为 NULL 表示不覆盖权限（仅清空/或仅踢出）。
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Uuid as SAUuid,
)
from sqlalchemy.orm import mapped_column

from models.base import BaseModel


class CollabSessionOverride(BaseModel):
    """单文档内某成员的会话级权限覆盖 / 踢出标记。"""

    __tablename__ = "collab_session_overrides"

    doc_key = mapped_column(String(500), nullable=False, index=True)
    """文档标识 repository_id:branch:path"""

    user_id = mapped_column(
        SAUuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    """被覆盖的成员用户ID"""

    scope = mapped_column(String(10), nullable=True)
    """覆盖的权限档位: read / write; NULL 表示不覆盖权限"""

    is_kicked = mapped_column(Boolean, nullable=False, default=False)
    """是否已被移出该协作会话"""

    created_by = mapped_column(
        SAUuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    """设置该覆盖的发起人用户ID"""

    __table_args__ = (
        CheckConstraint(
            "scope IS NULL OR scope IN ('read', 'write')",
            name="ck_collab_session_overrides_scope_valid",
        ),
        # 每 (doc_key, user_id) 唯一: 覆盖层的权威键
        Index(
            "uq_collab_session_overrides_doc_user",
            "doc_key",
            "user_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CollabSessionOverride(doc_key={self.doc_key}, user_id={self.user_id}, "
            f"scope={self.scope}, is_kicked={self.is_kicked})>"
        )
