"""Capability Matrix - 能力矩阵

每种资源的能力状态不是简单的"有/无"，而是五态判定：
- NONE: 不存在
- PARTIAL: 部分存在
- COMPLETE: 完整
- INVALID: 无效
- OUTDATED: 过期

这是动态工作流编排的核心基础。
"""

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field

from .asset_discovery import AssetStatus, AssetState


class CapabilityState(str, Enum):
    """能力状态"""
    NONE = "none"  # 不存在
    PARTIAL = "partial"  # 部分存在
    COMPLETE = "complete"  # 完整
    INVALID = "invalid"  # 无效
    OUTDATED = "outdated"  # 过期


class CapabilityThreshold(BaseModel):
    """能力判定阈值"""
    partial_min: float = 0.3  # PARTIAL 最低覆盖率
    partial_max: float = 0.89  # PARTIAL 最高覆盖率
    complete_min: float = 0.9  # COMPLETE 最低覆盖率


class CapabilityEntry(BaseModel):
    """能力条目"""
    state: CapabilityState
    coverage: float = 0.0
    version: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)


class CapabilityMatrix(BaseModel):
    """能力矩阵

    记录所有资源的能力状态。
    """
    # 视频/音频
    video: CapabilityEntry = Field(
        default_factory=lambda: CapabilityEntry(state=CapabilityState.NONE)
    )
    audio: CapabilityEntry = Field(
        default_factory=lambda: CapabilityEntry(state=CapabilityState.NONE)
    )

    # 字幕
    subtitle: CapabilityEntry = Field(
        default_factory=lambda: CapabilityEntry(state=CapabilityState.NONE)
    )

    # 数据库
    character_db: CapabilityEntry = Field(
        default_factory=lambda: CapabilityEntry(state=CapabilityState.NONE)
    )
    voice_db: CapabilityEntry = Field(
        default_factory=lambda: CapabilityEntry(state=CapabilityState.NONE)
    )
    story_db: CapabilityEntry = Field(
        default_factory=lambda: CapabilityEntry(state=CapabilityState.NONE)
    )
    translation_memory: CapabilityEntry = Field(
        default_factory=lambda: CapabilityEntry(state=CapabilityState.NONE)
    )

    # Artifact
    artifacts: Dict[str, CapabilityEntry] = Field(default_factory=dict)

    # 配置
    threshold: CapabilityThreshold = Field(default_factory=CapabilityThreshold)

    def get_score(self, capability: str) -> int:
        """获取能力评分

        Args:
            capability: 能力名称

        Returns:
            评分：0=NONE, 1=PARTIAL/INVALID, 2=OUTDATED, 3=COMPLETE
        """
        entry = getattr(self, capability, None)
        if entry is None:
            return 0

        state_map = {
            CapabilityState.NONE: 0,
            CapabilityState.PARTIAL: 1,
            CapabilityState.INVALID: 1,
            CapabilityState.OUTDATED: 2,
            CapabilityState.COMPLETE: 3,
        }
        return state_map.get(entry.state, 0)

    def has_capability(self, capability: str, min_state: CapabilityState = CapabilityState.PARTIAL) -> bool:
        """检查是否有足够的能力

        Args:
            capability: 能力名称
            min_state: 最低要求的状态

        Returns:
            是否满足要求
        """
        entry = getattr(self, capability, None)
        if entry is None:
            return False

        state_order = [
            CapabilityState.NONE,
            CapabilityState.INVALID,
            CapabilityState.PARTIAL,
            CapabilityState.OUTDATED,
            CapabilityState.COMPLETE,
        ]

        try:
            entry_index = state_order.index(entry.state)
            min_index = state_order.index(min_state)
            return entry_index >= min_index
        except ValueError:
            return False

    def is_ready_for_production(self) -> bool:
        """检查是否准备好进行生产级处理"""
        return (
            self.has_capability("video", CapabilityState.COMPLETE)
            and self.has_capability("audio", CapabilityState.COMPLETE)
            and self.has_capability("character_db", CapabilityState.COMPLETE)
            and self.has_capability("voice_db", CapabilityState.COMPLETE)
        )

    def is_ready_for_standard(self) -> bool:
        """检查是否准备好进行标准处理"""
        return (
            self.has_capability("video", CapabilityState.COMPLETE)
            and self.has_capability("audio", CapabilityState.PARTIAL)
            and self.has_capability("character_db", CapabilityState.PARTIAL)
            and self.has_capability("voice_db", CapabilityState.PARTIAL)
        )

    def get_missing_capabilities(self, min_state: CapabilityState = CapabilityState.COMPLETE) -> list[str]:
        """获取缺失的能力

        Args:
            min_state: 最低要求的状态

        Returns:
            缺失的能力列表
        """
        missing = []
        capabilities = ["video", "audio", "subtitle", "character_db", "voice_db"]

        for cap in capabilities:
            if not self.has_capability(cap, min_state):
                missing.append(cap)

        return missing


