"""
扩展 ProjectRecord 模型用于 Web UI

Revision ID: web_ui_002
Revises: web_ui_001
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'web_ui_002'
down_revision = 'web_ui_001'
branch_labels = None
depends_on = None


def upgrade():
    """升级：为 projects 表添加 Web UI 字段"""
    # 添加 owner_id 外键 - 使用 batch mode 支持 SQLite
    with op.batch_alter_table('projects') as batch_op:
        batch_op.add_column(
            sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True)
        )
    
    # 在 PostgreSQL 中创建外键，SQLite 在 batch mode 中会自动处理
    bind = op.get_bind()
    if bind.dialect.name != 'sqlite':
        op.create_foreign_key(
            'fk_projects_owner_id',
            'projects', 'users',
            ['owner_id'], ['id'],
            ondelete='CASCADE'
        )

    # 添加封面图片 URL
    with op.batch_alter_table('projects') as batch_op:
        batch_op.add_column(
            sa.Column('cover_image_url', sa.String(500), nullable=True)
        )


def downgrade():
    """降级：删除 Web UI 字段"""
    bind = op.get_bind()
    
    # 删除外键约束（仅 PostgreSQL）
    if bind.dialect.name != 'sqlite':
        op.drop_constraint('fk_projects_owner_id', 'projects', type_='foreignkey')
    
    # 使用 batch mode 删除列（支持 SQLite）
    with op.batch_alter_table('projects') as batch_op:
        batch_op.drop_column('cover_image_url')
        batch_op.drop_column('owner_id')
