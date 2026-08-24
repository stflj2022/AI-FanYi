"""
M13 QA 配置
"""
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class M13Config(BaseSettings):
    """M13 QA 配置"""

    # FFprobe 路径
    ffprobe_path: str = Field(default="ffprobe", description="FFprobe 可执行文件路径")

    # FFmpeg 路径（用于音量分析）
    ffmpeg_path: str = Field(default="ffmpeg", description="FFmpeg 可执行文件路径")

    # 技术质量阈值
    min_video_width: int = Field(default=720, description="最小视频宽度")
    min_video_height: int = Field(default=480, description="最小视频高度")
    min_fps: float = Field(default=23.976, description="最小帧率")
    max_fps: float = Field(default=60.0, description="最大帧率")
    min_audio_sample_rate: int = Field(default=44100, description="最小音频采样率")
    min_audio_channels: int = Field(default=2, description="最小音频声道数")

    # 音量标准（基于 ITU-R BS.1770）
    target_lufs: float = Field(default=-23.0, description="目标响度（LUFS）")
    lufs_tolerance: float = Field(default=2.0, description="响度容差（LUFS）")
    peak_db: float = Field(default=-1.0, description="最大峰值（dB）")

    # 同步检查
    sync_tolerance_seconds: float = Field(default=0.1, description="音画同步容差（秒）")

    # 静音检测
    silence_threshold_db: float = Field(default=-40.0, description="静音检测阈值（dB）")
    min_silence_duration: float = Field(default=2.0, description="最小静音持续时长（秒），超过即报告")

    # 对白完整性
    duplicate_dialogue_gap: float = Field(default=0.5, description="重复台词判定时间间隔（秒）")

    # 配音质量评分权重（总和为 1.0）
    weight_voice_consistency: float = Field(default=0.25, description="音色一致性权重")
    weight_emotion_match: float = Field(default=0.25, description="情绪匹配权重")
    weight_speech_rate: float = Field(default=0.20, description="语速合理性权重")
    weight_translation: float = Field(default=0.15, description="翻译质量权重")
    weight_dialogue_completeness: float = Field(default=0.10, description="对白完整性权重")
    weight_character_mismatch: float = Field(default=0.05, description="人物错配权重")

    # 技术质量扣分（按严重程度）
    deduction_critical: float = Field(default=30.0, description="严重问题扣分")
    deduction_high: float = Field(default=15.0, description="高优先级问题扣分")
    deduction_medium: float = Field(default=5.0, description="中等优先级问题扣分")
    deduction_low: float = Field(default=2.0, description="低优先级问题扣分")

    # 输出格式
    output_format: str = Field(default="json", description="输出格式（json/markdown）")
    output_dir: str = Field(default="/tmp/filmdub_qa", description="输出目录")
    report_enabled: bool = Field(default=True, description="是否写出 QA 报告文件")

    # 严格程度
    strict_mode: bool = Field(default=False, description="严格模式（所有问题都导致失败）")

    model_config = ConfigDict(
        env_prefix="M13_",
        case_sensitive=False
    )
