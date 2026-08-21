"""
M11 Video Assembly 配置
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class M11Config:
    """M11 配置"""

    # FFmpeg 配置
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    # 编码参数
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "5M"
    audio_bitrate: str = "192k"
    preset: str = "medium"
    crf: int = 23

    # 音频处理
    audio_sample_rate: int = 48000
    audio_channels: int = 2

    # 字幕
    enable_subtitles: bool = True
    subtitle_font: str = "Arial"
    subtitle_font_size: int = 24
    subtitle_font_color: str = "white"

    # 性能
    num_threads: int = 4
    batch_size: int = 4
    max_concurrent_jobs: int = 2
