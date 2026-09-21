"""add_repo_search_index

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-09-20 18:00:00.000000

新增代码搜索索引表（内容来自 Git 对象，存入主库）：
- repo_search_files：每文件一行（repository_id, path, content, size）
- repo_search_state：记录已索引提交，用于增量维护与陈旧检测

PostgreSQL 侧额外创建 pg_trgm 扩展与 GIN 索引，加速 `content ILIKE '%q%'`
子串检索（pg_trgm 自 PG13 起为 trusted 扩展，库属主即可创建）；SQLite（dev）
跳过扩展与索引，使用 LIKE 扫描。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TRGM_INDEX = "ix_repo_search_files_content_trgm"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "repo_search_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "path", name="uq_repo_search_file"),
    )
    with op.batch_alter_table("repo_search_files", schema=None) as batch_op:
        batch_op.create_index("ix_repo_search_files_id", ["id"], unique=False)
        batch_op.create_index("ix_repo_search_files_repository_id", ["repository_id"], unique=False)

    op.create_table(
        "repo_search_state",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("indexed_commit", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", name="uq_repo_search_state_repository"),
    )
    with op.batch_alter_table("repo_search_state", schema=None) as batch_op:
        batch_op.create_index("ix_repo_search_state_id", ["id"], unique=False)

    # PostgreSQL：pg_trgm + GIN（子串检索）
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(
            f"CREATE INDEX {TRGM_INDEX} "
            "ON repo_search_files USING gin (content gin_trgm_ops)"
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(f"DROP INDEX IF EXISTS {TRGM_INDEX}")

    with op.batch_alter_table("repo_search_state", schema=None) as batch_op:
        batch_op.drop_index("ix_repo_search_state_id")
    op.drop_table("repo_search_state")

    with op.batch_alter_table("repo_search_files", schema=None) as batch_op:
        batch_op.drop_index("ix_repo_search_files_repository_id")
        batch_op.drop_index("ix_repo_search_files_id")
    op.drop_table("repo_search_files")
