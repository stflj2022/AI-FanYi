"""
音色分配器

为人物分配或创建 Voice Profile
"""
from typing import List, Optional, Dict, Any
from loguru import logger

from .models import VoiceProfileAssignment, MappingResult
from .config import M06Config


class VoiceProfileAssigner:
    """音色分配器"""

    def __init__(self, config: M06Config = None):
        """
        初始化分配器

        Args:
            config: M06 配置
        """
        self.config = config or M06Config()

    def assign_voice_profiles(
        self,
        mapping_result: MappingResult,
        existing_profiles: Optional[List[Dict[str, Any]]] = None
    ) -> List[VoiceProfileAssignment]:
        """
        为人物分配音色

        Args:
            mapping_result: 映射结果
            existing_profiles: 已有音色档案

        Returns:
            音色分配列表
        """
        logger.info(f"Assigning voice profiles for {len(mapping_result.mappings)} characters")

        assignments = []

        for mapping in mapping_result.mappings:
            if mapping.status == "failed":
                continue

            character_id = mapping.character_id

            # 查找现有档案
            existing_profile = None
            if existing_profiles:
                existing_profile = self._find_existing_profile(
                    character_id,
                    existing_profiles
                )

            if existing_profile and self.config.reuse_profiles:
                # 复用现有档案
                assignment = self._reuse_voice_profile(
                    character_id,
                    existing_profile,
                    mapping
                )
            elif self.config.auto_create_profiles:
                # 创建新档案
                assignment = self._create_voice_profile(
                    character_id,
                    mapping
                )
            else:
                logger.warning(f"No voice profile for character {character_id}")
                continue

            assignments.append(assignment)

        # 更新映射结果
        mapping_result.voice_assignments = assignments

        logger.info(
            f"Voice profiles assigned: {sum(1 for a in assignments if a.is_new)} new, "
            f"{sum(1 for a in assignments if not a.is_new)} reused"
        )

        return assignments

    def _find_existing_profile(
        self,
        character_id: str,
        existing_profiles: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        查找现有档案

        Args:
            character_id: 人物 ID
            existing_profiles: 现有档案列表

        Returns:
            档案或 None
        """
        for profile in existing_profiles:
            if profile["character_id"] == character_id:
                return profile

        return None

    def _reuse_voice_profile(
        self,
        character_id: str,
        profile: Dict[str, Any],
        mapping: Any
    ) -> VoiceProfileAssignment:
        """
        复用音色档案

        Args:
            character_id: 人物 ID
            profile: 现有档案
            mapping: 映射信息

        Returns:
            音色分配
        """
        logger.info(f"Reusing voice profile {profile['voice_profile_id']} for character {character_id}")

        return VoiceProfileAssignment(
            character_id=character_id,
            voice_profile_id=profile["voice_profile_id"],
            is_new=False,
            confidence=mapping.confidence,
            metadata={
                "reused_from": profile.get("created_at"),
                "original_similarity": mapping.similarity
            }
        )

    def _create_voice_profile(
        self,
        character_id: str,
        mapping: Any
    ) -> VoiceProfileAssignment:
        """
        创建音色档案

        Args:
            character_id: 人物 ID
            mapping: 映射信息

        Returns:
            音色分配
        """
        # 生成新的音色档案 ID
        voice_profile_id = f"vp_{character_id}_{mapping.speaker_id}"

        logger.info(f"Creating new voice profile {voice_profile_id} for character {character_id}")

        # TODO: 实际创建档案到数据库
        # 这里应该调用 Voice Profile 服务

        return VoiceProfileAssignment(
            character_id=character_id,
            voice_profile_id=voice_profile_id,
            is_new=True,
            confidence=mapping.confidence,
            metadata={
                "created_from_mapping": True,
                "speaker_id": mapping.speaker_id,
                "similarity": mapping.similarity
            }
        )
