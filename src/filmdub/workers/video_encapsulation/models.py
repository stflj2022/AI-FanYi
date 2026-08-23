"""
M12 视频封装数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SubtitleMode(str, Enum):
    """字幕模式"""
    SOFT = "soft"  # 软字幕（独立轨道）
    HARD = "hard"  # 硬字幕（烧录到视频中）


class AudioTrack(BaseModel):
    """音轨配置"""
    file_path: str = Field(..., description="音频文件路径")
    volume: float = Field(default=1.0, ge=0.0, le=1.0, description="音量 (0.0-1.0)")
    language: Optional[str] = Field(default=None, description="语言代码 (如 'chi', 'eng')")
    is_default: bool = Field(default=False, description="是否为默认音轨")


class VideoQuality(BaseModel):
    """视频质量控制"""
    width: Optional[int] = Field(default=None, description="视频宽度")
    height: Optional[int] = Field(default=None, description="视频高度")
    bitrate: Optional[str] = Field(default=None, description="视频码率 (如 '2M')")
    fps: Optional[int] = Field(default=None, description="帧率")
    preset: Optional[str] = Field(default="medium", description="编码预设")
    crf: Optional[int] = Field(default=23, ge=0, le=51, description="恒定质量因子")


class SubtitleTrack(BaseModel):
    """字幕配置"""
    file_path: str = Field(..., description="字幕文件路径")
    language: Optional[str] = Field(default=None, description="语言代码")
    mode: SubtitleMode = Field(default=SubtitleMode.SOFT, description="字幕模式")
    font_name: Optional[str] = Field(default="Arial", description="字体名称")
    font_size: Optional[int] = Field(default=24, description="字号")
    color: Optional[str] = Field(default="&H00FFFFFF", description="颜色 (ASS 格式)")


class EncapsulationInput(BaseModel):
    """封装输入"""
    video_file: str = Field(..., description="原始视频文件路径")
    audio_tracks: List[AudioTrack] = Field(default_factory=list, description="音轨列表")
    subtitle_track: Optional[SubtitleTrack] = Field(default=None, description="字幕配置")
    output_file: str = Field(..., description="输出文件路径")
    quality: Optional[VideoQuality] = Field(default=None, description="视频质量控制")


class EncapsulationResult(BaseModel):
    """封装结果"""
    success: bool = Field(..., description="是否成功")
    output_file: str = Field(..., description="输出文件路径")
    duration: float = Field(..., description="视频时长（秒）")
    size_bytes: int = Field(..., description="文件大小（字节）")
    video_bitrate: Optional[str] = Field(default=None, description="实际视频码率")
    audio_bitrate: Optional[str] = Field(default=None, description="实际音频码率")
    resolution: str = Field(..., description="分辨率")
    fps: float = Field(..., description="帧率")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
