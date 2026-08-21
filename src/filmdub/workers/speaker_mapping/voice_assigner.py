"""
音色分配器

为人物分配合适的 Voice Profile
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

from .models import VoiceProfile, SpeakerToCharacterMapping
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

    async def assign_voice_profiles(
        self,
        mappings: List[SpeakerToCharacterMapping],
        characters: List[Dict[str, Any]],
        existing_voice_profiles: Optional[List[VoiceProfile]] = None,
        audio_paths: Optional[Dict[str, str]] = None
    ) -> List[VoiceProfile]:
        """
        为映射分配音色

        Args:
            mappings: 说话人到人物映射
            characters: 人物列表
            existing_voice_profiles: 已有音色列表
            audio_paths: 说话人音频路径字典

        Returns:
            音色配置列表
        """
        logger.info(f"Assigning voice profiles for {len(mappings)} mappings")

        voice_profiles = []
        existing_voice_profiles = existing_voice_profiles or []

        # 按人物分组映射
        mappings_by_character: Dict[str, List[SpeakerToCharacterMapping]] = {}
        for mapping in mappings:
            char_id = mapping.character_id
            if char_id not in mappings_by_character:
                mappings_by_character[char_id] = []
            mappings_by_character[char_id].append(mapping)

        # 为每个人物分配音色
        for char_id, char_mappings in mappings_by_character.items():
            # 查找人物信息
            character = next(
                (c for c in characters if c["character_id"] == char_id),
                None
            )

            if not character:
                logger.warning(f"Character {char_id} not found")
                continue

            # 检查是否可以复用已有音色
            if self.config.reuse_voice_profiles and existing_voice_profiles:
                reused = self._reuse_voice_profile(
                    char_id,
                    character,
                    existing_voice_profiles,
                    char_mappings,
                    voice_profiles
                )

                if reused:
                    continue

            # 为每个映射创建新音色
            for mapping in char_mappings:
                voice_profile = await self._create_voice_profile(
                    mapping,
                    character,
                    audio_paths
                )

                if voice_profile:
                    voice_profiles.append(voice_profile)

        logger.info(f"Created {len(voice_profiles)} voice profiles")

        return voice_profiles

    def _reuse_voice_profile(
        self,
        character_id: str,
        character: Dict[str, Any],
        existing_voice_profiles: List[VoiceProfile],
        mappings: List[SpeakerToCharacterMapping],
        voice_profiles: List[VoiceProfile]
    ) -> bool:
        """
        复用已有音色

        Args:
            character_id: 人物 ID
            character: 人物信息
            existing_voice_profiles: 已有音色列表
            mappings: 映射列表
            voice_profiles: 新音色列表（输出）

        Returns:
            是否成功复用
        """
        # 查找该人物的已有音色
        char_voice_profiles = [
            vp for vp in existing_voice_profiles
            if vp.character_id == character_id
        ]

        if not char_voice_profiles:
            return False

        # 检查是否超过最大音色数
        if len(char_voice_profiles) >= self.config.max_voice_profiles_per_character:
            # 使用参考音色
            reference_vps = [vp for vp in char_voice_profiles if vp.is_reference]

            if reference_vps:
                # 为所有映射使用参考音色
                for mapping in mappings:
                    mapping.voice_profile_id = reference_vps[0].voice_profile_id

                voice_profiles.extend(reference_vps)
                return True

        # 否则，为第一个映射复用已有音色
        if mappings:
            mappings[0].voice_profile_id = char_voice_profiles[0].voice_profile_id
            voice_profiles.append(char_voice_profiles[0])

            # 为剩余映射创建新音色
            for mapping in mappings[1:]:
                # TODO: 基于已有音色创建变体
                pass

            return True

        return False

    async def _create_voice_profile(
        self,
        mapping: SpeakerToCharacterMapping,
        character: Dict[str, Any],
        audio_paths: Optional[Dict[str, str]] = None
    ) -> Optional[VoiceProfile]:
        """
        创建新音色配置

        Args:
            mapping: 映射
            character: 人物信息
            audio_paths: 音频路径字典

        Returns:
            音色配置或 None
        """
        # 生成音色 ID
        voice_profile_id = f"vp_{uuid.uuid4().hex[:8]}"

        # 获取参考音频路径
        reference_audio_path = None
        if audio_paths and mapping.speaker_id in audio_paths:
            reference_audio_path = audio_paths[mapping.speaker_id]

        # 分析音频特征
        audio_features = None
        if reference_audio_path:
            audio_features = await self._analyze_audio(reference_audio_path)

        # 基于人物信息和音频特征生成音色参数
        voice_params = self._generate_voice_parameters(
            character,
            audio_features
        )

        # 创建音色配置
        voice_profile = VoiceProfile(
            voice_profile_id=voice_profile_id,
            character_id=character["character_id"],
            name=f"{character['name']}_{voice_profile_id}",
            gender=character.get("gender", "unknown"),
            age_range=character.get("age_range", "unknown"),
            style=voice_params.get("style", "neutral"),
            emotion=voice_params.get("emotion", "neutral"),
            pitch=voice_params.get("pitch", 1.0),
            speed=voice_params.get("speed", 1.0),
            volume=voice_params.get("volume", 1.0),
            is_reference=True,
            reference_audio_path=reference_audio_path,
            created_at=datetime.utcnow().isoformat()
        )

        # 更新映射的音色 ID
        mapping.voice_profile_id = voice_profile_id

        logger.info(
            f"Created voice profile {voice_profile_id} "
            f"for character {character['name']}"
        )

        return voice_profile

    async def _analyze_audio(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """
        分析音频特征

        Args:
            audio_path: 音频路径

        Returns:
            音频特征或 None
        """
        # TODO: 实现音频特征分析
        # 这里应该：
        # 1. 加载音频
        # 2. 提取音高、能量等特征
        # 3. 返回特征字典

        return {
            "pitch_mean": 0.0,
            "pitch_std": 0.0,
            "energy_mean": 0.0,
            "energy_std": 0.0
        }

    def _generate_voice_parameters(
        self,
        character: Dict[str, Any],
        audio_features: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成音色参数

        Args:
            character: 人物信息
            audio_features: 音频特征

        Returns:
            音色参数字典
        """
        params = {
            "style": "neutral",
            "emotion": "neutral",
            "pitch": 1.0,
            "speed": 1.0,
            "volume": 1.0
        }

        # 基于角色类型调整
        role_type = character.get("role_type", "unknown")

        if role_type == "protagonist":
            params["style"] = "confident"
            params["pitch"] = 1.0
            params["volume"] = 1.1
        elif role_type == "antagonist":
            params["style"] = "aggressive"
            params["pitch"] = 0.95
            params["volume"] = 1.15
        elif role_type == "narrator":
            params["style"] = "neutral"
            params["speed"] = 0.95
            params["volume"] = 1.0
        elif role_type == "supporting":
            params["style"] = "friendly"
            params["pitch"] = 1.0
            params["volume"] = 1.0

        # 基于性别调整
        gender = character.get("gender", "unknown")

        if gender == "male":
            params["pitch"] *= 0.9  # 男性音调较低
        elif gender == "female":
            params["pitch"] *= 1.1  # 女性音调较高

        # 基于年龄段调整
        age_range = character.get("age_range", "")

        if "child" in age_range.lower() or "young" in age_range.lower():
            params["pitch"] *= 1.15
            params["speed"] *= 1.05
        elif "elderly" in age_range.lower() or "old" in age_range.lower():
            params["pitch"] *= 0.85
            params["speed"] *= 0.9

        # 基于音频特征微调
        if audio_features:
            # TODO: 基于实际音频特征调整
            pass

        # 确保参数在合理范围内
        params["pitch"] = max(0.5, min(1.5, params["pitch"]))
        params["speed"] = max(0.5, min(1.5, params["speed"]))
        params["volume"] = max(0.5, min(1.5, params["volume"]))

        return params
