"""
M12 视频封装配置
"""
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class M12Config(BaseSettings):
    """M12 视频封装配置"""

    # FFmpeg 路径
    ffmpeg_path: str = Field(default="ffmpeg", description="FFmpeg 可执行文件路径")

    # 输出视频格式
    video_codec: str = Field(default="libx264", description="视频编码器")
    audio_codec: str = Field(default="aac", description="音频编码器")
    container_format: str = Field(default="mp4", description="容器格式")

    # 视频质量控制
    video_bitrate: str = Field(default="2M", description="视频码率")
    audio_bitrate: str = Field(default="192k", description="音频码率")
    preset: str = Field(default="medium", description="编码预设 (ultrafast/superfast/veryfast/faster/fast/medium/slow/slower/veryslow)")
    crf: int = Field(default=23, description="恒定质量因子 (0-51, 越小质量越高)")

    # 分辨率控制
    scale: str = Field(default="", description="视频缩放 (如 '1280:720')")

    # 帧率控制
    fps: int = Field(default=30, description="输出帧率")

    # 字幕控制
    subtitle_mode: str = Field(default="soft", description="字幕模式 (soft/hard)")
    subtitle_font: str = Field(default="Arial", description="字幕字体")
    subtitle_font_size: int = Field(default=24, description="字幕字号")
    subtitle_color: str = Field(default="&H00FFFFFF", description="字幕颜色 (ASS 格式)")

    # 音频混音
    dialogue_volume: float = Field(default=1.0, description="中文对白音量 (0.0-1.0)")
    background_volume: float = Field(default=0.3, description="背景音乐音量 (0.0-1.0)")

    # 临时目录
    temp_dir: str = Field(default="/tmp/filmdub_m12", description="临时文件目录")

    model_config = ConfigDict(
        env_prefix="M12_",
        case_sensitive=False
    )
