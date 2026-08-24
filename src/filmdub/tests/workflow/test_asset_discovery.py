"""AssetDiscovery 单元测试"""

import json
import pytest
from pathlib import Path
from filmdub.orchestrator.workflow.asset_discovery import (
    AssetDiscovery,
    AssetStatus,
    AssetState,
)


@pytest.fixture
def temp_project_dir(tmp_path):
    """创建临时项目目录"""
    project_dir = tmp_path / "test_project"
    media_dir = project_dir / "S01E01"
    media_dir.mkdir(parents=True)

    return project_dir


@pytest.fixture
def discovery(temp_project_dir):
    """创建 AssetDiscovery 实例"""
    return AssetDiscovery(temp_project_dir.parent)


class TestAssetDiscovery:
    """AssetDiscovery 测试"""

    def test_init(self, temp_project_dir):
        """测试初始化"""
        discovery = AssetDiscovery(temp_project_dir)
        assert discovery.project_root == temp_project_dir

    def test_check_video_exists(self, temp_project_dir, discovery):
        """测试检测视频文件存在"""
        media_dir = temp_project_dir / "S01E01"

        # 创建视频文件
        (media_dir / "video.mp4").touch()

        status = discovery.discover("test_project", "S01E01")
        assert status.video_exists is True

    def test_check_video_not_exists(self, temp_project_dir, discovery):
        """测试检测视频文件不存在"""
        status = discovery.discover("test_project", "S01E01")
        assert status.video_exists is False

    def test_check_audio_exists(self, temp_project_dir, discovery):
        """测试检测音频文件存在"""
        media_dir = temp_project_dir / "S01E01"

        # 创建音频文件
        (media_dir / "audio.wav").touch()

        status = discovery.discover("test_project", "S01E01")
        assert status.audio_exists is True

    def test_check_subtitle_srt(self, temp_project_dir, discovery):
        """测试检测 SRT 字幕"""
        media_dir = temp_project_dir / "S01E01"

        # 创建字幕文件
        subtitle_file = media_dir / "subtitle.srt"
        subtitle_file.write_text("1\n00:00:00,000 --> 00:00:02,000\nTest subtitle\n")

        status = discovery.discover("test_project", "S01E01")
        assert status.subtitle_state == AssetState.COMPLETE
        assert status.subtitle_language is not None

    def test_check_subtitle_verified(self, temp_project_dir, discovery):
        """测试检测已验证字幕"""
        media_dir = temp_project_dir / "S01E01"

        # 创建字幕文件和验证标记
        subtitle_file = media_dir / "subtitle.srt"
        subtitle_file.write_text("1\n00:00:00,000 --> 00:00:02,000\nTest subtitle\n")
        (media_dir / "subtitle.srt.verified").touch()

        status = discovery.discover("test_project", "S01E01")
        assert status.subtitle_quality == "verified"

    def test_check_subtitle_not_exists(self, temp_project_dir, discovery):
        """测试检测字幕不存在"""
        status = discovery.discover("test_project", "S01E01")
        assert status.subtitle_state == AssetState.NONE

    def test_check_character_db_none(self, temp_project_dir, discovery):
        """测试人物库不存在"""
        status = discovery.discover("test_project", "S01E01")
        assert status.character_db_state == AssetState.NONE
        assert status.character_db_coverage == 0.0

    def test_check_character_db_complete(self, temp_project_dir, discovery):
        """测试人物库完整"""
        character_db = {
            "version": "1.0",
            "characters": {
                "char1": {"name": "Character 1", "voice_id": "voice1"},
                "char2": {"name": "Character 2", "voice_id": "voice2"},
            },
        }

        char_db_file = temp_project_dir / "character_db.json"
        char_db_file.write_text(json.dumps(character_db), encoding='utf-8')

        status = discovery.discover("test_project", "S01E01")
        assert status.character_db_state == AssetState.COMPLETE
        assert status.character_db_coverage == 1.0

    def test_check_character_db_partial(self, temp_project_dir, discovery):
        """测试人物库部分完整"""
        character_db = {
            "version": "1.0",
            "characters": {
                "char1": {"name": "Character 1", "voice_id": "voice1"},
                "char2": {"name": "Character 2"},  # 没有 voice_id
                "char3": {"name": "Character 3", "voice_id": "voice3"},
            },
        }

        char_db_file = temp_project_dir / "character_db.json"
        char_db_file.write_text(json.dumps(character_db), encoding='utf-8')

        status = discovery.discover("test_project", "S01E01")
        assert status.character_db_state == AssetState.PARTIAL
        assert status.character_db_coverage == 2/3

    def test_check_voice_db_none(self, temp_project_dir, discovery):
        """测试声音库不存在"""
        status = discovery.discover("test_project", "S01E01")
        assert status.voice_db_state == AssetState.NONE

    def test_check_voice_db_complete(self, temp_project_dir, discovery):
        """测试声音库完整"""
        # 创建 voice_db.json
        voice_db = {
            "version": "1.0",
            "voices": {
                "voice1": {"name": "Voice 1"},
                "voice2": {"name": "Voice 2"},
            },
        }

        voice_db_file = temp_project_dir / "voice_db.json"
        voice_db_file.write_text(json.dumps(voice_db), encoding='utf-8')

        # 创建 cloned_voices 目录和文件
        cloned_voices = temp_project_dir / "cloned_voices"
        cloned_voices.mkdir()
        (cloned_voices / "voice1" / "reference.wav").parent.mkdir(parents=True, exist_ok=True)
        (cloned_voices / "voice1" / "reference.wav").touch()
        (cloned_voices / "voice2" / "reference.wav").parent.mkdir(parents=True, exist_ok=True)
        (cloned_voices / "voice2" / "reference.wav").touch()

        status = discovery.discover("test_project", "S01E01")
        assert status.voice_db_state == AssetState.COMPLETE
        assert status.voice_db_coverage == 1.0

    def test_check_voice_db_partial(self, temp_project_dir, discovery):
        """测试声音库部分完整"""
        # 创建 voice_db.json
        voice_db = {
            "version": "1.0",
            "voices": {
                "voice1": {"name": "Voice 1"},
                "voice2": {"name": "Voice 2"},
                "voice3": {"name": "Voice 3"},
            },
        }

        voice_db_file = temp_project_dir / "voice_db.json"
        voice_db_file.write_text(json.dumps(voice_db), encoding='utf-8')

        # 只创建部分音色文件
        cloned_voices = temp_project_dir / "cloned_voices"
        cloned_voices.mkdir()
        (cloned_voices / "voice1" / "reference.wav").parent.mkdir(parents=True, exist_ok=True)
        (cloned_voices / "voice1" / "reference.wav").touch()

        status = discovery.discover("test_project", "S01E01")
        assert status.voice_db_state == AssetState.PARTIAL
        assert status.voice_db_coverage == 1/3

    def test_check_story_db_exists(self, temp_project_dir, discovery):
        """测试故事库存在"""
        story_db = {"episodes": [], "relationships": {}}
        story_db_file = temp_project_dir / "story_bible.json"
        story_db_file.write_text(json.dumps(story_db), encoding='utf-8')

        status = discovery.discover("test_project", "S01E01")
        assert status.story_db_state == AssetState.COMPLETE

    def test_check_story_db_not_exists(self, temp_project_dir, discovery):
        """测试故事库不存在"""
        status = discovery.discover("test_project", "S01E01")
        assert status.story_db_state == AssetState.NONE

    def test_check_translation_memory_exists(self, temp_project_dir, discovery):
        """测试翻译记忆库存在"""
        tm = {"terms": {}, "memory": []}
        tm_file = temp_project_dir / "translation_memory.json"
        tm_file.write_text(json.dumps(tm), encoding='utf-8')

        status = discovery.discover("test_project", "S01E01")
        assert status.translation_memory_state == AssetState.COMPLETE

    def test_check_artifacts(self, temp_project_dir, discovery):
        """测试检查 Artifact"""
        media_dir = temp_project_dir / "S01E01"
        artifacts_dir = media_dir / "artifacts"
        artifacts_dir.mkdir()

        # 创建有效的 artifact
        artifact1 = artifacts_dir / "dialogue.json"
        artifact1.write_text(json.dumps({"valid": True, "data": []}), encoding='utf-8')

        # 创建无效的 artifact
        artifact2 = artifacts_dir / "invalid.json"
        artifact2.write_text("invalid json", encoding='utf-8')

        status = discovery.discover("test_project", "S01E01")
        assert "dialogue" in status.artifacts
        assert status.artifacts["dialogue"] == AssetState.COMPLETE
        assert "invalid" in status.artifacts
        assert status.artifacts["invalid"] == AssetState.INVALID

    def test_get_state_score(self):
        """测试获取资产状态评分"""
        status = AssetStatus()
        status.subtitle_state = AssetState.COMPLETE
        status.character_db_state = AssetState.PARTIAL
        status.voice_db_state = AssetState.NONE

        assert status.get_state_score("subtitle") == 3
        assert status.get_state_score("character_db") == 1
        assert status.get_state_score("voice_db") == 0

    def test_to_task_context(self, discovery):
        """测试转换 AssetStatus 为 TaskContext"""
        status = AssetStatus()
        status.subtitle_state = AssetState.COMPLETE
        status.subtitle_language = "zh-CN"
        status.subtitle_quality = "verified"
        status.audio_exists = True
        status.character_db_state = AssetState.COMPLETE
        status.character_db_coverage = 0.95
        status.character_db_version = "1.0"
        status.voice_db_state = AssetState.PARTIAL
        status.voice_db_coverage = 0.70
        status.voice_db_version = "1.0"
        status.story_db_state = AssetState.COMPLETE
        status.translation_memory_state = AssetState.COMPLETE

        context = discovery.to_task_context(status, "episode")
        context.project_id = "test_project"
        context.media_id = "S01E01"

        assert context.has_subtitle() is True
        assert context.has_verified_subtitle() is True
        assert context.character_db_complete() is True
        assert context.voice_db_complete() is False
        assert context.is_first_processing() is False

    def test_detect_subtitle_language_chinese(self, temp_project_dir, discovery):
        """测试检测中文字幕"""
        media_dir = temp_project_dir / "S01E01"
        subtitle_file = media_dir / "subtitle_zh.srt"
        subtitle_file.write_text("Test")

        assert discovery._detect_subtitle_language(subtitle_file) == "zh-CN"

    def test_detect_subtitle_language_english(self, temp_project_dir, discovery):
        """测试检测英文字幕"""
        media_dir = temp_project_dir / "S01E01"
        subtitle_file = media_dir / "subtitle_en.srt"
        subtitle_file.write_text("Test")

        assert discovery._detect_subtitle_language(subtitle_file) == "en"
