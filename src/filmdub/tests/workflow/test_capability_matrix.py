"""CapabilityMatrix 单元测试"""

import pytest
from filmdub.orchestrator.workflow.capability_matrix import (
    CapabilityMatrix,
    CapabilityState,
    CapabilityEntry,
    CapabilityThreshold,
    CapabilityBuilder,
)
from filmdub.orchestrator.workflow.asset_discovery import AssetStatus, AssetState


class TestCapabilityState:
    """CapabilityState 测试"""

    def test_enum_values(self):
        """测试枚举值"""
        assert CapabilityState.NONE.value == "none"
        assert CapabilityState.PARTIAL.value == "partial"
        assert CapabilityState.COMPLETE.value == "complete"
        assert CapabilityState.INVALID.value == "invalid"
        assert CapabilityState.OUTDATED.value == "outdated"


class TestCapabilityThreshold:
    """CapabilityThreshold 测试"""

    def test_default_values(self):
        """测试默认值"""
        threshold = CapabilityThreshold()
        assert threshold.partial_min == 0.3
        assert threshold.partial_max == 0.89
        assert threshold.complete_min == 0.9

    def test_custom_values(self):
        """测试自定义值"""
        threshold = CapabilityThreshold(
            partial_min=0.2,
            partial_max=0.8,
            complete_min=0.85
        )
        assert threshold.partial_min == 0.2
        assert threshold.partial_max == 0.8
        assert threshold.complete_min == 0.85


class TestCapabilityEntry:
    """CapabilityEntry 测试"""

    def test_create_basic(self):
        """测试创建基本条目"""
        entry = CapabilityEntry(state=CapabilityState.COMPLETE)
        assert entry.state == CapabilityState.COMPLETE
        assert entry.coverage == 0.0
        assert entry.version is None

    def test_create_with_details(self):
        """测试创建带详细信息的条目"""
        entry = CapabilityEntry(
            state=CapabilityState.PARTIAL,
            coverage=0.75,
            version="1.0",
            metadata={"quality": "good"},
        )
        assert entry.state == CapabilityState.PARTIAL
        assert entry.coverage == 0.75
        assert entry.version == "1.0"
        assert entry.metadata["quality"] == "good"


