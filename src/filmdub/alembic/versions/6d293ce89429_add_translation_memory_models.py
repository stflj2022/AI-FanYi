"""add_translation_memory_models

Revision ID: 6d293ce89429
Revises: story_bible_001
Create Date: 2026-08-25 01:04:33.880560

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d293ce89429'
down_revision: Union[str, Sequence[str], None] = 'story_bible_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create translation_memory_entries table
    op.create_table(
        'translation_memory_entries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=True),
        sa.Column('source_text', sa.Text(), nullable=False),
        sa.Column('translated_text', sa.Text(), nullable=False),
        sa.Column('source_lang', sa.String(length=10), nullable=False),
        sa.Column('target_lang', sa.String(length=10), nullable=False),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('character_name', sa.String(length=255), nullable=True),
        sa.Column('scene_description', sa.Text(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_tm_entry_project', 'translation_memory_entries', ['project_id'])
    op.create_index('idx_tm_entry_lang_pair', 'translation_memory_entries', ['source_lang', 'target_lang'])
    op.create_index('idx_tm_entry_source_text', 'translation_memory_entries', ['source_text'])
    op.create_index('idx_tm_entry_usage', 'translation_memory_entries', ['usage_count'])

    # Create glossary_terms table
    op.create_table(
        'glossary_terms',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=True),
        sa.Column('source_term', sa.String(length=500), nullable=False),
        sa.Column('target_term', sa.String(length=500), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('examples', sa.JSON(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_glossary_project', 'glossary_terms', ['project_id'])
    op.create_index('idx_glossary_source', 'glossary_terms', ['source_term'])
    op.create_index('idx_glossary_category', 'glossary_terms', ['category'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_glossary_category', 'glossary_terms')
    op.drop_index('idx_glossary_source', 'glossary_terms')
    op.drop_index('idx_glossary_project', 'glossary_terms')
    op.drop_table('glossary_terms')

    op.drop_index('idx_tm_entry_usage', 'translation_memory_entries')
    op.drop_index('idx_tm_entry_source_text', 'translation_memory_entries')
    op.drop_index('idx_tm_entry_lang_pair', 'translation_memory_entries')
    op.drop_index('idx_tm_entry_project', 'translation_memory_entries')
    op.drop_table('translation_memory_entries')
