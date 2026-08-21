"""
Module 03 数据库模型
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json


class SubtitleSourceType(str, Enum):
    """字幕来源类型"""
    EMBEDDED = "embedded"  # 内嵌
    EXTERNAL = "external"  # 外部
    USER = "user"  # 用户上传


@dataclass
class SubtitleSource:
    """字幕来源"""
    id: str
    project_id: str
    media_id: str

    # 字幕信息
    language: str
    source_type: SubtitleSourceType
    path: Optional[str] = None
    stream_index: Optional[int] = None
    format: str = "srt"

    # 时间信息
    duration: Optional[float] = None

    # 质量评分
    confidence: float = 1.0
    quality_score: Optional[float] = None

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "media_id": self.media_id,
            "language": self.language,
            "source_type": self.source_type.value,
            "path": self.path,
            "stream_index": self.stream_index,
            "format": self.format,
            "duration": self.duration,
            "confidence": self.confidence,
            "quality_score": self.quality_score,
            "metadata": self.metadata,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubtitleSource':
        """从字典创建"""
        return cls(
            id=data["id"],
            project_id=data["project_id"],
            media_id=data["media_id"],
            language=data["language"],
            source_type=SubtitleSourceType(data["source_type"]),
            path=data.get("path"),
            stream_index=data.get("stream_index"),
            format=data.get("format", "srt"),
            duration=data.get("duration"),
            confidence=data.get("confidence", 1.0),
            quality_score=data.get("quality_score"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat())
        )


@dataclass
class Dialogue:
    """对白条目"""
    id: str
    episode_id: str

    # 时间信息
    start: float
    end: float

    # 文本
    source_text: str
    normalized_text: Optional[str] = None
    translated_text: Optional[str] = None

    # 语言
    source_language: str = "en"
    target_language: str = "zh-CN"

    # 说话人信息
    speaker_id: Optional[str] = None
    character_id: Optional[str] = None
    candidate_character: Optional[str] = None

    # 类型
    dialogue_type: str = "dialogue"
    emotion_hint: Optional[str] = None

    # 来源
    source_type: str = "subtitle"  # subtitle, asr
    translation_source: Optional[str] = None  # existing_subtitle, qwen_translation, null

    # 质量评分
    confidence: float = 1.0

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "episode_id": self.episode_id,
            "start": self.start,
            "end": self.end,
            "source_text": self.source_text,
            "normalized_text": self.normalized_text,
            "translated_text": self.translated_text,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "speaker_id": self.speaker_id,
            "character_id": self.character_id,
            "candidate_character": self.candidate_character,
            "dialogue_type": self.dialogue_type,
            "emotion_hint": self.emotion_hint,
            "source_type": self.source_type,
            "translation_source": self.translation_source,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Dialogue':
        """从字典创建"""
        return cls(
            id=data["id"],
            episode_id=data["episode_id"],
            start=data["start"],
            end=data["end"],
            source_text=data["source_text"],
            normalized_text=data.get("normalized_text"),
            translated_text=data.get("translated_text"),
            source_language=data.get("source_language", "en"),
            target_language=data.get("target_language", "zh-CN"),
            speaker_id=data.get("speaker_id"),
            character_id=data.get("character_id"),
            candidate_character=data.get("candidate_character"),
            dialogue_type=data.get("dialogue_type", "dialogue"),
            emotion_hint=data.get("emotion_hint"),
            source_type=data.get("source_type", "subtitle"),
            translation_source=data.get("translation_source"),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat())
        )


@dataclass
class TranslationMemory:
    """翻译记忆"""
    id: str
    project_id: str
    character_id: Optional[str]

    source_text: str
    translated_text: str
    scene_context: Optional[str] = None

    confidence: float = 1.0
    usage_count: int = 0

    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_used: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "character_id": self.character_id,
            "source_text": self.source_text,
            "translated_text": self.translated_text,
            "scene_context": self.scene_context,
            "confidence": self.confidence,
            "usage_count": self.usage_count,
            "created_at": self.created_at,
            "last_used": self.last_used
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranslationMemory':
        """从字典创建"""
        return cls(
            id=data["id"],
            project_id=data["project_id"],
            character_id=data.get("character_id"),
            source_text=data["source_text"],
            translated_text=data["translated_text"],
            scene_context=data.get("scene_context"),
            confidence=data.get("confidence", 1.0),
            usage_count=data.get("usage_count", 0),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            last_used=data.get("last_used")
        )


@dataclass
class SubtitleEvidence:
    """字幕证据"""
    id: str
    project_id: str

    # 证据类型
    evidence_type: str  # discovery, validation, alignment, quality, etc.

    # 数据
    data: Dict[str, Any]

    # 置信度
    confidence: float = 1.0

    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "evidence_type": self.evidence_type,
            "data": self.data,
            "confidence": self.confidence,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubtitleEvidence':
        """从字典创建"""
        return cls(
            id=data["id"],
            project_id=data["project_id"],
            evidence_type=data["evidence_type"],
            data=data["data"],
            confidence=data.get("confidence", 1.0),
            created_at=data.get("created_at", datetime.utcnow().isoformat())
        )
