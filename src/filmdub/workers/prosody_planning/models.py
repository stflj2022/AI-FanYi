"""
M08 数据模型
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class ProsodyParams:
    """韵律参数"""
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    emotion: str = "neutral"

    # 停顿位置（相对于文本的字符索引）
    pauses: List[int] = None

    # 重音位置
    stresses: List[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "speed": self.speed,
            "pitch": self.pitch,
            "volume": self.volume,
            "emotion": self.emotion,
            "pauses": self.pauses or [],
            "stresses": self.stresses or []
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProsodyParams':
        """从字典创建"""
        return cls(
            speed=data.get("speed", 1.0),
            pitch=data.get("pitch", 1.0),
            volume=data.get("volume", 1.0),
            emotion=data.get("emotion", "neutral"),
            pauses=data.get("pauses", []),
            stresses=data.get("stresses", [])
        )


@dataclass
class PreparedDialogue:
    """准备好的对白（带韵律参数）"""
    dialogue_id: str
    text: str
    character_id: str
    speaker_id: str
    voice_profile_id: str

    # 时间信息
    start_time: float
    end_time: float
    target_duration: float

    # 韵律参数
    prosody: ProsodyParams

    # 元数据
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "dialogue_id": self.dialogue_id,
            "text": self.text,
            "character_id": self.character_id,
            "speaker_id": self.speaker_id,
            "voice_profile_id": self.voice_profile_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "target_duration": self.target_duration,
            "prosody": self.prosody.to_dict(),
            "confidence": self.confidence
        }
