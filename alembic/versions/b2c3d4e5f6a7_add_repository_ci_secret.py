"""add_repository_ci_secret

Revision ID: b2c3d4e5f6a7
Revises: a58c8a7aeb0a
Create Date: 2026-09-16 10:00:00.000000

为外部 CI runner 回调签名鉴权新增 repositories.ci_secret 列 (F-046)。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a58c8a7aeb0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('repositories', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('ci_secret', sa.String(length=128), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('repositories', schema=None) as batch_op:
        batch_op.drop_column('ci_secret')