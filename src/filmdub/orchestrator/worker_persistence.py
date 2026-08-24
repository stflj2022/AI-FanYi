"""
Worker 数据库持久化服务

打通 worker 产出与 orchestrator 数据库
"""
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from filmdub.orchestrator.models import Character, VoiceProfile, Project

logger = logging.getLogger(__name__)


class WorkerDBPersistence:
    """Worker 数据库持久化服务"""

    def __init__(self, db: AsyncSession):
        """
        初始化持久化服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def _get_or_create_project(self, project_id: str) -> uuid.UUID:
        """
        获取或创建项目（返回真实的 UUID）

        Args:
            project_id: 项目标识符（可能是字符串 ID）

        Returns:
            项目 UUID
        """
        # 尝试查找现有项目
        result = await self.db.execute(
            select(Project).where(Project.name == project_id)
        )
        project = result.scalar_one_or_none()

        if project:
            return project.id

        # 创建新项目
        project = Project(
            name=project_id,
            status="processing",
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)

        return project.id

    async def _resolve_project_uuid(self, project_id) -> uuid.UUID:
        """
        把项目标识符解析为真实的 project UUID（纯查询，不创建）

        接受：uuid.UUID 对象、UUID 格式字符串、或项目名（Project.name）字符串。
        项目不存在时抛出 ValueError，避免查询路径意外创建项目。

        Args:
            project_id: 项目标识符（UUID / UUID 字符串 / 项目名）

        Returns:
            项目 UUID

        Raises:
            ValueError: 项目无法解析为现有项目
        """
        if isinstance(project_id, uuid.UUID):
            return project_id

        # 字符串：先尝试按 UUID 解析
        try:
            return uuid.UUID(str(project_id))
        except (ValueError, TypeError, AttributeError):
            pass

        # 否则按项目名查询
        result = await self.db.execute(
            select(Project.id).where(Project.name == str(project_id))
        )
        project_id_uuid = result.scalar_one_or_none()
        if project_id_uuid is not None:
            return project_id_uuid

        raise ValueError(f"Project not found: {project_id}")

    async def save_character(
        self,
        project_id: str,
        character_data: Dict[str, Any],
    ) -> Character:
        """
        保存人物信息到 orchestrator 数据库

        Args:
            project_id: 项目 ID
            character_data: 人物数据（来自 character_db worker）

        Returns:
            保存的 Character 对象
        """
        # 获取真实的 project UUID
        project_uuid = await self._get_or_create_project(project_id)

        # 检查是否已存在
        existing = await self.get_character_by_name(project_uuid, character_data.get("name"))

        if existing:
            # 更新现有记录
            existing.name_en = character_data.get("name_en")
            existing.aliases = character_data.get("aliases", [])
            existing.gender = character_data.get("gender")
            existing.age_range = character_data.get("age_range")
            existing.role_type = character_data.get("role_type")
            existing.actor_name = character_data.get("actor_name")
            existing.description = character_data.get("description")
            existing.personality = character_data.get("personality")
            existing.speech_pattern = character_data.get("speech_pattern")
            existing.relationships = character_data.get("relationships", {})
            existing.is_active = character_data.get("is_active", True)
            existing.updated_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(existing)

            logger.info(f"Updated character: {existing.name}")
            return existing

        # 创建新记录
        character = Character(
            project_id=project_uuid,
            name=character_data.get("name"),
            name_en=character_data.get("name_en"),
            aliases=character_data.get("aliases", []),
            gender=character_data.get("gender"),
            age_range=character_data.get("age_range"),
            role_type=character_data.get("role_type"),
            actor_name=character_data.get("actor_name"),
            description=character_data.get("description"),
            personality=character_data.get("personality"),
            speech_pattern=character_data.get("speech_pattern"),
            relationships=character_data.get("relationships", {}),
            first_appearance_season=character_data.get("first_appearance_season"),
            first_appearance_episode=character_data.get("first_appearance_episode"),
            first_appearance_timestamp=character_data.get("first_appearance_timestamp"),
            is_active=character_data.get("is_active", True),
        )

        self.db.add(character)
        await self.db.commit()
        await self.db.refresh(character)

        logger.info(f"Created character: {character.name}")
        return character

    async def save_voice_profile(
        self,
        project_id: str,
        character_id: str,
        voice_data: Dict[str, Any],
    ) -> VoiceProfile:
        """
        保存音色档案到 orchestrator 数据库

        Args:
            project_id: 项目 ID
            character_id: 人物 ID
            voice_data: 音色数据（来自 voice_synthesis/speaker_mapping worker）

        Returns:
            保存的 VoiceProfile 对象
        """
        # 获取真实的 project UUID
        project_uuid = await self._get_or_create_project(project_id)

        # 检查是否已存在该人物的音色档案
        existing = await self.get_voice_profile_by_character(character_id)

        if existing:
            # 更新现有记录
            existing.name = voice_data.get("name", f"Voice-{character_id[:8]}")
            existing.version = voice_data.get("version", "v1.0")
            existing.tts_model = voice_data.get("tts_model")
            existing.tts_model_version = voice_data.get("tts_model_version")
            existing.tts_config = voice_data.get("tts_config", {})
            existing.pitch_range = voice_data.get("pitch_range")
            existing.speed_range = voice_data.get("speed_range")
            existing.emotional_range = voice_data.get("emotional_range", [])
            existing.is_validated = voice_data.get("is_validated", False)
            existing.updated_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(existing)

            logger.info(f"Updated voice profile for character: {character_id}")
            return existing

        # 创建新记录
        voice_profile = VoiceProfile(
            character_id=uuid.UUID(character_id),
            project_id=project_uuid,
            name=voice_data.get("name", f"Voice-{character_id[:8]}"),
            version=voice_data.get("version", "v1.0"),
            tts_model=voice_data.get("tts_model"),
            tts_model_version=voice_data.get("tts_model_version"),
            tts_config=voice_data.get("tts_config", {}),
            pitch_range=voice_data.get("pitch_range"),
            speed_range=voice_data.get("speed_range"),
            emotional_range=voice_data.get("emotional_range", []),
            is_validated=voice_data.get("is_validated", False),
        )

        self.db.add(voice_profile)
        await self.db.commit()
        await self.db.refresh(voice_profile)

        logger.info(f"Created voice profile for character: {character_id}")
        return voice_profile

    async def get_character_by_name(
        self,
        project_id: uuid.UUID,
        name: str,
    ) -> Optional[Character]:
        """
        根据名称查询人物（跨集复用）

        Args:
            project_id: 项目 UUID
            name: 人物名称

        Returns:
            Character 对象或 None
        """
        project_uuid = await self._resolve_project_uuid(project_id)
        result = await self.db.execute(
            select(Character).where(
                Character.project_id == project_uuid,
                Character.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def get_character_by_id(
        self,
        character_id: str,
    ) -> Optional[Character]:
        """
        根据 ID 查询人物

        Args:
            character_id: 人物 ID

        Returns:
            Character 对象或 None
        """
        result = await self.db.execute(
            select(Character).where(Character.id == uuid.UUID(character_id))
        )
        return result.scalar_one_or_none()

    async def get_voice_profile_by_character(
        self,
        character_id: str,
    ) -> Optional[VoiceProfile]:
        """
        根据人物 ID 查询音色档案（跨集复用）

        Args:
            character_id: 人物 ID

        Returns:
            VoiceProfile 对象或 None
        """
        result = await self.db.execute(
            select(VoiceProfile).where(
                VoiceProfile.character_id == uuid.UUID(character_id),
                VoiceProfile.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def list_project_characters(
        self,
        project_id: str,
    ) -> List[Character]:
        """
        列出项目的所有人物

        Args:
            project_id: 项目 ID（字符串）

        Returns:
            Character 列表
        """
        project_uuid = await self._resolve_project_uuid(project_id)
        result = await self.db.execute(
            select(Character).where(
                Character.project_id == project_uuid,
                Character.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def list_project_voice_profiles(
        self,
        project_id: str,
    ) -> List[VoiceProfile]:
        """
        列出项目的所有音色档案

        Args:
            project_id: 项目 ID（字符串）

        Returns:
            VoiceProfile 列表
        """
        project_uuid = await self._resolve_project_uuid(project_id)
        result = await self.db.execute(
            select(VoiceProfile).where(
                VoiceProfile.project_id == project_uuid,
                VoiceProfile.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def save_audio_analysis(
        self,
        project_id: str,
        analysis_data: Dict[str, Any],
    ) -> str:
        """
        保存音频分析结果到 audio_analysis 表（M05 产出落库，ticket-032）

        Args:
            project_id: 项目 ID
            analysis_data: 音频分析数据（media_file/analysis_type/payload）

        Returns:
            保存的 AudioAnalysis 记录 ID
        """
        from filmdub.orchestrator.models import AudioAnalysis

        project_uuid = await self._get_or_create_project(project_id)
        analysis = AudioAnalysis(
            project_id=project_uuid,
            media_file=analysis_data.get("media_file"),
            analysis_type=analysis_data.get("analysis_type", "speaker_segment"),
            payload=analysis_data.get("payload") or analysis_data,
        )
        self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)
        logger.info(f"Audio analysis saved for project: {project_id} (id={analysis.id})")
        return str(analysis.id)