class CapabilityBuilder:
    """能力矩阵构建器"""

    def __init__(self, threshold: Optional[CapabilityThreshold] = None):
        """初始化构建器

        Args:
            threshold: 能力判定阈值
        """
        self.threshold = threshold or CapabilityThreshold()

    def from_asset_status(self, asset_status: AssetStatus, current_version: Optional[Dict[str, str]] = None) -> CapabilityMatrix:
        """从 AssetStatus 构建 CapabilityMatrix

        Args:
            asset_status: 资产状态
            current_version: 当前版本信息

        Returns:
            CapabilityMatrix 实例
        """
        current_version = current_version or {}

        return CapabilityMatrix(
            video=self._build_video_capability(asset_status),
            audio=self._build_audio_capability(asset_status),
            subtitle=self._build_subtitle_capability(asset_status),
            character_db=self._build_db_capability(
                asset_status.character_db_state,
                asset_status.character_db_coverage,
                asset_status.character_db_version,
                current_version.get("character_db"),
            ),
            voice_db=self._build_db_capability(
                asset_status.voice_db_state,
                asset_status.voice_db_coverage,
                asset_status.voice_db_version,
                current_version.get("voice_db"),
            ),
            story_db=self._build_simple_capability(asset_status.story_db_state),
            translation_memory=self._build_simple_capability(asset_status.translation_memory_state),
            artifacts={
                name: self._build_simple_capability(state)
                for name, state in asset_status.artifacts.items()
            },
            threshold=self.threshold,
        )

    def _build_video_capability(self, asset_status: AssetStatus) -> CapabilityEntry:
        """构建视频能力"""
        if not asset_status.video_exists:
            return CapabilityEntry(state=CapabilityState.NONE)

        return CapabilityEntry(
            state=CapabilityState.COMPLETE if asset_status.video_quality == "good" else CapabilityState.PARTIAL,
            metadata={"quality": asset_status.video_quality},
        )

    def _build_audio_capability(self, asset_status: AssetStatus) -> CapabilityEntry:
        """构建音频能力"""
        if not asset_status.audio_exists:
            return CapabilityEntry(state=CapabilityState.NONE)

        return CapabilityEntry(
            state=CapabilityState.COMPLETE if asset_status.audio_quality == "good" else CapabilityState.PARTIAL,
            metadata={"quality": asset_status.audio_quality},
        )

    def _build_subtitle_capability(self, asset_status: AssetStatus) -> CapabilityEntry:
        """构建字幕能力"""
        if asset_status.subtitle_state == AssetState.NONE:
            return CapabilityEntry(state=CapabilityState.NONE)

        if asset_status.subtitle_state == AssetState.INVALID:
            return CapabilityEntry(state=CapabilityState.INVALID)

        # 根据质量判断状态
        if asset_status.subtitle_quality == "verified":
            state = CapabilityState.COMPLETE
        elif asset_status.subtitle_quality == "low":
            state = CapabilityState.PARTIAL
        else:
            state = CapabilityState.PARTIAL

        return CapabilityEntry(
            state=state,
            metadata={
                "language": asset_status.subtitle_language,
                "quality": asset_status.subtitle_quality,
                "timing_quality": asset_status.subtitle_timing_quality,
            },
        )

    def _build_db_capability(
        self,
        asset_state: AssetState,
        coverage: float,
        version: Optional[str],
        current_version: Optional[str],
    ) -> CapabilityEntry:
        """构建数据库能力（人物库/声音库）"""
        if asset_state == AssetState.NONE:
            return CapabilityEntry(state=CapabilityState.NONE)

        if asset_state == AssetState.INVALID:
            return CapabilityEntry(state=CapabilityState.INVALID)

        # 检查是否过期
        if current_version and version and version != current_version:
            return CapabilityEntry(
                state=CapabilityState.OUTDATED,
                coverage=coverage,
                version=version,
                metadata={"current_version": current_version},
            )

        # 根据覆盖率判断状态
        if coverage >= self.threshold.complete_min:
            state = CapabilityState.COMPLETE
        elif coverage >= self.threshold.partial_min:
            state = CapabilityState.PARTIAL
        else:
            state = CapabilityState.PARTIAL  # 虽然存在但覆盖率太低

        return CapabilityEntry(
            state=state,
            coverage=coverage,
            version=version,
        )

    def _build_simple_capability(self, asset_state: AssetState) -> CapabilityEntry:
        """构建简单能力（故事库/翻译记忆）"""
        if asset_state == AssetState.NONE:
            return CapabilityEntry(state=CapabilityState.NONE)

        if asset_state == AssetState.INVALID:
            return CapabilityEntry(state=CapabilityState.INVALID)

        return CapabilityEntry(state=CapabilityState.COMPLETE)
