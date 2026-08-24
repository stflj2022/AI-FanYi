"""Story Bible 服务

剧情数据库服务，用于管理角色、事件、关系、时间线、剧情状态等剧情条目
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from .models import StoryEntry, StoryEntryType


class StoryBibleService:
    """Story Bible 服务"""

    def __init__(self, db: AsyncSession):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def create_entry(self, entry_data: Dict[str, Any]) -> StoryEntry:
        """创建剧情条目

        Args:
            entry_data: 条目数据

        Returns:
            创建的条目
        """
        entry_id = entry_data.get('id') or str(uuid.uuid4())

        entry = StoryEntry(
            id=entry_id,
            project_id=entry_data['project_id'],
            episode_id=entry_data.get('episode_id'),
            entry_type=StoryEntryType(entry_data['entry_type']),
            title=entry_data['title'],
            description=entry_data.get('description'),
            character_name=entry_data.get('character_name'),
            character_role=entry_data.get('character_role'),
            personality=entry_data.get('personality'),
            speech_style=entry_data.get('speech_style'),
            event_time=entry_data.get('event_time'),
            event_location=entry_data.get('event_location'),
            from_character=entry_data.get('from_character'),
            to_character=entry_data.get('to_character'),
            relationship_type=entry_data.get('relationship_type'),
            timeline_order=entry_data.get('timeline_order'),
            season=entry_data.get('season'),
            episode=entry_data.get('episode'),
            state_key=entry_data.get('state_key'),
            state_value=entry_data.get('state_value'),
            extra_data=entry_data.get('extra_data'),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def get_entry(self, entry_id: str) -> Optional[StoryEntry]:
        """获取剧情条目

        Args:
            entry_id: 条目 ID

        Returns:
            条目或 None
        """
        result = await self.db.execute(
            select(StoryEntry).where(StoryEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def list_entries(
        self,
        project_id: str,
        entry_type: Optional[StoryEntryType] = None,
        episode_id: Optional[str] = None,
        character_name: Optional[str] = None,
    ) -> List[StoryEntry]:
        """列出剧情条目

        Args:
            project_id: 项目 ID
            entry_type: 条目类型（可选）
            episode_id: 集数 ID（可选）
            character_name: 角色名称（可选）

        Returns:
            条目列表
        """
        conditions = [StoryEntry.project_id == project_id]

        if entry_type:
            conditions.append(StoryEntry.entry_type == entry_type)
        if episode_id:
            conditions.append(StoryEntry.episode_id == episode_id)
        if character_name:
            conditions.append(StoryEntry.character_name == character_name)

        result = await self.db.execute(
            select(StoryEntry).where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def get_character_context(self, project_id: str, character_name: str) -> Dict[str, Any]:
        """获取角色上下文（用于翻译）

        Args:
            project_id: 项目 ID
            character_name: 角色名称

        Returns:
            角色上下文字典
        """
        # 获取角色条目
        character_entries = await self.list_entries(
            project_id=project_id,
            entry_type=StoryEntryType.CHARACTER,
            character_name=character_name,
        )

        if not character_entries:
            return {}

        character = character_entries[0]

        # 获取关系条目
        relationship_entries = await self.list_entries(
            project_id=project_id,
            entry_type=StoryEntryType.RELATIONSHIP,
        )

        # 过滤与该角色相关的关系
        relationships = []
        for rel in relationship_entries:
            if rel.from_character == character_name or rel.to_character == character_name:
                relationships.append({
                    'type': rel.relationship_type,
                    'from': rel.from_character,
                    'to': rel.to_character,
                })

        # 获取剧情状态
        state_entries = await self.list_entries(
            project_id=project_id,
            entry_type=StoryEntryType.STATE,
        )

        return {
            'character_name': character.character_name,
            'role': character.character_role,
            'personality': character.personality,
            'speech_style': character.speech_style,
            'relationships': relationships,
            'current_states': [
                {'key': s.state_key, 'value': s.state_value}
                for s in state_entries
            ],
        }

    async def update_entry(self, entry_id: str, entry_data: Dict[str, Any]) -> Optional[StoryEntry]:
        """更新剧情条目

        Args:
            entry_id: 条目 ID
            entry_data: 更新数据

        Returns:
            更新后的条目或 None
        """
        entry = await self.get_entry(entry_id)
        if not entry:
            return None

        for key, value in entry_data.items():
            if hasattr(entry, key) and key not in ['id', 'created_at']:
                setattr(entry, key, value)

        entry.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def delete_entry(self, entry_id: str) -> bool:
        """删除剧情条目

        Args:
            entry_id: 条目 ID

        Returns:
            是否删除成功
        """
        entry = await self.get_entry(entry_id)
        if not entry:
            return False

        await self.db.delete(entry)
        await self.db.commit()
        return True

    async def get_story_bible(self, project_id: str, episode_id: Optional[str] = None) -> Dict[str, Any]:
        """获取完整的 Story Bible

        Args:
            project_id: 项目 ID
            episode_id: 集数 ID（可选）

        Returns:
            Story Bible 字典
        """
        all_entries = await self.list_entries(
            project_id=project_id,
            episode_id=episode_id,
        )

        # 按类型分组
        characters = [e for e in all_entries if e.entry_type == StoryEntryType.CHARACTER]
        events = [e for e in all_entries if e.entry_type == StoryEntryType.EVENT]
        relationships = [e for e in all_entries if e.entry_type == StoryEntryType.RELATIONSHIP]
        timelines = [e for e in all_entries if e.entry_type == StoryEntryType.TIMELINE]
        states = [e for e in all_entries if e.entry_type == StoryEntryType.STATE]

        return {
            'project_id': project_id,
            'episode_id': episode_id,
            'characters': [
                {
                    'id': c.id,
                    'name': c.character_name,
                    'role': c.character_role,
                    'personality': c.personality,
                    'speech_style': c.speech_style,
                }
                for c in characters
            ],
            'events': [
                {
                    'id': e.id,
                    'title': e.title,
                    'description': e.description,
                    'time': e.event_time.isoformat() if e.event_time else None,
                    'location': e.event_location,
                }
                for e in events
            ],
            'relationships': [
                {
                    'id': r.id,
                    'from': r.from_character,
                    'to': r.to_character,
                    'type': r.relationship_type,
                }
                for r in relationships
            ],
            'timeline': [
                {
                    'id': t.id,
                    'order': t.timeline_order,
                    'season': t.season,
                    'episode': t.episode,
                    'title': t.title,
                }
                for t in sorted(timelines, key=lambda x: x.timeline_order or 0)
            ],
            'states': [
                {
                    'id': s.id,
                    'key': s.state_key,
                    'value': s.state_value,
                }
                for s in states
            ],
        }
