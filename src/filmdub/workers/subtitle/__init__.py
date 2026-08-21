"""
Module 03: Subtitle & Dialogue Acquisition Worker

负责字幕发现、导入、验证、对齐、对白提取、翻译和ASR
核心原则：优先使用现成中文字幕，没有才翻译，没有才ASR
"""

from .models import (
    Dialogue,
    SubtitleSource,
    TranslationMemory,
    SubtitleEvidence
)
from .config import SubtitleConfig, TranslationMode, DialogueType
from .runner import SubtitleRunner

__all__ = [
    'Dialogue',
    'SubtitleSource',
    'TranslationMemory',
    'SubtitleEvidence',
    'SubtitleConfig',
    'TranslationMode',
    'DialogueType',
    'SubtitleRunner'
]
