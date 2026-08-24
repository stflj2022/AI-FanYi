"""TaskContext 单元测试"""

import pytest
from filmdub.orchestrator.workflow.task_context import (
    TaskContext,
    TaskType,
    QualityRequirement,
    SubtitleStatus,
    AudioStatus,
    DatabaseStatus,
)


class TestTaskContext:
    """TaskContext 测试"""

    def test_create_basic_task_context(self):
        """测试创建基本任务上下文"""
        context = TaskContext(
            project_id="test_project",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            subtitle=SubtitleStatus(exists=False),
            audio=AudioStatus(exists=False),
            character_db=DatabaseStatus(exists=False),
            voice_db=DatabaseStatus(exists=False),
            story_db=DatabaseStatus(exists=False),
            translation_memory=DatabaseStatus(exists=False),
        )

        assert context.project_id == "test_project"
        assert context.media_id == "S01E01"
        assert context.task_type == TaskType.EPISODE
        assert context.first_processing is True

    def test_create_from_project(self):
        """测试从项目信息创建 TaskContext"""
        context = TaskContext.from_project(
            project_id="breaking_bad",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            subtitle=SubtitleStatus(exists=False),
            audio=AudioStatus(exists=False),
            character_db=DatabaseStatus(exists=False),
            voice_db=DatabaseStatus(exists=False),
            story_db=DatabaseStatus(exists=False),
            translation_memory=DatabaseStatus(exists=False),
        )

        assert context.project_id == "breaking_bad"
        assert context.media_id == "S01E01"

    def test_is_short_video(self):
        """测试短视频判断"""
        # 短视频（15分钟）
        context = TaskContext(
            project_id="test",
            media_id="short",
            task_type=TaskType.CLIP,
            duration_seconds=15 * 60,
            subtitle=SubtitleStatus(exists=False),
            audio=AudioStatus(exists=False),
            character_db=DatabaseStatus(exists=False),
            voice_db=DatabaseStatus(exists=False),
            story_db=DatabaseStatus(exists=False),
            translation_memory=DatabaseStatus(exists=False),
        )
        assert context.is_short_video() is True

        # 长视频（45分钟）
        context.duration_seconds = 45 * 60
        assert context.is_short_video() is False

    def test_has_subtitle(self):
        """测试字幕存在判断"""
        context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            subtitle=SubtitleStatus(exists=True, language="zh-CN"),
            audio=AudioStatus(exists=False),
            character_db=DatabaseStatus(exists=False),
            voice_db=DatabaseStatus(exists=False),
            story_db=DatabaseStatus(exists=False),
            translation_memory=DatabaseStatus(exists=False),
        )
        assert context.has_subtitle() is True

        context.subtitle.exists = False
        assert context.has_subtitle() is False

    def test_has_verified_subtitle(self):
        """测试已验证字幕判断"""
        context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            subtitle=SubtitleStatus(exists=True, language="zh-CN", quality="verified"),
            audio=AudioStatus(exists=False),
            character_db=DatabaseStatus(exists=False),
            voice_db=DatabaseStatus(exists=False),
            story_db=DatabaseStatus(exists=False),
            translation_memory=DatabaseStatus(exists=False),
        )
        assert context.has_verified_subtitle() is True

        context.subtitle.quality = "low"
        assert context.has_verified_subtitle() is False

    def test_character_db_complete(self):
        """测试人物库完整判断"""
        context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            subtitle=SubtitleStatus(exists=False),
            audio=AudioStatus(exists=False),
            character_db=DatabaseStatus(exists=True, coverage=0.95),
            voice_db=DatabaseStatus(exists=False),
            story_db=DatabaseStatus(exists=False),
            translation_memory=DatabaseStatus(exists=False),
        )
        assert context.character_db_complete() is True

        context.character_db.coverage = 0.80
        assert context.character_db_complete() is False

        context.character_db.exists = False
        assert context.character_db_complete() is False

    def test_voice_db_complete(self):
        """测试声音库完整判断"""
        context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            subtitle=SubtitleStatus(exists=False),
            audio=AudioStatus(exists=False),
            character_db=DatabaseStatus(exists=False),
            voice_db=DatabaseStatus(exists=True, coverage=0.92),
            story_db=DatabaseStatus(exists=False),
            translation_memory=DatabaseStatus(exists=False),
        )
        assert context.voice_db_complete() is True

        context.voice_db.coverage = 0.85
        assert context.voice_db_complete() is False

    def test_is_first_processing(self):
        """测试首次处理判断"""
        context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            first_processing=True,
            subtitle=SubtitleStatus(exists=False),
            audio=AudioStatus(exists=False),
            character_db=DatabaseStatus(exists=False),
            voice_db=DatabaseStatus(exists=False),
            story_db=DatabaseStatus(exists=False),
            translation_memory=DatabaseStatus(exists=False),
        )
        assert context.is_first_processing() is True

        context.first_processing = False
        assert context.is_first_processing() is False

    def test_needs_full_processing(self):
        """测试需要全流程处理判断"""
        # 首次处理
        context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            first_processing=True,
            subtitle=SubtitleStatus(exists=False),
            audio=AudioStatus(exists=False),
            character_db=DatabaseStatus(exists=True, coverage=0.95),
            voice_db=DatabaseStatus(exists=True, coverage=0.95),
            story_db=DatabaseStatus(exists=False),
            translation_memory=DatabaseStatus(exists=False),
        )
        assert context.needs_full_processing() is True

        # 人物库不完整
        context.first_processing = False
        context.character_db.coverage = 0.70
        assert context.needs_full_processing() is True

        # 声音库不完整
        context.character_db.coverage = 0.95
        context.voice_db.coverage = 0.60
        assert context.needs_full_processing() is True

        # 都完整，不需要全流程
        context.voice_db.coverage = 0.95
        assert context.needs_full_processing() is False

    def test_task_type_enum(self):
        """测试任务类型枚举"""
        assert TaskType.PREVIEW.value == "preview"
        assert TaskType.CLIP.value == "clip"
        assert TaskType.EPISODE.value == "episode"
        assert TaskType.MOVIE.value == "movie"
        assert TaskType.SEASON.value == "season"
        assert TaskType.REVOICE.value == "revoice"
        assert TaskType.RERENDER.value == "rerender"
        assert TaskType.QA.value == "qa"

    def test_quality_requirement_enum(self):
        """测试质量要求枚举"""
        assert QualityRequirement.QUICK.value == "quick"
        assert QualityRequirement.STANDARD.value == "standard"
        assert QualityRequirement.PRODUCTION.value == "production"

    def test_context_with_metadata(self):
        """测试带元数据的上下文"""
        context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            metadata={"custom_field": "value", "priority": "high"},
            subtitle=SubtitleStatus(exists=False),
            audio=AudioStatus(exists=False),
            character_db=DatabaseStatus(exists=False),
            voice_db=DatabaseStatus(exists=False),
            story_db=DatabaseStatus(exists=False),
            translation_memory=DatabaseStatus(exists=False),
        )

        assert context.metadata["custom_field"] == "value"
        assert context.metadata["priority"] == "high"

    def test_context_with_force_workflow(self):
        """测试强制工作流"""
        context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            force_workflow="custom_workflow",
            subtitle=SubtitleStatus(exists=False),
            audio=AudioStatus(exists=False),
            character_db=DatabaseStatus(exists=False),
            voice_db=DatabaseStatus(exists=False),
            story_db=DatabaseStatus(exists=False),
            translation_memory=DatabaseStatus(exists=False),
        )

        assert context.force_workflow == "custom_workflow"
