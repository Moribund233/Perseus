"""add_collab_invite_revocations

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-17 16:00:00.000000

新增 collab_invite_revocations 表：按 jti 记录被撤销的协作邀请 token（黑名单），
支持邀请 token 的"签发后可撤销"。expires_at 记录原 token 过期时刻供后续清理。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: 建 collab_invite_revocations 表。"""
    op.create_table(
        "collab_invite_revocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("doc_key", sa.String(length=500), nullable=False),
        sa.Column("revoked_by", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["revoked_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("collab_invite_revocations", schema=None) as batch_op:
        batch_op.create_index("ix_collab_invite_revocations_id", ["id"], unique=False)
        batch_op.create_index("ix_collab_invite_revocations_jti", ["jti"], unique=False)
        batch_op.create_index("uq_collab_invite_revocations_jti", ["jti"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("collab_invite_revocations", schema=None) as batch_op:
        batch_op.drop_index("uq_collab_invite_revocations_jti")
        batch_op.drop_index("ix_collab_invite_revocations_jti")
        batch_op.drop_index("ix_collab_invite_revocations_id")
    op.drop_table("collab_invite_revocations")
