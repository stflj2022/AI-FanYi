"""测试 Story Bible 服务"""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.core.models import StoryEntry, StoryEntryType
from filmdub.core.story_bible import StoryBibleService


class TestStoryBibleService:
    """测试 Story Bible 服务"""

    @pytest.fixture
    def service(self, db: AsyncSession):
        """创建服务实例"""
        return StoryBibleService(db)

    @pytest.fixture
    def project_id(self):
        """项目 ID（使用唯一 ID 避免测试间数据污染）"""
        import uuid
        return f"test_project_{uuid.uuid4().hex[:8]}"

    @pytest.mark.asyncio
    async def test_create_character_entry(self, service, project_id):
        """测试创建角色条目"""
        entry_data = {
            'project_id': project_id,
            'entry_type': 'character',
            'title': 'Walter White',
            'character_name': 'Walter White',
            'character_role': 'main',
            'personality': 'Complex, brilliant, initially timid later becomes ruthless',
            'speech_style': 'Precise, scientific, uses specific vocabulary',
        }

        entry = await service.create_entry(entry_data)

        assert entry.id is not None
        assert entry.project_id == project_id
        assert entry.entry_type == StoryEntryType.CHARACTER
        assert entry.character_name == 'Walter White'
        assert entry.character_role == 'main'

    @pytest.mark.asyncio
    async def test_create_relationship_entry(self, service, project_id):
        """测试创建关系条目"""
        entry_data = {
            'project_id': project_id,
            'entry_type': 'relationship',
            'title': 'Walter and Jesse',
            'from_character': 'Walter White',
            'to_character': 'Jesse Pinkman',
            'relationship_type': 'teacher_student',
        }

        entry = await service.create_entry(entry_data)

        assert entry.id is not None
        assert entry.entry_type == StoryEntryType.RELATIONSHIP
        assert entry.from_character == 'Walter White'
        assert entry.to_character == 'Jesse Pinkman'

    @pytest.mark.asyncio
    async def test_get_character_context(self, service, project_id):
        """测试获取角色上下文"""
        # 创建角色条目
        character_data = {
            'project_id': project_id,
            'entry_type': 'character',
            'title': 'Jesse Pinkman',
            'character_name': 'Jesse Pinkman',
            'character_role': 'main',
            'personality': 'Street-smart, emotional, loyal',
            'speech_style': 'Colloquial, uses slang',
        }
        await service.create_entry(character_data)

        # 创建关系条目
        relationship_data = {
            'project_id': project_id,
            'entry_type': 'relationship',
            'title': 'Jesse and Walter',
            'from_character': 'Jesse Pinkman',
            'to_character': 'Walter White',
            'relationship_type': 'student_teacher',
        }
        await service.create_entry(relationship_data)

        # 获取角色上下文
        context = await service.get_character_context(project_id, 'Jesse Pinkman')

        assert context['character_name'] == 'Jesse Pinkman'
        assert context['role'] == 'main'
        assert context['personality'] is not None
        assert len(context['relationships']) == 1

    @pytest.mark.asyncio
    async def test_get_story_bible(self, service, project_id):
        """测试获取完整 Story Bible"""
        # 创建多个条目
        character_data = {
            'project_id': project_id,
            'entry_type': 'character',
            'title': 'Skyler White',
            'character_name': 'Skyler White',
            'character_role': 'main',
        }
        await service.create_entry(character_data)

        event_data = {
            'project_id': project_id,
            'entry_type': 'event',
            'title': 'Walter diagnosed with cancer',
            'description': 'Walter learns he has lung cancer',
            'event_time': datetime(2008, 1, 1),
        }
        await service.create_entry(event_data)

        # 获取完整 Story Bible
        bible = await service.get_story_bible(project_id)

        assert bible['project_id'] == project_id
        assert len(bible['characters']) == 1
        assert len(bible['events']) == 1

    @pytest.mark.asyncio
    async def test_update_entry(self, service, project_id):
        """测试更新条目"""
        # 创建条目
        entry_data = {
            'project_id': project_id,
            'entry_type': 'character',
            'title': 'Hank Schrader',
            'character_name': 'Hank Schrader',
            'character_role': 'supporting',
        }
        entry = await service.create_entry(entry_data)

        # 更新条目
        updated = await service.update_entry(entry.id, {
            'personality': 'Brave, dedicated DEA agent',
            'speech_style': 'Law enforcement jargon, casual',
        })

        assert updated is not None
        assert updated.personality == 'Brave, dedicated DEA agent'

    @pytest.mark.asyncio
    async def test_delete_entry(self, service, project_id):
        """测试删除条目"""
        # 创建条目
        entry_data = {
            'project_id': project_id,
            'entry_type': 'character',
            'title': 'Gus Fring',
            'character_name': 'Gus Fring',
            'character_role': 'supporting',
        }
        entry = await service.create_entry(entry_data)

        # 删除条目
        result = await service.delete_entry(entry.id)

        assert result is True

        # 验证已删除
        deleted_entry = await service.get_entry(entry.id)
        assert deleted_entry is None
