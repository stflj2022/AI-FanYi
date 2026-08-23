"""人物数据库服务"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from filmdub.apps.web.backend.models.character import Character, VoiceProfile
from filmdub.core.database import Base


class CharacterService:
    """人物数据库服务"""

    @staticmethod
    async def get_characters(
        db: AsyncSession,
        project_id: Optional[UUID] = None,
        search: Optional[str] = None,
        gender: Optional[str] = None,
        age_range: Optional[str] = None,
        role_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Character], int]:
        """获取人物列表"""
        query = select(Character)

        # 筛选条件
        conditions = []
        if project_id:
            conditions.append(Character.project_id == project_id)
        if gender:
            conditions.append(Character.gender == gender)
        if age_range:
            conditions.append(Character.age_range == age_range)
        if role_type:
            conditions.append(Character.role_type == role_type)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    Character.name.ilike(search_pattern),
                    Character.description.ilike(search_pattern),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # 获取总数
        count_query = select(Character.id).where(and_(*conditions)) if conditions else select(Character.id)
        count_result = await db.execute(count_query)
        total = len(count_result.scalars().all())

        # 分页和排序
        query = query.order_by(Character.name).offset(skip).limit(limit)
        result = await db.execute(query)
        characters = result.scalars().all()

        return characters, total

    @staticmethod
    async def get_character_by_id(db: AsyncSession, character_id: UUID) -> Optional[Character]:
        """根据 ID 获取人物"""
        result = await db.execute(select(Character).where(Character.id == character_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_character_by_name(db: AsyncSession, project_id: UUID, name: str) -> Optional[Character]:
        """根据项目 ID 和名称获取人物"""
        result = await db.execute(
            select(Character).where(
                and_(Character.project_id == project_id, Character.name == name)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_character(
        db: AsyncSession,
        project_id: UUID,
        name: str,
        gender: Optional[str] = None,
        age_range: Optional[str] = None,
        role_type: Optional[str] = None,
        description: Optional[str] = None,
        original_actor: Optional[str] = None,
        avatar_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Character:
        """创建人物"""
        character = Character(
            project_id=project_id,
            name=name,
            gender=gender,
            age_range=age_range,
            role_type=role_type,
            description=description,
            original_actor=original_actor,
            avatar_url=avatar_url,
            metadata=metadata or {},
        )
        db.add(character)
        await db.commit()
        await db.refresh(character)
        return character

    @staticmethod
    async def update_character(
        db: AsyncSession,
        character_id: UUID,
        name: Optional[str] = None,
        gender: Optional[str] = None,
        age_range: Optional[str] = None,
        role_type: Optional[str] = None,
        description: Optional[str] = None,
        original_actor: Optional[str] = None,
        avatar_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[Character]:
        """更新人物"""
        character = await CharacterService.get_character_by_id(db, character_id)
        if not character:
            return None

        if name is not None:
            character.name = name
        if gender is not None:
            character.gender = gender
        if age_range is not None:
            character.age_range = age_range
        if role_type is not None:
            character.role_type = role_type
        if description is not None:
            character.description = description
        if original_actor is not None:
            character.original_actor = original_actor
        if avatar_url is not None:
            character.avatar_url = avatar_url
        if metadata is not None:
            character.meta_data = metadata

        await db.commit()
        await db.refresh(character)
        return character

    @staticmethod
    async def delete_character(db: AsyncSession, character_id: UUID) -> bool:
        """删除人物"""
        character = await CharacterService.get_character_by_id(db, character_id)
        if not character:
            return False

        await db.delete(character)
        await db.commit()
        return True

    @staticmethod
    async def get_voice_profiles(
        db: AsyncSession,
        character_id: UUID,
    ) -> List[VoiceProfile]:
        """获取人物的音色档案"""
        result = await db.execute(
            select(VoiceProfile).where(VoiceProfile.character_id == character_id)
        )
        return result.scalars().all()

    @staticmethod
    async def create_voice_profile(
        db: AsyncSession,
        character_id: UUID,
        voice_id: str,
        provider: str,
        model: Optional[str] = None,
        style: Optional[str] = None,
        similarity_score: Optional[float] = None,
        is_active: bool = True,
        metadata: Optional[dict] = None,
    ) -> VoiceProfile:
        """创建音色档案"""
        voice_profile = VoiceProfile(
            character_id=character_id,
            voice_id=voice_id,
            provider=provider,
            model=model,
            style=style,
            similarity_score=similarity_score,
            is_active=is_active,
            metadata=metadata or {},
        )
        db.add(voice_profile)
        await db.commit()
        await db.refresh(voice_profile)
        return voice_profile

    @staticmethod
    async def update_voice_profile(
        db: AsyncSession,
        voice_profile_id: UUID,
        voice_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        style: Optional[str] = None,
        similarity_score: Optional[float] = None,
        is_active: Optional[bool] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[VoiceProfile]:
        """更新音色档案"""
        result = await db.execute(
            select(VoiceProfile).where(VoiceProfile.id == voice_profile_id)
        )
        voice_profile = result.scalar_one_or_none()
        if not voice_profile:
            return None

        if voice_id is not None:
            voice_profile.voice_id = voice_id
        if provider is not None:
            voice_profile.provider = provider
        if model is not None:
            voice_profile.model = model
        if style is not None:
            voice_profile.style = style
        if similarity_score is not None:
            voice_profile.similarity_score = similarity_score
        if is_active is not None:
            voice_profile.is_active = is_active
        if metadata is not None:
            voice_profile.meta_data = metadata

        await db.commit()
        await db.refresh(voice_profile)
        return voice_profile

    @staticmethod
    async def delete_voice_profile(db: AsyncSession, voice_profile_id: UUID) -> bool:
        """删除音色档案"""
        result = await db.execute(
            select(VoiceProfile).where(VoiceProfile.id == voice_profile_id)
        )
        voice_profile = result.scalar_one_or_none()
        if not voice_profile:
            return False

        await db.delete(voice_profile)
        await db.commit()
        return True
