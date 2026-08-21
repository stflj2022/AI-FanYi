"""
韵律规划器

为对白规划韵律参数（语速、音高、音量、停顿、重音）
"""
import re
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

from .models import ProsodyParams, PreparedDialogue
from .config import M08Config


class ProsodyPlanner:
    """韵律规划器"""

    def __init__(self, config: M08Config = None):
        """
        初始化规划器

        Args:
            config: M08 配置
        """
        self.config = config or M08Config()

        # 情绪到韵律的映射
        self._init_emotion_mappings()

    def _init_emotion_mappings(self):
        """初始化情绪映射"""
        self.emotion_mappings = {
            "happy": {
                "speed": 1.2,
                "pitch": 1.1,
                "volume": 1.1,
                "emotion": "happy"
            },
            "sad": {
                "speed": 0.8,
                "pitch": 0.9,
                "volume": 0.9,
                "emotion": "sad"
            },
            "angry": {
                "speed": 1.3,
                "pitch": 1.2,
                "volume": 1.3,
                "emotion": "angry"
            },
            "excited": {
                "speed": 1.4,
                "pitch": 1.15,
                "volume": 1.2,
                "emotion": "excited"
            },
            "calm": {
                "speed": 0.9,
                "pitch": 0.95,
                "volume": 0.95,
                "emotion": "calm"
            },
            "surprised": {
                "speed": 1.1,
                "pitch": 1.3,
                "volume": 1.1,
                "emotion": "surprised"
            },
            "fearful": {
                "speed": 1.0,
                "pitch": 1.1,
                "volume": 0.8,
                "emotion": "fearful"
            },
            "neutral": {
                "speed": 1.0,
                "pitch": 1.0,
                "volume": 1.0,
                "emotion": "neutral"
            }
        }

    async def plan_dialogues(
        self,
        dialogues: List[Dict[str, Any]],
        voice_profiles: List[Dict[str, Any]],
        audio_features: Optional[Dict[str, Any]] = None
    ) -> List[PreparedDialogue]:
        """
        为对白列表规划韵律

        Args:
            dialogues: 对白列表
            voice_profiles: 音色配置列表
            audio_features: 音频特征（可选）

        Returns:
            准备好的对白列表
        """
        logger.info(f"Planning prosody for {len(dialogues)} dialogues")

        prepared_dialogues = []

        for dialogue in dialogues:
            prepared = await self.plan_dialogue(
                dialogue,
                voice_profiles,
                audio_features
            )

            if prepared:
                prepared_dialogues.append(prepared)

        logger.info(f"Planned prosody for {len(prepared_dialogues)} dialogues")

        return prepared_dialogues

    async def plan_dialogue(
        self,
        dialogue: Dict[str, Any],
        voice_profiles: List[Dict[str, Any]],
        audio_features: Optional[Dict[str, Any]] = None
    ) -> Optional[PreparedDialogue]:
        """
        为单个对白规划韵律

        Args:
            dialogue: 对白数据
            voice_profiles: 音色配置列表
            audio_features: 音频特征

        Returns:
            准备好的对白或 None
        """
        text = dialogue.get("text", "")
        character_id = dialogue.get("character_id")
        speaker_id = dialogue.get("speaker_id")
        voice_profile_id = dialogue.get("voice_profile_id")

        if not text or not voice_profile_id:
            return None

        # 查找音色配置
        voice_profile = next(
            (vp for vp in voice_profiles if vp["voice_profile_id"] == voice_profile_id),
            None
        )

        if not voice_profile:
            logger.warning(f"Voice profile {voice_profile_id} not found")
            return None

        # 计算目标时长
        start_time = dialogue.get("start_time", 0.0)
        end_time = dialogue.get("end_time", 0.0)
        original_duration = end_time - start_time

        # 规划韵律
        prosody = await self._plan_prosody_params(
            dialogue,
            voice_profile,
            audio_features,
            original_duration
        )

        # 计算置信度
        confidence = self._calculate_confidence(prosody)

        return PreparedDialogue(
            dialogue_id=dialogue.get("dialogue_id", ""),
            text=text,
            character_id=character_id,
            speaker_id=speaker_id,
            voice_profile_id=voice_profile_id,
            start_time=start_time,
            end_time=end_time,
            target_duration=original_duration,
            prosody=prosody,
            confidence=confidence
        )

    async def _plan_prosody_params(
        self,
        dialogue: Dict[str, Any],
        voice_profile: Dict[str, Any],
        audio_features: Optional[Dict[str, Any]],
        original_duration: float
    ) -> ProsodyParams:
        """
        规划韵律参数

        Args:
            dialogue: 对白数据
            voice_profile: 音色配置
            audio_features: 音频特征
            original_duration: 原始时长

        Returns:
            韵律参数
        """
        text = dialogue.get("text", "")

        # 1. 基于情绪的韵律
        emotion = dialogue.get("emotion", voice_profile.get("emotion", "neutral"))
        emotion_prosody = self.emotion_mappings.get(emotion, self.emotion_mappings["neutral"])

        # 2. 计算语速
        speed = await self._calculate_speed(
            text,
            original_duration,
            emotion_prosody["speed"]
        )

        # 3. 计算音高
        pitch = await self._calculate_pitch(
            voice_profile,
            audio_features,
            emotion_prosody["pitch"]
        )

        # 4. 计算音量
        volume = await self._calculate_volume(
            voice_profile,
            audio_features,
            emotion_prosody["volume"]
        )

        # 5. 计算停顿
        pauses = self._calculate_pauses(text)

        # 6. 计算重音
        stresses = self._calculate_stresses(text)

        return ProsodyParams(
            speed=speed,
            pitch=pitch,
            volume=volume,
            emotion=emotion,
            pauses=pauses,
            stresses=stresses
        )

    async def _calculate_speed(
        self,
        text: str,
        original_duration: float,
        emotion_factor: float
    ) -> float:
        """
        计算语速

        Args:
            text: 文本
            original_duration: 原始时长
            emotion_factor: 情绪因子

        Returns:
            语速 (0.5-2.0)
        """
        # 计算字符数（中文）
        char_count = len(text)

        if original_duration > 0:
            # 原始语速（字符/秒）
            original_speed = char_count / original_duration

            # 标准语速约为 4-6 字符/秒
            target_speed = 5.0

            # 调整因子
            speed_factor = target_speed / original_speed if original_speed > 0 else 1.0

            # 应用情绪因子
            speed_factor *= emotion_factor

            # 限制范围
            speed = max(
                self.config.speed_min,
                min(self.config.speed_max, speed_factor)
            )

            return speed

        return 1.0 * emotion_factor

    async def _calculate_pitch(
        self,
        voice_profile: Dict[str, Any],
        audio_features: Optional[Dict[str, Any]],
        emotion_factor: float
    ) -> float:
        """
        计算音高

        Args:
            voice_profile: 音色配置
            audio_features: 音频特征
            emotion_factor: 情绪因子

        Returns:
            音高因子 (0.5-2.0)
        """
        # 基于音色配置的基准音高
        base_pitch = voice_profile.get("pitch", 1.0)

        # 基于音频特征微调（真实特征：实际基频相对 180Hz 参考的偏差）
        if audio_features:
            pitch_mean = audio_features.get("pitch_mean", 0.0)
            if pitch_mean > 0:
                # 参考中性基频 180Hz；与基准音高的偏离按比例修正（±20% 上限）
                target_adjust = pitch_mean / 180.0
                # 基准音高本身已包含角色性别/年龄段信息，此处只做小幅修正
                base_pitch *= min(1.2, max(0.8, target_adjust))

        # 应用情绪因子
        pitch = base_pitch * emotion_factor

        # 限制范围
        pitch = max(
            self.config.pitch_min,
            min(self.config.pitch_max, pitch)
        )

        return pitch

    async def _calculate_volume(
        self,
        voice_profile: Dict[str, Any],
        audio_features: Optional[Dict[str, Any]],
        emotion_factor: float
    ) -> float:
        """
        计算音量

        Args:
            voice_profile: 音色配置
            audio_features: 音频特征
            emotion_factor: 情绪因子

        Returns:
            音量因子 (0.5-1.5)
        """
        # 基于音色配置的基准音量
        base_volume = voice_profile.get("volume", 1.0)

        # 基于音频特征微调（真实特征：RMS 幅度整体偏大时降低音量避免削波）
        if audio_features:
            rms = audio_features.get("rms", 0.0)
            if rms > 0:
                # 0.5 RMS 视为中性；更响 → 音量略降，更轻 → 音量略升（±20% 上限）
                loudness_adjust = 0.5 / max(rms, 0.05)
                base_volume *= min(1.2, max(0.8, loudness_adjust))

        # 应用情绪因子
        volume = base_volume * emotion_factor

        # 限制范围
        volume = max(
            self.config.volume_min,
            min(self.config.volume_max, volume)
        )

        return volume

    def _calculate_pauses(self, text: str) -> List[int]:
        """
        计算停顿位置

        Args:
            text: 文本

        Returns:
            停顿位置列表（字符索引）
        """
        pauses = []

        # 句末标点
        sentence_endings = r"[。！？]"
        for match in re.finditer(sentence_endings, text):
            pauses.append(match.end())

        # 分句标点
        clause_separators = r"[，；：]"
        for match in re.finditer(clause_separators, text):
            pauses.append(match.end())

        # 按阅读顺序排序（TTS 需要时间有序的停顿位置）
        pauses.sort()

        return pauses

    def _calculate_stresses(self, text: str) -> List[int]:
        """
        计算重音位置

        Args:
            text: 文本

        Returns:
            重音位置列表（字符索引）
        """
        stresses = []

        # 简化版：强调关键词
        keywords = ["不", "很", "最", "非常", "特别", "一定"]

        for keyword in keywords:
            index = text.find(keyword)
            if index != -1:
                # 强调关键词后的字符
                stress_pos = index + len(keyword)
                if stress_pos < len(text):
                    stresses.append(stress_pos)

        return stresses

    def _calculate_confidence(self, prosody: ProsodyParams) -> float:
        """
        计算置信度

        Args:
            prosody: 韵律参数

        Returns:
            置信度 (0.0-1.0)
        """
        # 基于参数的合理性计算置信度
        confidence = 1.0

        # 检查参数是否在合理范围内
        if not (self.config.speed_min <= prosody.speed <= self.config.speed_max):
            confidence *= 0.8

        if not (self.config.pitch_min <= prosody.pitch <= self.config.pitch_max):
            confidence *= 0.8

        if not (self.config.volume_min <= prosody.volume <= self.config.volume_max):
            confidence *= 0.8

        # 停顿数量异常（>40 个）时降置信度
        if prosody.pauses and len(prosody.pauses) > 40:
            confidence *= 0.9

        return max(0.0, min(1.0, confidence))
