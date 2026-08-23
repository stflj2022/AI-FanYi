"""
扩展 Character 模型用于 Web UI

Revision ID: web_ui_004
Revises: web_ui_003
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'web_ui_004'
down_revision = 'web_ui_003'
branch_labels = None
depends_on = None


def upgrade():
    """升级：为 characters 表添加 Web UI 字段"""
    # 添加头像 URL
    op.add_column(
        'characters',
        sa.Column('avatar_url', sa.String(500), nullable=True)
    )

    # 添加首次出现的剧集名称
    op.add_column(
        'characters',
        sa.Column('first_appearance_episode_name', sa.String(255), nullable=True)
    )


def downgrade():
    """降级：删除 Web UI 字段"""
    op.drop_column('characters', 'first_appearance_episode_name')
    op.drop_column('characters', 'avatar_url')
