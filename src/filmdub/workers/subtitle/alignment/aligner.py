"""
字幕对齐器 - 对齐字幕时间轴到视频时间轴
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

from ..importer.parser import SubtitleEntry
from ...subtitle.config import SubtitleConfig

logger = logging.getLogger(__name__)


@dataclass
class AlignmentResult:
    """对齐结果"""
    aligned_entries: List[SubtitleEntry]
    offset: float
    scale: float
    confidence: float
    method: str


class SubtitleAligner:
    """字幕对齐器"""

    def __init__(self, config: SubtitleConfig):
        """
        初始化对齐器

        Args:
            config: 字幕配置
        """
        self.config = config

    def align(
        self,
        entries: List[SubtitleEntry],
        video_duration: float,
        reference_entries: Optional[List[SubtitleEntry]] = None
    ) -> AlignmentResult:
        """
        对齐字幕到视频时间轴

        Args:
            entries: 字幕条目列表
            video_duration: 视频时长（秒）
            reference_entries: 参考字幕条目列表（用于计算偏移）

        Returns:
            对齐结果
        """
        if not entries:
            return AlignmentResult(
                aligned_entries=[],
                offset=0.0,
                scale=1.0,
                confidence=0.0,
                method="none"
            )

        # 如果有参考字幕，使用参考字幕计算偏移
        if reference_entries:
            return self._align_with_reference(entries, reference_entries)

        # 否则，根据时长差异决定是否需要对齐
        subtitle_duration = entries[-1].end
        duration_diff = abs(subtitle_duration - video_duration)

        if duration_diff <= self.config.max_duration_diff:
            # 时长接近，不需要对齐
            logger.info(f"Duration diff ({duration_diff:.2f}s) within threshold, no alignment needed")
            return AlignmentResult(
                aligned_entries=entries,
                offset=0.0,
                scale=1.0,
                confidence=1.0,
                method="none"
            )
        else:
            # 时长差异大，需要缩放
            return self._align_by_scaling(entries, video_duration, subtitle_duration)

    def _align_with_reference(
        self,
        entries: List[SubtitleEntry],
        reference_entries: List[SubtitleEntry]
    ) -> AlignmentResult:
        """使用参考字幕对齐"""
        # 尝试找到最佳偏移量
        offset, confidence = self._find_best_offset(entries, reference_entries)

        if offset == 0 and confidence < 0.5:
            logger.warning(f"Low confidence alignment (confidence={confidence:.2f})")
            return AlignmentResult(
                aligned_entries=entries,
                offset=0.0,
                scale=1.0,
                confidence=confidence,
                method="reference_low_confidence"
            )

        # 应用偏移
        aligned = []
        for entry in entries:
            aligned_entry = SubtitleEntry(
                index=entry.index,
                start=max(0, entry.start + offset),
                end=max(0, entry.end + offset),
                text=entry.text
            )
            aligned.append(aligned_entry)

        logger.info(f"Aligned with reference: offset={offset:.2f}s, confidence={confidence:.2f}")
        return AlignmentResult(
            aligned_entries=aligned,
            offset=offset,
            scale=1.0,
            confidence=confidence,
            method="reference"
        )

    def _find_best_offset(
        self,
        entries: List[SubtitleEntry],
        reference_entries: List[SubtitleEntry]
    ) -> Tuple[float, float]:
        """
        找到最佳偏移量

        通过比较字幕时间戳的相似性来计算偏移
        """
        # 提取时间戳
        entry_times = [(e.start, e.end) for e in entries]
        ref_times = [(e.start, e.end) for e in reference_entries]

        # 尝试不同的偏移量
        best_offset = 0.0
        best_score = 0.0

        # 搜索范围
        search_range = self.config.max_offset_search
        step = 0.1  # 100ms 精度

        if HAS_NUMPY:
            offsets = np.arange(-search_range, search_range + step, step)
        else:
            offsets = [i * step for i in range(int(-search_range / step), int(search_range / step) + 1)]

        for offset in offsets:
            score = self._calculate_offset_score(entry_times, ref_times, offset)
            if score > best_score:
                best_score = score
                best_offset = offset

        confidence = min(1.0, best_score / len(entries))
        return best_offset, confidence

    def _calculate_offset_score(
        self,
        entry_times: List[Tuple[float, float]],
        ref_times: List[Tuple[float, float]],
        offset: float
    ) -> float:
        """
        计算偏移得分

        计算在给定偏移下，有多少字幕时间戳与参考字幕对齐
        """
        score = 0
        tolerance = 2.0  # 2秒容差

        for entry_start, entry_end in entry_times:
            adjusted_start = entry_start + offset
            adjusted_end = entry_end + offset

            for ref_start, ref_end in ref_times:
                # 检查时间戳是否重叠
                if (adjusted_start <= ref_end + tolerance and
                    adjusted_end >= ref_start - tolerance):
                    score += 1
                    break

        return score

    def _align_by_scaling(
        self,
        entries: List[SubtitleEntry],
        video_duration: float,
        subtitle_duration: float
    ) -> AlignmentResult:
        """通过缩放对齐"""
        # 计算缩放比例
        scale = video_duration / subtitle_duration

        # 应用缩放
        aligned = []
        for entry in entries:
            aligned_entry = SubtitleEntry(
                index=entry.index,
                start=entry.start * scale,
                end=entry.end * scale,
                text=entry.text
            )
            aligned.append(aligned_entry)

        confidence = max(0.0, 1.0 - abs(scale - 1.0))

        logger.info(f"Aligned by scaling: scale={scale:.4f}, confidence={confidence:.2f}")
        return AlignmentResult(
            aligned_entries=aligned,
            offset=0.0,
            scale=scale,
            confidence=confidence,
            method="scaling"
        )

    def detect_cuts(
        self,
        entries: List[SubtitleEntry],
        video_duration: float
    ) -> List[float]:
        """
        检测可能的剪辑点（字幕间隔大的位置）

        Args:
            entries: 字幕条目列表
            video_duration: 视频时长

        Returns:
            剪辑点时间列表
        """
        cuts = []

        for i in range(1, len(entries)):
            gap = entries[i].start - entries[i-1].end

            # 如果间隔超过阈值，可能是剪辑点
            if gap > self.config.max_subtitle_gap:
                cut_time = (entries[i-1].end + entries[i].start) / 2
                cuts.append(cut_time)
                logger.debug(f"Detected cut at {cut_time:.2f}s (gap={gap:.2f}s)")

        return cuts
