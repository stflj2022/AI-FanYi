"""Asset Discovery - 资产发现

扫描并检查所有资源状态，包括：
- 视频/音频文件
- 字幕文件
- 人物数据库
- 声音数据库
- 剧情数据库
- 翻译记忆
- 已有 Artifact

不只看文件存在，还检查版本、覆盖率、适用性。
"""

import os
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from .task_context import (
    TaskContext,
    SubtitleStatus,
    AudioStatus,
    DatabaseStatus,
)


class AssetState(str, Enum):
    """资产状态"""
    NONE = "none"  # 不存在
    PARTIAL = "partial"  # 部分存在
    COMPLETE = "complete"  # 完整
    INVALID = "invalid"  # 无效
    OUTDATED = "outdated"  # 过期


class AssetStatus(BaseModel):
    """资产状态

    记录所有资源的状态。
    """
    # 视频/音频
    video_exists: bool = False
    audio_exists: bool = False
    video_quality: Optional[str] = None
    audio_quality: Optional[str] = None

    # 字幕
    subtitle_state: AssetState = AssetState.NONE
    subtitle_language: Optional[str] = None
    subtitle_quality: Optional[str] = None
    subtitle_timing_quality: Optional[str] = None

    # 数据库
    character_db_state: AssetState = AssetState.NONE
    character_db_coverage: float = 0.0
    character_db_version: Optional[str] = None

    voice_db_state: AssetState = AssetState.NONE
    voice_db_coverage: float = 0.0
    voice_db_version: Optional[str] = None

    story_db_state: AssetState = AssetState.NONE
    translation_memory_state: AssetState = AssetState.NONE

    # Artifact
    artifacts: Dict[str, AssetState] = Field(default_factory=dict)

    # 版本信息
    versions: Dict[str, str] = Field(default_factory=dict)

    def get_state_score(self, asset_type: str) -> int:
        """获取资产状态评分

        Args:
            asset_type: 资产类型 (subtitle, character_db, voice_db, etc.)

        Returns:
            状态评分：0=NONE, 1=PARTIAL/INVALID, 2=OUTDATED, 3=COMPLETE
        """
        state_map = {
            AssetState.NONE: 0,
            AssetState.PARTIAL: 1,
            AssetState.INVALID: 1,
            AssetState.OUTDATED: 2,
            AssetState.COMPLETE: 3,
        }

        if asset_type == "subtitle":
            return state_map[self.subtitle_state]
        elif asset_type == "character_db":
            return state_map[self.character_db_state]
        elif asset_type == "voice_db":
            return state_map[self.voice_db_state]
        elif asset_type == "story_db":
            return state_map[self.story_db_state]
        elif asset_type == "translation_memory":
            return state_map[self.translation_memory_state]

        return 0


