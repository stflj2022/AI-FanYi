"""
韵律规划器

为对白规划韵律参数
"""
import numpy as np
from typing import List, Dict, Any, Optional
from loguru import logger

from .models import ProsodyParams, PreparedDialogue, Emotion
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

        # 情绪到韵律参数的映射
        self.emotion_params = {
            Emotion.HAPPY: {
                "pitch_offset": 4.0,
                "speed_factor": 1.1,
                "energy_boost": 0.2
            },
            Emotion.SAD: {
                "pitch_offset": -4.0,
                "speed_factor": 0.9,
                "energy_boost": -0.2
            },
            Emotion.ANGRY: {
                "pitch_offset": 6.0,
                "speed_factor": 1.2,
                "energy_boost": 0.3
            },
            Emotion.SURPRISED: {
                "pitch_offset": 8.0,
                "speed_factor": 1.1,
                "energy_boost": 0.2
            },
            Emotion.FEARFUL: {
                "pitch_offset": 3.0,
                "speed_factor": 1.15,
                "energy_boost": 0.1
            },
            Emotion.DISGUSTED: {
                "pitch_offset": -2.0,
                "speed_factor": 0.95,
                "energy_boost": -0.1
            },
            Emotion.NEUTRAL: {
                "pitch_offset": 0.0,
                "speed_factor": 1.0,
                "energy_boost": 0.0
            }
        }

    def plan_prosody(
        self,
        dialogues: List[Dict[str, Any]],
        characters: List[Dict[str, Any]],
        audio_features: Optional[List[Dict[str, Any]]] = None
    ) -> List[PreparedDialogue]:
        """
        规划韵律

        Args:
            dialogues: 对白列表
            characters: 人物列表
            audio_features: 音频特征（可选）

        Returns:
            准备好的对白列表
        """
        logger.info(f"Planning prosody for {len(dialogues)} dialogues")

        prepared_dialogues = []

        for i, dialogue in enumerate(dialogues):
            try:
                # 获取人物信息
                character = self._get_character(
                    dialogue.get("character_id"),
                    characters
                )

                # 获取音频特征
                audio_feature = None
                if audio_features:
                    audio_feature = self._get_audio_feature(
                        dialogue.get("dialogue_id"),
                        audio_features
                    )

                # 规划韵律参数
                prosody = self._calculate_prosody(
                    dialogue,
                    character,
                    audio_feature
                )

                # 创建准备好的对白
                prepared_dialogue = PreparedDialogue(
                    dialogue_id=dialogue.get("dialogue_id", f"d_{i}"),
                    character_id=dialogue.get("character_id"),
                    text=dialogue.get("text"),
                    start_time=dialogue.get("start_time", 0.0),
                    end_time=dialogue.get("end_time", 0.0),
                    prosody=prosody,
                    metadata=dialogue.get("metadata")
                )

                prepared_dialogues.append(prepared_dialogue)

            except Exception as e:
                logger.warning(f"Failed to plan prosody for dialogue {i}: {e}")
                # 使用默认韵律参数
                default_prosody = ProsodyParams()
                prepared_dialogues.append(
                    PreparedDialogue(
                        dialogue_id=dialogue.get("dialogue_id", f"d_{i}"),
                        character_id=dialogue.get("character_id"),
                        text=dialogue.get("text"),
                        start_time=dialogue.get("start_time", 0.0),
                        end_time=dialogue.get("end_time", 0.0),
                        prosody=default_prosody
                    )
                )

        logger.info(f"Planned prosody for {len(prepared_dialogues)} dialogues")

        return prepared_dialogues

    def _get_character(
        self,
        character_id: str,
        characters: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """获取人物信息"""
        for character in characters:
            if character.get("character_id") == character_id:
                return character
        return None

    def _get_audio_feature(
        self,
        dialogue_id: str,
        audio_features: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """获取音频特征"""
        # 简化版：按顺序匹配
        # 实际实现应该使用 dialogue_id 匹配
        return None

    def _calculate_prosody(
        self,
        dialogue: Dict[str, Any],
        character: Optional[Dict[str, Any]],
        audio_feature: Optional[Dict[str, Any]]
    ) -> ProsodyParams:
        """
        计算韵律参数

        Args:
            dialogue: 对白
            character: 人物
            audio_feature: 音频特征

        Returns:
            韵律参数
        """
        prosody = ProsodyParams()

        # 1. 计算语速
        speed = self._calculate_speed(dialogue, character, audio_feature)
        prosody.speed = speed
        prosody.speed_variance = np.random.uniform(-0.05, 0.05)

        # 2. 计算音高
        pitch = self._calculate_pitch(dialogue, character, audio_feature)
        prosody.pitch = pitch
        prosody.pitch_variance = np.random.uniform(-1.0, 1.0)

        # 3. 计算停顿
        pause_before, pause_after = self._calculate_pauses(dialogue, character)
        prosody.pause_before = pause_before
        prosody.pause_after = pause_after

        # 4. 计算能量
        energy = self._calculate_energy(dialogue, character, audio_feature)
        prosody.energy = energy
        prosody.energy_variance = np.random.uniform(-0.05, 0.05)

        # 5. 调整情绪
        prosody = self._adjust_emotion(prosody, dialogue, character)

        return prosody

    def _calculate_speed(
        self,
        dialogue: Dict[str, Any],
        character: Optional[Dict[str, Any]],
        audio_feature: Optional[Dict[str, Any]]
    ) -> float:
        """计算语速"""
        base_speed = 1.0

        # 根据文本长度调整
        text = dialogue.get("text", "")
        text_length = len(text)

        if text_length < 20:
            speed_factor = 0.9  # 短句子稍慢
        elif text_length < 50:
            speed_factor = 1.0  # 中等长度正常
        else:
            speed_factor = 1.1  # 长句子稍快

        # 根据音频特征调整
        if audio_feature:
            # TODO: 使用音频特征调整语速
            pass

        speed = base_speed * speed_factor
        return max(self.config.min_speed, min(self.config.max_speed, speed))

    def _calculate_pitch(
        self,
        dialogue: Dict[str, Any],
        character: Optional[Dict[str, Any]],
        audio_feature: Optional[Dict[str, Any]]
    ) -> float:
        """计算音高偏移"""
        base_pitch = 0.0

        # 根据人物性别调整
        gender = character.get("gender", "unknown") if character else "unknown"
        if gender == "male":
            base_pitch = -2.0
        elif gender == "female":
            base_pitch = 2.0

        # 根据音频特征调整
        if audio_feature:
            # TODO: 使用音频特征调整音高
            pass

        # 限制范围
        return max(self.config.min_pitch, min(self.config.max_pitch, base_pitch))

    def _calculate_pauses(
        self,
        dialogue: Dict[str, Any],
        character: Optional[Dict[str, Any]]
    ) -> tuple[float, float]:
        """计算停顿"""
        text = dialogue.get("text", "")

        # 句号/问号/感叹号后停顿
        if text.strip().endswith(('.', '。')):
            pause_after = np.random.uniform(0.3, 0.6)
        elif text.strip().endswith(('?', '？', '!', '！')):
            pause_after = np.random.uniform(0.2, 0.4)
        else:
            pause_after = np.random.uniform(0.0, 0.2)

        # 句前停顿
        pause_before = np.random.uniform(0.0, 0.2)

        # 限制范围
        pause_before = max(self.config.min_pause, min(self.config.max_pause, pause_before))
        pause_after = max(self.config.min_pause, min(self.config.max_pause, pause_after))

        return pause_before, pause_after

    def _calculate_energy(
        self,
        dialogue: Dict[str, Any],
        character: Optional[Dict[str, Any]],
        audio_feature: Optional[Dict[str, Any]]
    ) -> float:
        """计算能量"""
        base_energy = 1.0

        # 根据文本调整
        text = dialogue.get("text", "")
        if any(char in text for char in ('！', '!', '！')):
            base_energy += 0.2
        elif any(char in text for char in ('？', '?')):
            base_energy += 0.1

        # 限制范围
        return max(0.0, min(1.0, base_energy))

    def _adjust_emotion(
        self,
        prosody: ProsodyParams,
        dialogue: Dict[str, Any],
        character: Optional[Dict[str, Any]]
    ) -> ProsodyParams:
        """
        调整情绪

        Args:
            prosody: 韵律参数
            dialogue: 对白
            character: 人物

        Returns:
            调整后的韵律参数
        """
        # 获取情绪（简化版：从对白中推断）
        emotion = self._infer_emotion(dialogue, character)
        intensity = 0.5  # 默认强度

        # 获取情绪参数
        emotion_params = self.emotion_params.get(emotion, self.emotion_params[Emotion.NEUTRAL])

        # 应用情绪参数
        prosody.pitch += emotion_params["pitch_offset"] * intensity * self.config.emotion_pitch_weight
        prosody.speed *= 1.0 + (emotion_params["speed_factor"] - 1.0) * intensity * self.config.emotion_speed_weight
        prosody.energy += emotion_params["energy_boost"] * intensity * self.config.emotion_pause_weight

        # 限制范围
        prosody.pitch = max(self.config.min_pitch, min(self.config.max_pitch, prosody.pitch))
        prosody.speed = max(self.config.min_speed, min(self.config.max_speed, prosody.speed))
        prosody.energy = max(0.0, min(1.0, prosody.energy))

        prosody.emotion = emotion
        prosody.emotion_intensity = intensity

        return prosody

    def _infer_emotion(
        self,
        dialogue: Dict[str, Any],
        character: Optional[Dict[str, Any]]
    ) -> Emotion:
        """
        推断情绪

        Args:
            dialogue: 对白
            character: 人物

        Returns:
            情绪
        """
        text = dialogue.get("text", "")

        # 简化版：基于关键词推断
        if any(word in text for word in ("!", "！", "太好了", "真棒")):
            return Emotion.HAPPY
        elif any(word in text for word in ("难过", "悲伤", "对不起")):
            return Emotion.SAD
        elif any(word in text for word in ("！!", "该死", "混蛋")):
            return Emotion.ANGRY
        elif any(word in text for word in ("!", "什么", "真的")):
            return Emotion.SURPRISED
        else:
            return Emotion.NEUTRAL
