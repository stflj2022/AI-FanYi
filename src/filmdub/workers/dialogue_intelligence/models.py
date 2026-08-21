"""
M07 数据模型
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class ProcessedDialogue:
    """处理后的对白"""
    dialogue_id: str
    original_text: str
    processed_text: str
    character_id: str
    speaker_id: str
    start_time: float
    end_time: float

    # 处理信息
    terminology_changes: List[Dict[str, str]]
    cultural_adaptations: List[Dict[str, str]]
    tone_adjustments: List[Dict[str, str]]

    # 元数据
    confidence: float
    needs_manual_review: bool = False
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "dialogue_id": self.dialogue_id,
            "original_text": self.original_text,
            "processed_text": self.processed_text,
            "character_id": self.character_id,
            "speaker_id": self.speaker_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "terminology_changes": self.terminology_changes,
            "cultural_adaptations": self.cultural_adaptations,
            "tone_adjustments": self.tone_adjustments,
            "confidence": self.confidence,
            "needs_manual_review": self.needs_manual_review,
            "notes": self.notes
        }


@dataclass
class TerminologyEntry:
    """术语条目"""
    term: str
    translation: str
    context: str
    category: str
