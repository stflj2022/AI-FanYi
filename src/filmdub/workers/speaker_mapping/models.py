"""
M06 数据模型
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class SpeakerToCharacterMapping:
    """说话人到人物映射"""
    speaker_id: str
    character_id: str
    similarity: float
    confidence: float
    voice_profile_id: Optional[str] = None
    manual_override: bool = False
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "speaker_id": self.speaker_id,
            "character_id": self.character_id,
            "similarity": self.similarity,
            "confidence": self.confidence,
            "voice_profile_id": self.voice_profile_id,
            "manual_override": self.manual_override,
            "notes": self.notes
        }


@dataclass
class VoiceProfile:
    """音色配置"""
    voice_profile_id: str
    character_id: str
    name: str
    gender: str
    age_range: str
    style: str
    emotion: str
    pitch: float
    speed: float
    volume: float
    is_reference: bool = False
    reference_audio_path: Optional[str] = None
    created_at: str = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "voice_profile_id": self.voice_profile_id,
            "character_id": self.character_id,
            "name": self.name,
            "gender": self.gender,
            "age_range": self.age_range,
            "style": self.style,
            "emotion": self.emotion,
            "pitch": self.pitch,
            "speed": self.speed,
            "volume": self.volume,
            "is_reference": self.is_reference,
            "reference_audio_path": self.reference_audio_path,
            "created_at": self.created_at
        }


@dataclass
class MappingResult:
    """映射结果"""
    mappings: List[SpeakerToCharacterMapping]
    voice_profiles: List[VoiceProfile]
    unmapped_speakers: List[str]
    unmapped_characters: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "mappings": [m.to_dict() for m in self.mappings],
            "voice_profiles": [vp.to_dict() for vp in self.voice_profiles],
            "unmapped_speakers": self.unmapped_speakers,
            "unmapped_characters": self.unmapped_characters
        }