class TestCapabilityMatrix:
    """CapabilityMatrix 测试"""

    def test_create_basic(self):
        """测试创建基本能力矩阵"""
        matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.NONE),
            character_db=CapabilityEntry(state=CapabilityState.NONE),
            voice_db=CapabilityEntry(state=CapabilityState.NONE),
            story_db=CapabilityEntry(state=CapabilityState.NONE),
            translation_memory=CapabilityEntry(state=CapabilityState.NONE),
        )
        assert matrix.video.state == CapabilityState.COMPLETE
        assert matrix.subtitle.state == CapabilityState.NONE

    def test_get_score(self):
        """测试获取能力评分"""
        matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.PARTIAL),
            subtitle=CapabilityEntry(state=CapabilityState.NONE),
            character_db=CapabilityEntry(state=CapabilityState.INVALID),
            voice_db=CapabilityEntry(state=CapabilityState.OUTDATED),
            story_db=CapabilityEntry(state=CapabilityState.NONE),
            translation_memory=CapabilityEntry(state=CapabilityState.NONE),
        )

        assert matrix.get_score("video") == 3
        assert matrix.get_score("audio") == 1
        assert matrix.get_score("subtitle") == 0
        assert matrix.get_score("character_db") == 1
        assert matrix.get_score("voice_db") == 2

    def test_has_capability(self):
        """测试检查能力"""
        matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.PARTIAL),
            subtitle=CapabilityEntry(state=CapabilityState.NONE),
            character_db=CapabilityEntry(state=CapabilityState.PARTIAL),
            voice_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            story_db=CapabilityEntry(state=CapabilityState.NONE),
            translation_memory=CapabilityEntry(state=CapabilityState.NONE),
        )

        assert matrix.has_capability("video", CapabilityState.COMPLETE) is True
        assert matrix.has_capability("video", CapabilityState.PARTIAL) is True
        assert matrix.has_capability("audio", CapabilityState.COMPLETE) is False
        assert matrix.has_capability("audio", CapabilityState.PARTIAL) is True
        assert matrix.has_capability("subtitle", CapabilityState.PARTIAL) is False

    def test_is_ready_for_production(self):
        """测试检查是否准备好生产级处理"""
        # 准备就绪
        matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.PARTIAL),
            character_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            voice_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            story_db=CapabilityEntry(state=CapabilityState.NONE),
            translation_memory=CapabilityEntry(state=CapabilityState.NONE),
        )
        assert matrix.is_ready_for_production() is True

        # 人物库不完整
        matrix.character_db = CapabilityEntry(state=CapabilityState.PARTIAL)
        assert matrix.is_ready_for_production() is False

    def test_is_ready_for_standard(self):
        """测试检查是否准备好标准处理"""
        # 准备就绪
        matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.PARTIAL),
            subtitle=CapabilityEntry(state=CapabilityState.PARTIAL),
            character_db=CapabilityEntry(state=CapabilityState.PARTIAL),
            voice_db=CapabilityEntry(state=CapabilityState.PARTIAL),
            story_db=CapabilityEntry(state=CapabilityState.NONE),
            translation_memory=CapabilityEntry(state=CapabilityState.NONE),
        )
        assert matrix.is_ready_for_standard() is True

        # 音频不存在
        matrix.audio = CapabilityEntry(state=CapabilityState.NONE)
        assert matrix.is_ready_for_standard() is False

    def test_get_missing_capabilities(self):
        """测试获取缺失能力"""
        matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.PARTIAL),
            subtitle=CapabilityEntry(state=CapabilityState.NONE),
            character_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            voice_db=CapabilityEntry(state=CapabilityState.PARTIAL),
            story_db=CapabilityEntry(state=CapabilityState.NONE),
            translation_memory=CapabilityEntry(state=CapabilityState.NONE),
        )

        missing = matrix.get_missing_capabilities(CapabilityState.COMPLETE)
        assert "audio" in missing
        assert "subtitle" in missing
        assert "voice_db" in missing
        assert "video" not in missing
        assert "character_db" not in missing

        missing = matrix.get_missing_capabilities(CapabilityState.PARTIAL)
        assert "subtitle" in missing
        assert "audio" not in missing
        assert "voice_db" not in missing


