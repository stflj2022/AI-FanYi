"""
扩展 Job 模型用于 Web UI

Revision ID: web_ui_003
Revises: web_ui_002
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'web_ui_003'
down_revision = 'web_ui_002'
branch_labels = None
depends_on = None


def upgrade():
    """升级：为 jobs 表添加 Web UI 字段"""
    # 添加用户友好的状态和错误信息
    op.add_column(
        'jobs',
        sa.Column('user_friendly_status', sa.String(100), nullable=True)
    )
    op.add_column(
        'jobs',
        sa.Column('user_friendly_error', sa.Text(), nullable=True)
    )


def downgrade():
    """降级：删除 Web UI 字段"""
    op.drop_column('jobs', 'user_friendly_error')
    op.drop_column('jobs', 'user_friendly_status')
