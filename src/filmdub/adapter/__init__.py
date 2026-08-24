"""
AI-FanYi Adapter Layer

This module provides a unified interface for external services (qwen-tts, etc.)
to be used by multiple modules (M04/M09/M02/M05) without coupling.
"""

from .voice import (
    VoiceAdapter,
    QwenTTSAdapter,
    CosyVoiceAdapter,
    F5TTSAdapter,
    LocalVoiceAdapter,
    VoiceAdapterInterface,
)
from .asr import ASRAdapter
from .separate import AudioSeparationAdapter

__all__ = [
    "VoiceAdapter",
    "QwenTTSAdapter",
    "CosyVoiceAdapter",
    "F5TTSAdapter",
    "LocalVoiceAdapter",
    "VoiceAdapterInterface",
    "ASRAdapter",
    "AudioSeparationAdapter",
]
