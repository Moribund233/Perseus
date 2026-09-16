"""add_watchers_and_watch_count

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-16 11:00:00.000000

新增仓库 Watch(关注) 能力: repositories.watch_count 列 + watchers 表 (F-205)。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('repositories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('watch_count', sa.Integer(), nullable=True))

    op.create_table(
        'watchers',
        sa.Column('repository_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('repository_id', 'user_id', name='uq_repo_user_watch'),
    )
    with op.batch_alter_table('watchers', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_watchers_id'), ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('watchers', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_watchers_id'))
    op.drop_table('watchers')

    with op.batch_alter_table('repositories', schema=None) as batch_op:
        batch_op.drop_column('watch_count')
