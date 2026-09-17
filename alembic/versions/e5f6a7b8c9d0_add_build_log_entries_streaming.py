"""add_build_log_entries_streaming

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-17 14:00:00.000000

新增 build_log_entries 子表，为构建日志引入"分步 + 时间戳 + 增量拉取"（6.2 P2）：

- 每行日志独立成行：seq（build 内自增，从 1 起）、stream（stdout/stderr 分流）、
  line 内容、logged_at（timestamptz 时区感知写入时刻）；
- build_id -> build_status.id 级联删除（ondelete CASCADE），并建 (build_id, seq)
  唯一索引作为增量拉取 after_seq 的权威边界；
- 外部 CI runner 通过签名回调 log_entries 追加写入，不再整串覆盖 BuildStatus.logs。

兼容性：BuildStatus.logs（Text 整串）保留不动，旧 GET /builds/{id}/logs 不回退。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: 建 build_log_entries 子表（端到端增量日志权威来源）。"""
    op.create_table(
        "build_log_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("build_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("stream", sa.String(length=20), nullable=False),
        sa.Column("line", sa.Text(), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("seq >= 1", name="ck_build_log_entries_seq_positive"),
        sa.CheckConstraint(
            "stream IN ('stdout', 'stderr')",
            name="ck_build_log_entries_stream_valid",
        ),
        sa.ForeignKeyConstraint(
            ["build_id"], ["build_status.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("build_log_entries", schema=None) as batch_op:
        batch_op.create_index("ix_build_log_entries_id", ["id"], unique=False)
        batch_op.create_index("ix_build_log_entries_build_id", ["build_id"], unique=False)
        batch_op.create_index(
            "uq_build_log_entries_build_seq", ["build_id", "seq"], unique=True
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("build_log_entries", schema=None) as batch_op:
        batch_op.drop_index("uq_build_log_entries_build_seq")
        batch_op.drop_index("ix_build_log_entries_build_id")
        batch_op.drop_index("ix_build_log_entries_id")
    op.drop_table("build_log_entries")
