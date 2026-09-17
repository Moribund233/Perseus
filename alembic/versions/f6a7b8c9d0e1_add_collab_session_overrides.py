"""add_collab_session_overrides

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-17 15:00:00.000000

新增 collab_session_overrides 表，支撑协作会话级角色覆盖层（3.5 权限即时性）：

- (doc_key, user_id) 唯一，记录该成员在该文档的权限覆盖（scope read/write）与踢出标记；
- scope 为 NULL 表示不覆盖权限；is_kicked 表示已被移出会话；
- user_id / created_by 外键到 users.id（删除用户级联清覆盖 / 发起人置空）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: 建 collab_session_overrides 表。"""
    op.create_table(
        "collab_session_overrides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("doc_key", sa.String(length=500), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=10), nullable=True),
        sa.Column("is_kicked", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "scope IS NULL OR scope IN ('read', 'write')",
            name="ck_collab_session_overrides_scope_valid",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("collab_session_overrides", schema=None) as batch_op:
        batch_op.create_index("ix_collab_session_overrides_id", ["id"], unique=False)
        batch_op.create_index("ix_collab_session_overrides_doc_key", ["doc_key"], unique=False)
        batch_op.create_index("ix_collab_session_overrides_user_id", ["user_id"], unique=False)
        batch_op.create_index(
            "uq_collab_session_overrides_doc_user",
            ["doc_key", "user_id"],
            unique=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("collab_session_overrides", schema=None) as batch_op:
        batch_op.drop_index("uq_collab_session_overrides_doc_user")
        batch_op.drop_index("ix_collab_session_overrides_user_id")
        batch_op.drop_index("ix_collab_session_overrides_doc_key")
        batch_op.drop_index("ix_collab_session_overrides_id")
    op.drop_table("collab_session_overrides")
