"""add_ssh_keys_table

Revision ID: 42017859e904
Revises: 1143975a9442
Create Date: 2026-06-11 09:11:20.332921

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '42017859e904'
down_revision: Union[str, Sequence[str], None] = '1143975a9442'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('ssh_keys',
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('public_key', sa.Text(), nullable=False),
        sa.Column('fingerprint', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('ssh_keys', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ssh_keys_fingerprint'), ['fingerprint'], unique=False)
        batch_op.create_index(batch_op.f('ix_ssh_keys_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('ssh_keys')
