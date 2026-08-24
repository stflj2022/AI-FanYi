"""
M10 Prosody & Performance 数据模型
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from pathlib import Path


class EmotionType(str, Enum):
    """情绪类型"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEAR = "fear"
    SURPRISED = "surprised"
    CALM = "calm"
    EXCITED = "excited"
    WORRIED = "worried"
    CONFIDENT = "confident"


@dataclass
class ProsodyParams:
    """韵律参数"""
    pitch: float = 1.0  # 音高因子
    speed: float = 1.0  # 语速因子
    volume: float = 1.0  # 音量因子
    pause_before: float = 0.0  # 前停顿（秒）
    pause_after: float = 0.0  # 后停顿（秒）
    energy: float = 1.0  # 能量/强度
    breath: bool = False  # 是否添加呼吸声

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "pitch": self.pitch,
            "speed": self.speed,
            "volume": self.volume,
            "pause_before": self.pause_before,
            "pause_after": self.pause_after,
            "energy": self.energy,
            "breath": self.breath,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProsodyParams":
        """从字典创建"""
        return cls(
            pitch=data.get("pitch", 1.0),
            speed=data.get("speed", 1.0),
            volume=data.get("volume", 1.0),
            pause_before=data.get("pause_before", 0.0),
            pause_after=data.get("pause_after", 0.0),
            energy=data.get("energy", 1.0),
            breath=data.get("breath", False),
        )


@dataclass
class DialogueSegment:
    """对白片段"""
    dialogue_id: str
    text: str
    audio_path: Path  # TTS 生成的原始音频
    speaker: str
    character: str
    emotion: EmotionType = EmotionType.NEUTRAL
    target_duration: Optional[float] = None  # 目标时长（秒）
    current_duration: Optional[float] = None  # 当前时长（秒）

    # 韵律参数
    prosody_params: Optional[ProsodyParams] = None

    # 输出
    output_path: Optional[Path] = None  # 处理后的音频路径

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "dialogue_id": self.dialogue_id,
            "text": self.text,
            "audio_path": str(self.audio_path),
            "speaker": self.speaker,
            "character": self.character,
            "emotion": self.emotion.value,
            "target_duration": self.target_duration,
            "current_duration": self.current_duration,
            "prosody_params": self.prosody_params.to_dict() if self.prosody_params else None,
            "output_path": str(self.output_path) if self.output_path else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DialogueSegment":
        """从字典创建"""
        return cls(
            dialogue_id=data["dialogue_id"],
            text=data["text"],
            audio_path=Path(data["audio_path"]),
            speaker=data["speaker"],
            character=data["character"],
            emotion=EmotionType(data.get("emotion", "neutral")),
            target_duration=data.get("target_duration"),
            current_duration=data.get("current_duration"),
            prosody_params=ProsodyParams.from_dict(data["prosody_params"]) if data.get("prosody_params") else None,
            output_path=Path(data["output_path"]) if data.get("output_path") else None,
        )


@dataclass
class ProsodyResult:
    """韵律处理结果"""
    dialogue_id: str
    input_path: Path
    output_path: Path
    success: bool
    error: Optional[str] = None
    applied_params: Optional[ProsodyParams] = None
    duration_before: Optional[float] = None
    duration_after: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "dialogue_id": self.dialogue_id,
            "input_path": str(self.input_path),
            "output_path": str(self.output_path),
            "success": self.success,
            "error": self.error,
            "applied_params": self.applied_params.to_dict() if self.applied_params else None,
            "duration_before": self.duration_before,
            "duration_after": self.duration_after,
        }


@dataclass
class BatchProsodyResult:
    """批量韵律处理结果"""
    total: int
    successful: int
    failed: int
    results: List[ProsodyResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total": self.total,
            "successful": self.successful,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
        }
