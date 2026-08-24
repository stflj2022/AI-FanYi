"""
M11 Video Assembly 配置
"""
from dataclasses import dataclass, field
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

    # 音频分离配置
    enable_audio_separation: bool = True
    separation_model: str = "htdemucs"  # HTDemucs 模型
    separation_device: str = "cpu"

    # LUFS 响度归一化配置
    enable_lufs_normalization: bool = True
    target_lufs: float = -16.0  # EBU R128 目标响度
    lufs_tolerance: float = 2.0  # 容差

    # 原声处理配置
    original_vocal_volume: float = 0.0  # 原人声音量（0.0 = 完全静音）
    dialogue_suppression_db: float = -60.0  # 对白时段原声衰减 dB

    # 音轨音量配置
    dialogue_volume: float = 1.0  # AI 对白音量
    background_volume: float = 0.3  # 背景音乐音量
    ambient_volume: float = 0.5  # 环境音音量
    effects_volume: float = 0.8  # 音效音量

    # 音轨混合配置
    default_fade_in: float = 0.5  # 默认淡入时长
    default_fade_out: float = 0.5  # 默认淡出时长
    crossfade_duration: float = 0.2  # 交叉混合时长
