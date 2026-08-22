"""Translation module models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4


@dataclass
class TranslationRequest:
    """Translation request."""

    text: str
    source_lang: str = "en"
    target_lang: str = "zh"
    context: Optional[str] = None
    character_id: Optional[UUID] = None
    emotion: Optional[str] = None


@dataclass
class TranslationResult:
    """Translation result."""

    original_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    confidence: float = 1.0
    used_memory: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TermEntry:
    """Glossary term entry."""

    source_term: str
    target_term: str
    category: str = ""
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TranslationMemoryEntry:
    """Translation memory entry."""

    id: UUID = field(default_factory=uuid4)
    source_text: str = ""
    translated_text: str = ""
    source_lang: str = "en"
    target_lang: str = "zh"
    context: str = ""
    usage_count: int = 0
    last_used: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class M06Input:
    """M06 Worker input."""

    project_id: UUID
    job_id: UUID
    dialogue_timeline: List[Dict]
    character_database: Dict
    translation_memory: Optional[List[TranslationMemoryEntry]] = None


@dataclass
class M06Output:
    """M06 Worker output."""

    project_id: UUID
    job_id: UUID
    translated_dialogues: List[Dict]
    translation_memory_updates: List[TranslationMemoryEntry]
    statistics: Dict
