"""Add config column to jobs table

Ticket 003: Job 级配置持久化（作业创建时携带 config，调度执行时需要读取）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b3c8d1e4f5a'
down_revision: Union[str, Sequence[str], None] = '606f4aa397a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add jobs.config JSON column."""
    op.add_column('jobs', sa.Column('config', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove jobs.config column."""
    op.drop_column('jobs', 'config')
