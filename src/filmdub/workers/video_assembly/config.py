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

    # 视频编码参数
    video_codec: str = "libx264"
    video_bitrate: str = "5M"
    video_preset: str = "medium"
    crf: int = 23  # Constant Rate Factor (18-28, 越低质量越高)

    # 音频编码参数
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    audio_sample_rate: int = 48000

    # 字幕配置
    subtitle_font: str = "Arial"
    subtitle_font_size: int = 24
    subtitle_color: str = "&H00FFFFFF"  # 白色
    subtitle_outline_color: str = "&H00000000"  # 黑色边框
    subtitle_outline_width: int = 2

    # 性能
    max_concurrent_jobs: int = 2
    gpu_acceleration: bool = False
