"""人物数据库服务"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from filmdub.core.models import Character, VoiceProfile
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

    @staticmethod
    async def get_characters_by_series(
        db: AsyncSession,
        series_name: Optional[str] = None,
        season_number: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Character], int]:
        """根据剧集名称和季数获取人物列表（用于跨集复用）
        
        注意：此功能需要在 Project 模型中添加 series_name 和 season_number 字段
        当前实现通过 project_id 查询，实际使用需要扩展数据模型
        """
        # TODO: 当 Project 模型添加 series_name 和 season_number 字段后实现
        # 当前返回空列表
        return [], 0

    @staticmethod
    async def copy_character_to_project(
        db: AsyncSession,
        source_character_id: UUID,
        target_project_id: UUID,
        copy_voice_profile: bool = True,
    ) -> Optional[Character]:
        """将人物复制到目标项目（跨集复用）
        
        Args:
            db: 数据库会话
            source_character_id: 源人物 ID
            target_project_id: 目标项目 ID
            copy_voice_profile: 是否同时复制音色档案
        
        Returns:
            新创建的人物对象
        """
        # 获取源人物
        source_character = await CharacterService.get_character_by_id(db, source_character_id)
        if not source_character:
            return None

        # 检查目标项目是否已存在同名人物
        existing = await CharacterService.get_character_by_name(
            db, target_project_id, source_character.name
        )
        if existing:
            return existing

        # 创建新人物
        new_character = await CharacterService.create_character(
            db=db,
            project_id=target_project_id,
            name=source_character.name,
            gender=source_character.gender,
            age_range=source_character.age_range,
            role_type=source_character.role_type,
            description=source_character.description,
            original_actor=source_character.actor_name,
            avatar_url=source_character.avatar_url,
            metadata=source_character.relationships if source_character.relationships else {},
        )

        # 如果需要复制音色档案
        if copy_voice_profile:
            source_voice_profiles = await CharacterService.get_voice_profiles(db, source_character_id)
            for vp in source_voice_profiles:
                await CharacterService.create_voice_profile(
                    db=db,
                    character_id=new_character.id,
                    voice_id=vp.voice_id,
                    provider=vp.provider,
                    model=vp.model,
                    style=vp.style,
                    similarity_score=vp.similarity_score,
                    is_active=vp.is_active,
                    metadata=vp.metadata if vp.metadata else {},
                )

        return new_character

    @staticmethod
    async def get_available_characters_for_project(
        db: AsyncSession,
        project_id: UUID,
        exclude_project_id: UUID,
    ) -> List[dict]:
        """获取可以复制到目标项目的人物列表
        
        Args:
            db: 数据库会话
            project_id: 源项目 ID（可选，用于筛选同一剧集的项目）
            exclude_project_id: 排除的目标项目 ID
        
        Returns:
            可用人物列表，包含项目信息和人物信息
        """
        # 查询所有其他项目的人物
        query = select(Character).where(Character.project_id != exclude_project_id)
        if project_id:
            query = query.where(Character.project_id == project_id)
        
        result = await db.execute(query.order_by(Character.name))
        characters = result.scalars().all()

        # 按项目分组
        grouped: dict = {}
        for char in characters:
            if char.project_id not in grouped:
                grouped[char.project_id] = {
                    "project_id": str(char.project_id),
                    "characters": [],
                }
            grouped[char.project_id]["characters"].append({
                "id": str(char.id),
                "name": char.name,
                "gender": char.gender,
                "age_range": char.age_range,
                "role_type": char.role_type,
                "actor_name": char.actor_name,
                "has_voice_profile": True,  # 需要实际查询
            })

        return list(grouped.values())