class AssetDiscovery:
    """资产发现器

    扫描项目目录，检查所有资源状态。
    """

    def __init__(self, project_root: Path):
        """初始化资产发现器

        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root)

    def discover(self, project_id: str, media_id: str) -> AssetStatus:
        """发现资产状态

        Args:
            project_id: 项目 ID
            media_id: 媒体 ID

        Returns:
            AssetStatus 实例
        """
        project_path = self.project_root / project_id
        media_path = project_path / media_id

        status = AssetStatus()

        # 检查视频/音频
        status.video_exists = self._check_video(media_path)
        status.audio_exists = self._check_audio(media_path)

        # 检查字幕
        subtitle_info = self._check_subtitle(media_path)
        status.subtitle_state = subtitle_info["state"]
        status.subtitle_language = subtitle_info.get("language")
        status.subtitle_quality = subtitle_info.get("quality")
        status.subtitle_timing_quality = subtitle_info.get("timing_quality")

        # 检查人物库
        character_info = self._check_character_db(project_path)
        status.character_db_state = character_info["state"]
        status.character_db_coverage = character_info.get("coverage", 0.0)
        status.character_db_version = character_info.get("version")

        # 检查声音库
        voice_info = self._check_voice_db(project_path)
        status.voice_db_state = voice_info["state"]
        status.voice_db_coverage = voice_info.get("coverage", 0.0)
        status.voice_db_version = voice_info.get("version")

        # 检查故事库和翻译记忆
        status.story_db_state = self._check_story_db(project_path)
        status.translation_memory_state = self._check_translation_memory(project_path)

        # 检查已有 Artifact
        status.artifacts = self._check_artifacts(media_path)

        return status

    def _check_video(self, media_path: Path) -> bool:
        """检查视频文件是否存在"""
        video_extensions = [".mp4", ".mkv", ".avi", ".mov", ".webm"]
        for ext in video_extensions:
            if (media_path / f"video{ext}").exists():
                return True
            # 也检查直接命名的文件
            if (media_path.parent / f"{media_path.name}{ext}").exists():
                return True
        return False

    def _check_audio(self, media_path: Path) -> bool:
        """检查音频文件是否存在"""
        audio_extensions = [".mp3", ".wav", ".aac", ".m4a", ".flac"]
        for ext in audio_extensions:
            if (media_path / f"audio{ext}").exists():
                return True
        return False

    def _check_subtitle(self, media_path: Path) -> Dict[str, Any]:
        """检查字幕文件"""
        subtitle_extensions = [".srt", ".ass", ".vtt", ".ssa"]

        for ext in subtitle_extensions:
            subtitle_file = media_path / f"subtitle{ext}"
            if subtitle_file.exists():
                # 检查质量标记
                quality = self._detect_subtitle_quality(subtitle_file)
                return {
                    "state": AssetState.COMPLETE,
                    "language": self._detect_subtitle_language(subtitle_file),
                    "quality": quality,
                    "timing_quality": self._detect_timing_quality(subtitle_file),
                }

        return {"state": AssetState.NONE}

    def _check_character_db(self, project_path: Path) -> Dict[str, Any]:
        """检查人物数据库"""
        character_db_path = project_path / "character_db.json"

        if not character_db_path.exists():
            return {"state": AssetState.NONE}

        # 读取并分析数据库
        try:
            import json
            with open(character_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查版本
            version = data.get("version", "1.0")
            characters = data.get("characters", {})

            # 计算覆盖率（基于是否有 voice_id）
            if characters:
                with_voice = sum(1 for c in characters.values() if c.get("voice_id"))
                coverage = len(characters) / max(len(characters), 1)
                voice_coverage = with_voice / max(len(characters), 1)
            else:
                coverage = 0.0
                voice_coverage = 0.0

            # 判断状态
            if voice_coverage >= 0.9:
                state = AssetState.COMPLETE
            elif voice_coverage > 0.5:
                state = AssetState.PARTIAL
            else:
                state = AssetState.PARTIAL

            return {
                "state": state,
                "coverage": voice_coverage,
                "version": version,
            }

        except Exception:
            return {"state": AssetState.INVALID}

    def _check_voice_db(self, project_path: Path) -> Dict[str, Any]:
        """检查声音数据库"""
        voice_db_path = project_path / "voice_db.json"

        if not voice_db_path.exists():
            return {"state": AssetState.NONE}

        # 检查 cloned_voices 目录
        cloned_voices_path = project_path / "cloned_voices"
        if not cloned_voices_path.exists():
            return {"state": AssetState.NONE}

        # 计算覆盖率
        try:
            import json
            with open(voice_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            voices = data.get("voices", {})
            version = data.get("version", "1.0")

            # 检查实际音色文件
            available_voices = []
            for voice_id in voices.keys():
                voice_dir = cloned_voices_path / voice_id
                if voice_dir.exists() and any(voice_dir.iterdir()):
                    available_voices.append(voice_id)

            if voices:
                coverage = len(available_voices) / len(voices)
            else:
                coverage = 0.0

            # 判断状态
            if coverage >= 0.9:
                state = AssetState.COMPLETE
            elif coverage > 0.5:
                state = AssetState.PARTIAL
            else:
                state = AssetState.PARTIAL

            return {
                "state": state,
                "coverage": coverage,
                "version": version,
            }

        except Exception:
            return {"state": AssetState.INVALID}

    def _check_story_db(self, project_path: Path) -> AssetState:
        """检查故事数据库"""
        story_db_path = project_path / "story_bible.json"

        if not story_db_path.exists():
            return AssetState.NONE

        return AssetState.COMPLETE

    def _check_translation_memory(self, project_path: Path) -> AssetState:
        """检查翻译记忆库"""
        tm_path = project_path / "translation_memory.json"

        if not tm_path.exists():
            return AssetState.NONE

        return AssetState.COMPLETE

    def _check_artifacts(self, media_path: Path) -> Dict[str, AssetState]:
        """检查已有 Artifact"""
        artifacts_path = media_path / "artifacts"

        if not artifacts_path.exists():
            return {}

        artifacts = {}
        for artifact_file in artifacts_path.glob("*.json"):
            artifact_name = artifact_file.stem
            try:
                import json
                with open(artifact_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 检查版本和有效性
                    if data.get("valid", True):
                        artifacts[artifact_name] = AssetState.COMPLETE
                    else:
                        artifacts[artifact_name] = AssetState.INVALID
            except Exception:
                artifacts[artifact_name] = AssetState.INVALID

        return artifacts

    def _detect_subtitle_quality(self, subtitle_file: Path) -> str:
        """检测字幕质量"""
        # 简单实现：检查是否有 .verified 标记文件
        verified_file = subtitle_file.with_suffix(subtitle_file.suffix + ".verified")
        if verified_file.exists():
            return "verified"

        # 检查文件大小
        if subtitle_file.stat().st_size < 100:
            return "low"

        return "unknown"

    def _detect_subtitle_language(self, subtitle_file: Path) -> Optional[str]:
        """检测字幕语言"""
        # 从文件名检测
        name = subtitle_file.name.lower()
        if "zh" in name or "cn" in name or "chinese" in name:
            return "zh-CN"
        elif "en" in name or "english" in name:
            return "en"
        # 默认假设是中文字幕
        return "zh-CN"

    def _detect_timing_quality(self, subtitle_file: Path) -> Optional[str]:
        """检测字幕时间轴质量"""
        # 简单实现：检查是否有 .timing_ok 标记文件
        timing_file = subtitle_file.with_suffix(subtitle_file.suffix + ".timing_ok")
        if timing_file.exists():
            return "good"

        return "unknown"

    def to_task_context(self, asset_status: AssetStatus, task_type: str = "episode") -> TaskContext:
        """将 AssetStatus 转换为 TaskContext

        Args:
            asset_status: 资产状态
            task_type: 任务类型

        Returns:
            TaskContext 实例
        """
        from .task_context import TaskType, QualityRequirement

        return TaskContext(
            project_id="",  # 需要外部传入
            media_id="",  # 需要外部传入
            task_type=TaskType(task_type),
            subtitle=SubtitleStatus(
                exists=asset_status.subtitle_state != AssetState.NONE,
                language=asset_status.subtitle_language,
                quality=asset_status.subtitle_quality,
                timing_quality=asset_status.subtitle_timing_quality,
            ),
            audio=AudioStatus(
                exists=asset_status.audio_exists,
                quality=asset_status.audio_quality,
            ),
            character_db=DatabaseStatus(
                exists=asset_status.character_db_state != AssetState.NONE,
                coverage=asset_status.character_db_coverage,
                version=asset_status.character_db_version,
                outdated=asset_status.character_db_state == AssetState.OUTDATED,
            ),
            voice_db=DatabaseStatus(
                exists=asset_status.voice_db_state != AssetState.NONE,
                coverage=asset_status.voice_db_coverage,
                version=asset_status.voice_db_version,
                outdated=asset_status.voice_db_state == AssetState.OUTDATED,
            ),
            story_db=DatabaseStatus(
                exists=asset_status.story_db_state != AssetState.NONE,
            ),
            translation_memory=DatabaseStatus(
                exists=asset_status.translation_memory_state != AssetState.NONE,
            ),
            first_processing=asset_status.character_db_state == AssetState.NONE,
            quality_requirement=QualityRequirement.STANDARD,
        )
