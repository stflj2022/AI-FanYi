"""
M09 数据模型
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class M09Input:
    """M09 输入"""
    dialogue_id: str
    character_id: str
    voice_profile_id: str
    text: str

    # 韵律参数
    speed: float = 1.0
    pitch: float = 0.0
    pause_before: float = 0.0
    pause_after: float = 0.0
    energy: float = 1.0

    # 情绪
    emotion: str = "neutral"
    emotion_intensity: float = 0.5

    # 元数据
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AudioArtifact:
    """音频 Artifact"""
    artifact_id: str
    dialogue_id: str
    character_id: str
    file_path: str
    duration: float
    sample_rate: int
    num_channels: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "artifact_id": self.artifact_id,
            "dialogue_id": self.dialogue_id,
            "character_id": self.character_id,
            "file_path": self.file_path,
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "num_channels": self.num_channels
        }


@dataclass
class M09Output:
    """M09 输出"""
    status: str
    dialogue_id: str
    character_id: str
    audio_artifact: Optional[AudioArtifact] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status,
            "dialogue_id": self.dialogue_id,
            "character_id": self.character_id,
            "audio_artifact": self.audio_artifact.to_dict() if self.audio_artifact else None,
            "error": self.error,
            "metadata": self.metadata
        }
