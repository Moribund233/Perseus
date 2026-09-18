"""add_revoked_tokens

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-18 10:00:00.000000

新增 revoked_tokens 表：按 jti 记录被撤销的访问/刷新 token（登出即时失效）。
expires_at 记录原 token 过期时刻，供后续清理已过期记录。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: 创建 revoked_tokens 表"""
    op.create_table(
        "revoked_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("token_type", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("revoked_tokens", schema=None) as batch_op:
        batch_op.create_index("ix_revoked_tokens_id", ["id"], unique=False)
        batch_op.create_index("ix_revoked_tokens_jti", ["jti"], unique=False)
        batch_op.create_index("uq_revoked_tokens_jti", ["jti"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("revoked_tokens", schema=None) as batch_op:
        batch_op.drop_index("uq_revoked_tokens_jti")
        batch_op.drop_index("ix_revoked_tokens_jti")
        batch_op.drop_index("ix_revoked_tokens_id")
    op.drop_table("revoked_tokens")
