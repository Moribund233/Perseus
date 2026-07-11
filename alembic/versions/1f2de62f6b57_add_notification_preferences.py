"""add notification_preferences table

Revision ID: 1f2de62f6b57
Revises: a1b2c3d4e5f6
Create Date: 2026-06-22 21:19:59.615022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f2de62f6b57'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('notification_preferences',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('email_on_mention', sa.Boolean(), nullable=False),
    sa.Column('email_on_pr_review', sa.Boolean(), nullable=False),
    sa.Column('email_on_issue_comment', sa.Boolean(), nullable=False),
    sa.Column('email_on_pr_merge', sa.Boolean(), nullable=False),
    sa.Column('email_on_release', sa.Boolean(), nullable=False),
    sa.Column('in_app_on_mention', sa.Boolean(), nullable=False),
    sa.Column('in_app_on_pr_review', sa.Boolean(), nullable=False),
    sa.Column('in_app_on_issue_comment', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('notification_preferences', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notification_preferences_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_notification_preferences_user_id'), ['user_id'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('notification_preferences', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notification_preferences_user_id'))
        batch_op.drop_index(batch_op.f('ix_notification_preferences_id'))

    op.drop_table('notification_preferences')
