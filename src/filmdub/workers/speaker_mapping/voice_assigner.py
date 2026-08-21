"""
音色分配器

为人物分配合适的 Voice Profile
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

import numpy as np

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

            # 为剩余映射创建变体：复制参数并在音高上做确定性微调
            base = char_voice_profiles[0]
            for mapping in mappings[1:]:
                variant_id = f"vp_{uuid.uuid4().hex[:8]}"
                # 基于 speaker_id 哈希做确定性微调，同一说话人跨集得到相同变体
                seed = sum(ord(c) for c in mapping.speaker_id)
                pitch_delta = ((seed % 5) - 2) * 0.02  # -4% ~ +4%
                variant = VoiceProfile(
                    voice_profile_id=variant_id,
                    character_id=character_id,
                    name=f"{base.name}_variant",
                    gender=base.gender,
                    age_range=base.age_range,
                    style=base.style,
                    emotion=base.emotion,
                    pitch=round(max(0.5, min(1.5, base.pitch + pitch_delta)), 3),
                    speed=base.speed,
                    volume=base.volume,
                    is_reference=False,
                    reference_audio_path=base.reference_audio_path,
                    created_at=datetime.utcnow().isoformat(),
                )
                mapping.voice_profile_id = variant_id
                voice_profiles.append(variant)

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
        分析音频特征（真实信号处理，基于 scipy/numpy）

        提取：
        - pitch_mean/pitch_std: 基频估计（自相关峰值法）
        - energy_mean/energy_std: 短时能量
        - rms: 均方根幅度
        - sample_rate

        Args:
            audio_path: 音频路径

        Returns:
            音频特征或 None（文件不可读时）
        """
        try:
            from scipy.io import wavfile

            sample_rate, data = wavfile.read(audio_path)

            # 转为 float 单声道
            if data.ndim == 2:
                data = np.mean(data, axis=1)
            audio = data.astype(np.float64) / (np.iinfo(data.dtype).max if np.issubdtype(data.dtype, np.integer) else 1.0)

            if len(audio) < sample_rate * 0.05:
                logger.warning(f"Audio too short for feature analysis: {audio_path}")
                return None

            # 短时能量
            frame_length = 1024
            hop_length = 512
            frames = [
                audio[i:i + frame_length]
                for i in range(0, len(audio) - frame_length, hop_length)
            ]
            energies = np.array([np.sum(f ** 2) for f in frames]) if frames else np.array([0.0])

            # 基频估计：对每帧用自相关法估计 F0，取带通 60-400Hz 的 voiced 帧
            pitch_estimates = []
            for frame in frames:
                frame = frame - np.mean(frame)
                if np.std(frame) < 1e-6:
                    continue
                corr = np.correlate(frame, frame, mode="full")[len(frame) - 1:]
                min_lag = int(sample_rate / 400)
                max_lag = int(sample_rate / 60)
                if len(corr) <= max_lag:
                    continue
                lag_region = corr[min_lag:max_lag]
                if len(lag_region) == 0:
                    continue
                peak_lag = min_lag + int(np.argmax(lag_region))
                if peak_lag > 0 and corr[peak_lag] > 0:
                    f0 = sample_rate / peak_lag
                    if 60.0 <= f0 <= 400.0:
                        pitch_estimates.append(f0)

            if pitch_estimates:
                pitch_mean = float(np.mean(pitch_estimates))
                pitch_std = float(np.std(pitch_estimates))
            else:
                pitch_mean = 0.0
                pitch_std = 0.0

            features = {
                "pitch_mean": pitch_mean,
                "pitch_std": pitch_std,
                "energy_mean": float(np.mean(energies)),
                "energy_std": float(np.std(energies)),
                "rms": float(np.sqrt(np.mean(audio ** 2))),
                "sample_rate": int(sample_rate),
                "duration_seconds": float(len(audio) / sample_rate),
            }

            logger.debug(f"Analyzed audio {audio_path}: {features}")
            return features

        except Exception as e:
            logger.warning(f"Failed to analyze audio {audio_path}: {e}")
            return None

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

        # 基于音频特征微调（真实特征：用基频与能量微调音高/音量）
        if audio_features:
            pitch_mean = audio_features.get("pitch_mean", 0.0)
            if pitch_mean > 0:
                # 参考中性基频 180Hz：低音（<180）音高下调，高音（>180）音高上调
                pitch_adjust = pitch_mean / 180.0
                params["pitch"] *= min(1.3, max(0.7, pitch_adjust))

            rms = audio_features.get("rms", 0.0)
            if rms > 0:
                # 音量整体偏大/偏小时微调 volume
                params["volume"] *= min(1.2, max(0.8, 0.8 + rms))

        # 确保参数在合理范围内
        params["pitch"] = max(0.5, min(1.5, params["pitch"]))
        params["speed"] = max(0.5, min(1.5, params["speed"]))
        params["volume"] = max(0.5, min(1.5, params["volume"]))

        return params
