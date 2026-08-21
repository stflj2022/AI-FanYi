"""
M06 数据模型
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class MappingStatus(Enum):
    """映射状态"""
    AUTO_CONFIRMED = "auto_confirmed"
    MANUAL_REVIEW = "manual_review"
    FAILED = "failed"


@dataclass
class SpeakerToCharacterMapping:
    """说话人到人物的映射"""
    speaker_id: str
    character_id: str
    similarity: float
    confidence: float
    status: MappingStatus
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "speaker_id": self.speaker_id,
            "character_id": self.character_id,
            "similarity": self.similarity,
            "confidence": self.confidence,
            "status": self.status.value,
            "metadata": self.metadata
        }


@dataclass
class VoiceProfileAssignment:
    """音色分配"""
    character_id: str
    voice_profile_id: str
    is_new: bool = False
    confidence: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "character_id": self.character_id,
            "voice_profile_id": self.voice_profile_id,
            "is_new": self.is_new,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


@dataclass
class MappingResult:
    """映射结果"""
    mappings: List[SpeakerToCharacterMapping]
    voice_assignments: List[VoiceProfileAssignment]
    num_speakers: int
    num_characters: int
    num_auto_confirmed: int
    num_manual_review: int

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "mappings": [m.to_dict() for m in self.mappings],
            "voice_assignments": [v.to_dict() for v in self.voice_assignments],
            "num_speakers": self.num_speakers,
            "num_characters": self.num_characters,
            "num_auto_confirmed": self.num_auto_confirmed,
            "num_manual_review": self.num_manual_review
        }
