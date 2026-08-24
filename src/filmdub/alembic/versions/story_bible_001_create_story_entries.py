"""创建 Story Bible 表

实现 Story Bible（剧情数据库）作为长期资产，存储角色/事件/关系/时间线/剧情状态
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'story_bible_001'
down_revision: Union[str, Sequence[str], None] = 'web_ui_005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 story_entries 表"""
    op.create_table(
        'story_entries',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('project_id', sa.String(50), nullable=False),
        sa.Column('episode_id', sa.String(50), nullable=True),
        sa.Column('entry_type', sa.Enum('character', 'event', 'relationship', 'timeline', 'state', name='storyentrytype'), nullable=False),
        
        # 条目内容
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        
        # 角色相关字段
        sa.Column('character_name', sa.String(100), nullable=True),
        sa.Column('character_role', sa.String(50), nullable=True),
        sa.Column('personality', sa.Text(), nullable=True),
        sa.Column('speech_style', sa.Text(), nullable=True),
        
        # 事件相关字段
        sa.Column('event_time', sa.DateTime(), nullable=True),
        sa.Column('event_location', sa.String(200), nullable=True),
        
        # 关系相关字段
        sa.Column('from_character', sa.String(100), nullable=True),
        sa.Column('to_character', sa.String(100), nullable=True),
        sa.Column('relationship_type', sa.String(50), nullable=True),
        
        # 时间线相关字段
        sa.Column('timeline_order', sa.Integer(), nullable=True),
        sa.Column('season', sa.Integer(), nullable=True),
        sa.Column('episode', sa.Integer(), nullable=True),
        
        # 剧情状态相关字段
        sa.Column('state_key', sa.String(100), nullable=True),
        sa.Column('state_value', sa.Text(), nullable=True),
        
        # 元数据
        sa.Column('extra_data', postgresql.JSON(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # 创建索引
    op.create_index('idx_story_entry_project', 'story_entries', ['project_id'])
    op.create_index('idx_story_entry_episode', 'story_entries', ['episode_id'])
    op.create_index('idx_story_entry_type', 'story_entries', ['entry_type'])
    op.create_index('idx_story_entry_character', 'story_entries', ['character_name'])


def downgrade() -> None:
    """删除 story_entries 表"""
    op.drop_index('idx_story_entry_character', table_name='story_entries')
    op.drop_index('idx_story_entry_type', table_name='story_entries')
    op.drop_index('idx_story_entry_episode', table_name='story_entries')
    op.drop_index('idx_story_entry_project', table_name='story_entries')
    op.drop_table('story_entries')
    op.execute('DROP TYPE IF EXISTS storyentrytype')
