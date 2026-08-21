"""
M08 数据模型
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class Emotion(Enum):
    """情绪类型"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"


@dataclass
class ProsodyParams:
    """韵律参数"""
    # 语速 (0.5-2.0, 1.0 为正常)
    speed: float = 1.0
    speed_variance: float = 0.1

    # 音高偏移 (st, -24 to +24)
    pitch: float = 0.0
    pitch_variance: float = 2.0

    # 停顿 (秒)
    pause_before: float = 0.0
    pause_after: float = 0.0
    pause_internal: List[float] = None

    # 能量/音量 (0.0-1.0)
    energy: float = 1.0
    energy_variance: float = 0.1

    # 情绪
    emotion: Emotion = Emotion.NEUTRAL
    emotion_intensity: float = 0.5

    def __post_init__(self):
        """初始化后处理"""
        if self.pause_internal is None:
            self.pause_internal = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "speed": self.speed,
            "speed_variance": self.speed_variance,
            "pitch": self.pitch,
            "pitch_variance": self.pitch_variance,
            "pause_before": self.pause_before,
            "pause_after": self.pause_after,
            "pause_internal": self.pause_internal,
            "energy": self.energy,
            "energy_variance": self.energy_variance,
            "emotion": self.emotion.value,
            "emotion_intensity": self.emotion_intensity
        }


@dataclass
class PreparedDialogue:
    """准备好的对白"""
    dialogue_id: str
    character_id: str
    text: str
    start_time: float
    end_time: float

    # 韵律参数
    prosody: ProsodyParams

    # 元数据
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "dialogue_id": self.dialogue_id,
            "character_id": self.character_id,
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "prosody": self.prosody.to_dict(),
            "metadata": self.metadata
        }
