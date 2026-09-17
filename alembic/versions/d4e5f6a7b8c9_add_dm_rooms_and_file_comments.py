"""add_dm_rooms_and_file_comments

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-17 10:00:00.000000

新增:
- realtime_rooms.room_type 列 + repository_id 改为可空 (支持 DM 会话, F-203)
- direct_messages 表 (私聊会话对)
- file_comments 表 (行内评论锚定)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('realtime_rooms', schema=None) as batch_op:
        batch_op.add_column(sa.Column('room_type', sa.String(20), nullable=False, server_default='repository'))
        batch_op.alter_column('repository_id', existing_type=sa.Uuid(), nullable=True)

    op.create_table(
        'direct_messages',
        sa.Column('room_id', sa.Uuid(), nullable=False),
        sa.Column('user_a_id', sa.Uuid(), nullable=False),
        sa.Column('user_b_id', sa.Uuid(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['room_id'], ['realtime_rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_a_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user_b_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_a_id', 'user_b_id', name='uq_dm_pair'),
    )
    with op.batch_alter_table('direct_messages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_direct_messages_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_direct_messages_room_id'), ['room_id'], unique=True)

    op.create_table(
        'file_comments',
        sa.Column('repository_id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('branch', sa.String(length=100), nullable=True),
        sa.Column('commit_hash', sa.String(length=40), nullable=True),
        sa.Column('parent_id', sa.Uuid(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.CheckConstraint('line_number IS NULL OR line_number >= 1', name='ck_file_comment_line_positive'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['file_comments.id'], ),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('file_comments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_file_comments_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_file_comments_repository_id'), ['repository_id'], unique=False)
        batch_op.create_index('ix_file_comments_repo_file_created', ['repository_id', 'file_path', 'created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('file_comments', schema=None) as batch_op:
        batch_op.drop_index('ix_file_comments_repo_file_created')
        batch_op.drop_index(batch_op.f('ix_file_comments_repository_id'))
        batch_op.drop_index(batch_op.f('ix_file_comments_id'))
    op.drop_table('file_comments')

    with op.batch_alter_table('direct_messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_direct_messages_room_id'))
        batch_op.drop_index(batch_op.f('ix_direct_messages_id'))
    op.drop_table('direct_messages')

    with op.batch_alter_table('realtime_rooms', schema=None) as batch_op:
        batch_op.alter_column('repository_id', existing_type=sa.Uuid(), nullable=False)
        batch_op.drop_column('room_type')