"""Task Context - 任务上下文构建

为每个任务构建统一的任务上下文，包括：
- 项目信息
- 媒体信息
- 资源状态（字幕、音频、人物库、声音库、故事库、翻译记忆）
- 任务类型
- 质量要求
- 首次处理标记
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """任务类型"""
    PREVIEW = "preview"  # 预览
    CLIP = "clip"  # 片段
    EPISODE = "episode"  # 单集
    MOVIE = "movie"  # 电影
    SEASON = "season"  # 季
    REVOICE = "revoice"  # 重新配音
    RERENDER = "rerender"  # 重新渲染
    QA = "qa"  # 质检


class QualityRequirement(str, Enum):
    """质量要求"""
    QUICK = "quick"  # 快速
    STANDARD = "standard"  # 标准
    PRODUCTION = "production"  # 生产


class SubtitleStatus(BaseModel):
    """字幕状态"""
    exists: bool
    language: Optional[str] = None
    quality: Optional[str] = None  # verified, low, timing_error
    timing_quality: Optional[str] = None  # good, poor, unknown


class AudioStatus(BaseModel):
    """音频状态"""
    exists: bool
    quality: Optional[str] = None  # good, poor, unknown


class DatabaseStatus(BaseModel):
    """数据库状态（人物库、声音库等）"""
    exists: bool
    coverage: float = 0.0  # 覆盖率 0.0 - 1.0
    version: Optional[str] = None
    outdated: bool = False


class TaskContext(BaseModel):
    """任务上下文

    整个 Layer 0 的标准输入，包含任务的所有必要信息。
    """
    project_id: str
    media_id: str
    task_type: TaskType

    # 媒体时长（秒）
    duration_seconds: Optional[float] = None

    # 资源状态（可选，便于测试）
    subtitle: Optional[SubtitleStatus] = None
    audio: Optional[AudioStatus] = None
    character_db: Optional[DatabaseStatus] = None
    voice_db: Optional[DatabaseStatus] = None
    story_db: Optional[DatabaseStatus] = None
    translation_memory: Optional[DatabaseStatus] = None

    # 任务属性
    first_processing: bool = True
    quality_requirement: QualityRequirement = QualityRequirement.STANDARD
    force_workflow: Optional[str] = None  # 强制使用的工作流

    # 扩展字段
    metadata: dict = Field(default_factory=dict)

    @classmethod
    def from_project(
        cls,
        project_id: str,
        media_id: str,
        task_type: TaskType,
        **kwargs
    ) -> "TaskContext":
        """从项目信息创建 TaskContext

        Args:
            project_id: 项目 ID
            media_id: 媒体 ID
            task_type: 任务类型
            **kwargs: 其他属性

        Returns:
            TaskContext 实例
        """
        return cls(
            project_id=project_id,
            media_id=media_id,
            task_type=task_type,
            **kwargs
        )

    def is_short_video(self, threshold_seconds: float = 20 * 60) -> bool:
        """判断是否为短视频（≤20分钟）"""
        if self.duration_seconds is None:
            return False
        return self.duration_seconds <= threshold_seconds

    def has_subtitle(self) -> bool:
        """是否有字幕"""
        return self.subtitle.exists

    def has_verified_subtitle(self) -> bool:
        """是否有已验证的字幕"""
        return self.subtitle.exists and self.subtitle.quality == "verified"

    def character_db_complete(self) -> bool:
        """人物库是否完整（覆盖率 ≥ 90%）"""
        return self.character_db.exists and self.character_db.coverage >= 0.9

    def voice_db_complete(self) -> bool:
        """声音库是否完整（覆盖率 ≥ 90%）"""
        return self.voice_db.exists and self.voice_db.coverage >= 0.9

    def is_first_processing(self) -> bool:
        """是否首次处理"""
        return self.first_processing

    def needs_full_processing(self) -> bool:
        """是否需要全流程处理"""
        return (
            self.is_first_processing()
            or not self.character_db_complete()
            or not self.voice_db_complete()
        )
