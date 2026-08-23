"""
M13 QA 数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class QAIssueSeverity(str, Enum):
    """问题严重程度"""
    CRITICAL = "critical"  # 严重问题，必须修复
    HIGH = "high"  # 高优先级问题
    MEDIUM = "medium"  # 中等优先级问题
    LOW = "low"  # 低优先级问题，可选修复
    INFO = "info"  # 信息性提示


class QAIssueCategory(str, Enum):
    """问题分类"""
    TECHNICAL = "technical"  # 技术质量问题
    VOICE = "voice"  # 配音质量问题
    SYNC = "sync"  # 音画同步问题
    SUBTITLE = "subtitle"  # 字幕问题
    PERFORMANCE = "performance"  # 性能问题
    OTHER = "other"  # 其他问题


class QAIssue(BaseModel):
    """QA 问题"""
    category: QAIssueCategory = Field(..., description="问题分类")
    severity: QAIssueSeverity = Field(..., description="严重程度")
    title: str = Field(..., description="问题标题")
    description: str = Field(..., description="问题描述")
    details: Optional[str] = Field(default=None, description="详细信息")
    suggestion: Optional[str] = Field(default=None, description="修复建议")
    timestamp: Optional[float] = Field(default=None, description="问题发生时间点（秒）")
    duration: Optional[float] = Field(default=None, description="问题持续时长（秒）")


class TechnicalQuality(BaseModel):
    """技术质量检查结果"""
    passed: bool = Field(..., description="是否通过")
    score: float = Field(..., ge=0.0, le=100.0, description="技术质量评分（0-100）")

    # 视频质量
    video_codec: Optional[str] = Field(default=None, description="视频编码")
    video_width: Optional[int] = Field(default=None, description="视频宽度")
    video_height: Optional[int] = Field(default=None, description="视频高度")
    video_bitrate: Optional[int] = Field(default=None, description="视频码率（bps）")
    fps: Optional[float] = Field(default=None, description="帧率")

    # 音频质量
    audio_codec: Optional[str] = Field(default=None, description="音频编码")
    audio_sample_rate: Optional[int] = Field(default=None, description="音频采样率")
    audio_channels: Optional[int] = Field(default=None, description="音频声道数")
    audio_bitrate: Optional[int] = Field(default=None, description="音频码率（bps）")
    loudness_lufs: Optional[float] = Field(default=None, description="响度（LUFS）")
    peak_db: Optional[float] = Field(default=None, description="峰值（dB）")

    # 同步质量
    sync_offset: Optional[float] = Field(default=None, description="音画同步偏差（秒）")
    sync_issues: int = Field(default=0, description="同步问题数量")

    # 文件信息
    duration: float = Field(default=0.0, description="视频时长（秒）")
    size_bytes: int = Field(default=0, description="文件大小（字节）")


class VoiceQuality(BaseModel):
    """配音质量检查结果"""
    passed: bool = Field(..., description="是否通过")
    score: float = Field(..., ge=0.0, le=100.0, description="配音质量评分（0-100）")

    # 音色一致性
    voice_consistency: float = Field(default=100.0, ge=0.0, le=100.0, description="音色一致性评分")
    voice_issues: int = Field(default=0, description="音色问题数量")

    # 情绪匹配
    emotion_match: float = Field(default=100.0, ge=0.0, le=100.0, description="情绪匹配评分")
    emotion_issues: int = Field(default=0, description="情绪问题数量")

    # 语速合理性
    speech_rate_reasonable: float = Field(default=100.0, ge=0.0, le=100.0, description="语速合理性评分")
    speech_rate_issues: int = Field(default=0, description="语速问题数量")

    # 翻译质量
    translation_quality: float = Field(default=100.0, ge=0.0, le=100.0, description="翻译质量评分")
    translation_issues: int = Field(default=0, description="翻译问题数量")


class QAResult(BaseModel):
    """QA 检查结果"""
    success: bool = Field(False, description="总体是否通过")
    overall_score: float = Field(0.0, ge=0.0, le=100.0, description="总体评分（0-100）")

    # 子检查结果
    technical_quality: TechnicalQuality = Field(..., description="技术质量检查结果")
    voice_quality: VoiceQuality = Field(..., description="配音质量检查结果")

    # 问题列表
    issues: List[QAIssue] = Field(default_factory=list, description="问题列表")

    # 统计
    critical_issues: int = Field(default=0, description="严重问题数量")
    high_issues: int = Field(default=0, description="高优先级问题数量")
    medium_issues: int = Field(default=0, description="中等优先级问题数量")
    low_issues: int = Field(default=0, description="低优先级问题数量")
    info_issues: int = Field(default=0, description="信息提示数量")

    # 元数据
    checked_at: datetime = Field(default_factory=datetime.utcnow, description="检查时间")
    video_file: str = Field(..., description="检查的视频文件")
    duration_seconds: float = Field(default=0.0, description="视频时长（秒）")

    def calculate_statistics(self):
        """计算问题统计"""
        self.critical_issues = sum(1 for i in self.issues if i.severity == QAIssueSeverity.CRITICAL)
        self.high_issues = sum(1 for i in self.issues if i.severity == QAIssueSeverity.HIGH)
        self.medium_issues = sum(1 for i in self.issues if i.severity == QAIssueSeverity.MEDIUM)
        self.low_issues = sum(1 for i in self.issues if i.severity == QAIssueSeverity.LOW)
        self.info_issues = sum(1 for i in self.issues if i.severity == QAIssueSeverity.INFO)

    def calculate_overall_score(self):
        """计算总体评分"""
        # 技术质量权重 40%
        # 配音质量权重 60%
        self.overall_score = (
            self.technical_quality.score * 0.4 +
            self.voice_quality.score * 0.6
        )


class QAInput(BaseModel):
    """QA 检查输入"""
    video_file: str = Field(..., description="中文配音视频文件路径")
    original_video: Optional[str] = Field(default=None, description="原始视频文件路径（用于对比）")
    character_db: Optional[str] = Field(default=None, description="人物数据库路径")
    dialogue_timeline: Optional[str] = Field(default=None, description="对白时间轴路径")
    subtitle_file: Optional[str] = Field(default=None, description="字幕文件路径")
    strict_mode: bool = Field(default=False, description="严格模式")
