"""Add CANCELLED to projectstatus enum and config to jobs table

Ticket 003: 项目取消生命周期支持（cancel_project 需要持久化 CANCELLED 状态），
以及作业级 config 持久化。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c9d0e2f1a3b'
down_revision: Union[str, Sequence[str], None] = '2b3c8d1e4f5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Recreate projects.status with CANCELLED enum value."""
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("projects") as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=sa.Enum(
                    'PENDING', 'INTAKE', 'PROCESSING', 'REVIEW',
                    'COMPLETED', 'FAILED', 'CANCELLED', 'ARCHIVED',
                    name='projectstatus',
                ),
                nullable=False,
            )
    else:
        op.alter_column(
            "projects",
            "status",
            existing_type=sa.Enum(
                'PENDING', 'INTAKE', 'PROCESSING', 'REVIEW',
                'COMPLETED', 'FAILED', 'CANCELLED', 'ARCHIVED',
                name='projectstatus',
            ),
            nullable=False,
        )


def downgrade() -> None:
    """Restore the previous status enum (without CANCELLED)."""
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("projects") as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=sa.Enum(
                    'PENDING', 'INTAKE', 'PROCESSING', 'REVIEW',
                    'COMPLETED', 'FAILED', 'ARCHIVED',
                    name='projectstatus',
                ),
                nullable=False,
            )
    else:
        op.alter_column(
            "projects",
            "status",
            existing_type=sa.Enum(
                'PENDING', 'INTAKE', 'PROCESSING', 'REVIEW',
                'COMPLETED', 'FAILED', 'ARCHIVED',
                name='projectstatus',
            ),
            nullable=False,
        )