class TestCapabilityBuilder:
    """CapabilityBuilder 测试"""

    def test_from_asset_status_basic(self):
        """测试从 AssetStatus 构建基本能力矩阵"""
        asset_status = AssetStatus(
            video_exists=True,
            video_quality="good",
            audio_exists=True,
            audio_quality="good",
            subtitle_state=AssetState.COMPLETE,
            subtitle_language="zh-CN",
            subtitle_quality="verified",
            character_db_state=AssetState.COMPLETE,
            character_db_coverage=0.95,
            character_db_version="1.0",
            voice_db_state=AssetState.COMPLETE,
            voice_db_coverage=0.90,
            voice_db_version="1.0",
            story_db_state=AssetState.COMPLETE,
            translation_memory_state=AssetState.COMPLETE,
        )

        builder = CapabilityBuilder()
        matrix = builder.from_asset_status(asset_status)

        assert matrix.video.state == CapabilityState.COMPLETE
        assert matrix.audio.state == CapabilityState.COMPLETE
        assert matrix.subtitle.state == CapabilityState.COMPLETE
        assert matrix.character_db.state == CapabilityState.COMPLETE
        assert matrix.voice_db.state == CapabilityState.COMPLETE

    def test_from_asset_status_partial(self):
        """测试从 AssetStatus 构建部分能力矩阵"""
        asset_status = AssetStatus(
            video_exists=True,
            video_quality="good",
            audio_exists=True,
            audio_quality="good",
            subtitle_state=AssetState.PARTIAL,
            character_db_state=AssetState.PARTIAL,
            character_db_coverage=0.60,
            voice_db_state=AssetState.PARTIAL,
            voice_db_coverage=0.50,
            story_db_state=AssetState.NONE,
            translation_memory_state=AssetState.NONE,
        )

        builder = CapabilityBuilder()
        matrix = builder.from_asset_status(asset_status)

        # video/audio quality 为 "good"，所以是 COMPLETE
        assert matrix.video.state == CapabilityState.COMPLETE
        assert matrix.audio.state == CapabilityState.COMPLETE
        assert matrix.character_db.state == CapabilityState.PARTIAL
        assert matrix.voice_db.state == CapabilityState.PARTIAL
        assert matrix.story_db.state == CapabilityState.NONE
        assert matrix.translation_memory.state == CapabilityState.NONE

    def test_from_asset_status_outdated(self):
        """测试从 AssetStatus 构建过期能力矩阵"""
        asset_status = AssetStatus(
            video_exists=True,
            video_quality="good",
            audio_exists=True,
            audio_quality="good",
            character_db_state=AssetState.COMPLETE,
            character_db_coverage=0.95,
            character_db_version="1.0",
            voice_db_state=AssetState.COMPLETE,
            voice_db_coverage=0.95,
            voice_db_version="1.0",
        )

        current_versions = {
            "character_db": "2.0",
            "voice_db": "2.0",
        }

        builder = CapabilityBuilder()
        matrix = builder.from_asset_status(asset_status, current_versions)

        assert matrix.character_db.state == CapabilityState.OUTDATED
        assert matrix.voice_db.state == CapabilityState.OUTDATED
        assert matrix.character_db.metadata["current_version"] == "2.0"

    def test_from_asset_status_invalid(self):
        """测试从 AssetStatus 构建无效能力矩阵"""
        asset_status = AssetStatus(
            video_exists=True,
            video_quality="good",
            audio_exists=True,
            audio_quality="good",
            subtitle_state=AssetState.INVALID,
            character_db_state=AssetState.INVALID,
            voice_db_state=AssetState.COMPLETE,
            voice_db_coverage=0.95,
        )

        builder = CapabilityBuilder()
        matrix = builder.from_asset_status(asset_status)

        assert matrix.subtitle.state == CapabilityState.INVALID
        assert matrix.character_db.state == CapabilityState.INVALID
        assert matrix.voice_db.state == CapabilityState.COMPLETE

    def test_custom_threshold(self):
        """测试自定义阈值"""
        asset_status = AssetStatus(
            video_exists=True,
            video_quality="good",
            audio_exists=True,
            audio_quality="good",
            character_db_state=AssetState.PARTIAL,
            character_db_coverage=0.85,
        )

        # 默认阈值
        builder = CapabilityBuilder()
        matrix = builder.from_asset_status(asset_status)
        assert matrix.character_db.state == CapabilityState.PARTIAL

        # 自定义阈值
        threshold = CapabilityThreshold(complete_min=0.80)
        builder = CapabilityBuilder(threshold=threshold)
        matrix = builder.from_asset_status(asset_status)
        assert matrix.character_db.state == CapabilityState.COMPLETE

    def test_artifacts(self):
        """测试 Artifact 能力"""
        asset_status = AssetStatus(
            video_exists=True,
            video_quality="good",
            audio_exists=True,
            audio_quality="good",
            artifacts={
                "dialogue": AssetState.COMPLETE,
                "analysis": AssetState.PARTIAL,
                "invalid": AssetState.INVALID,
            },
        )

        builder = CapabilityBuilder()
        matrix = builder.from_asset_status(asset_status)

        assert matrix.artifacts["dialogue"].state == CapabilityState.COMPLETE
        assert matrix.artifacts["analysis"].state == CapabilityState.COMPLETE  # simple capability
        assert matrix.artifacts["invalid"].state == CapabilityState.INVALID

    def test_subtitle_quality_mapping(self):
        """测试字幕质量映射"""
        # 已验证字幕
        asset_status = AssetStatus(
            video_exists=True,
            video_quality="good",
            audio_exists=True,
            audio_quality="good",
            subtitle_state=AssetState.COMPLETE,
            subtitle_quality="verified",
        )
        builder = CapabilityBuilder()
        matrix = builder.from_asset_status(asset_status)
        assert matrix.subtitle.state == CapabilityState.COMPLETE

        # 低质量字幕
        asset_status.subtitle_quality = "low"
        matrix = builder.from_asset_status(asset_status)
        assert matrix.subtitle.state == CapabilityState.PARTIAL
