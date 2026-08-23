"""
M12 视频封装模块

将中文对白、背景音、字幕组装成最终的 mp4 视频
"""
from .config import M12Config
from .worker import VideoEncapsulationWorker
from .models import (
    EncapsulationInput,
    EncapsulationResult,
    AudioTrack,
    SubtitleTrack,
    VideoQuality,
    SubtitleMode
)

__all__ = [
    "M12Config",
    "VideoEncapsulationWorker",
    "EncapsulationInput",
    "EncapsulationResult",
    "AudioTrack",
    "SubtitleTrack",
    "VideoQuality",
    "SubtitleMode",
]
